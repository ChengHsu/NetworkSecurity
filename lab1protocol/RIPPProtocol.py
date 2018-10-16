import asyncio
import random
import time
import os

from playground.network.common import StackingProtocol
from .RIPPPacket import RIPPPacket

from termcolor import colored


class RIPPProtocol(StackingProtocol):
    # Constants
    WINDOW_SIZE = 150
    TIMEOUT = 0.1
    MAX_RIP_RETRIES = 4
    SCAN_INTERVAL = 0.02
    DEBUG_MODE = True
    LOSS_RATE = 0
    MTU = 1500

    # State definitions
    DEFAULT = "DEFAULT"
    SERVER_LISTEN = "SERVER_LISTEN"
    SERVER_SYN_RCVD = "SERVER_SYN_RCVD"
    SERVER_ESTABLISHED = "SERVER_ESTABLISHED"
    SERVER_FIN_WAIT = "SERVER_FIN_WAIT"
    SERVER_CLOSED = "SERVER_CLOSED"
    CLIENT_INITIAL_SYN = "CLIENT_INITIAL_SYN"
    CLIENT_SYN_SNT = "CLIENT_SYN_SNT"
    CLIENT_ESTABLISHED = "CLIENT_ESTABLISHED"
    CLIENT_FIN_WAIT = "CLIENT_FIN_WAIT"
    CLIENT_CLOSED = "CLIENT_CLOSED"

    def __init__(self):
        super().__init__()
        self.state = self.DEFAULT
        self.transport = None
        self.deserializer = RIPPPacket.Deserializer()
        self.sendSeq = random.randint(0, 10000)
        self.recvSeq = None
        self.sentDataCache = {}
        self.sendingDataBuffer = []
        self.receivedDataBuffer = {}
        self.tasks = []


    def sendSyn(self,transport):
        self.transport = transport
        #create SYN Packet
        synPkt = RIPPPacket()
        synPkt.Type = synPkt.SYN
        synPkt.SeqNo = self.sendSeq
        synPkt.updateChecksum()
        self.debug_logger ("Sending SYN packet. Seq: " + str(self.sendSeq),'green')
        transport.write(synPkt.__serialize__())


    def sendSynAck(self, transport, synAck_seqNum):
        # create SYN-ACK Packet
        synAckPkt = RIPPPacket()
        synAckPkt.Type = synAckPkt.SYN + synAckPkt.ACK
        synAckPkt.SeqNo = synAck_seqNum
        synAckPkt.AckNo = self.recvSeq
        synAckPkt.updateChecksum()
        self.debug_logger("Sending SYN_ACK packet.  Seq: " + str(synAck_seqNum) +
                      ", ack number " + str(self.recvSeq),'green')
        transport.write(synAckPkt.__serialize__())

    def sendAck(self, transport):
        # create ACK Packet
        ackPkt = RIPPPacket()
        ackPkt.Type = ackPkt.ACK
        ackPkt.AckNo = self.recvSeq
        ackPkt.updateChecksum()
        self.debug_logger("Sending ACK packet. Ack: " + str(self.recvSeq) +
              ", current state " + self.state,'green')
        transport.write(ackPkt.__serialize__())

    def sendFin(self, transport):
        # create FIN Packet
        finPkt = RIPPPacket()
        finPkt.Type = finPkt.FIN
        finPkt.SeqNo = self.sendSeq
        finPkt.updateChecksum()
        self.debug_logger("Sending FIN packet.  Seq: " + str(self.sendSeq) +
                      ", current state " + self.state,'green')
        transport.write(finPkt.__serialize__())

    def sendFinAck(self, transport):
        # create FIN Packet
        finAckPkt = RIPPPacket()
        finAckPkt.Type = finAckPkt.FIN + finAckPkt.ACK
        finAckPkt.AckNo = self.recvSeq
        finAckPkt.updateChecksum()
        self.debug_logger("Sending FIN_ACK packet.  Seq: " + str(self.sendSeq) +
                    ", ack number " + str(self.recvSeq) + ", current state " + self.state,'green')
        transport.write(finAckPkt.__serialize__())

    def recvDataPkt(self, pkt):
        if self.isClosing():
            self.debug_logger("Closing, ignored data packet.  Seq: " + str(pkt.SeqNo),'red')
        elif pkt.SeqNo == self.recvSeq:  # in order
            self.debug_logger("Received DATA packet.  Seq: " +
                  str(pkt.SeqNo),'blue')
            self.recvSeq = pkt.SeqNo + len(
                pkt.Data)
            self.higherProtocol().data_received(pkt.Data)

            while self.recvSeq in self.receivedDataBuffer:
                nextPkt = self.receivedDataBuffer.pop(self.recvSeq)
                self.r = nextPkt.SeqNo + len(nextPkt.Data)
                self.higherProtocol().data_received(nextPkt.Data)
        elif pkt.SeqNo > self.recvSeq:
            self.debug_logger("Received Data packet with bigger Seq: " +str(pkt.SeqNo) + ", " + str(self.recvSeq) + "expected.",'blue')
            self.receivedDataBuffer[pkt.SeqNo] = pkt
        else:
            self.debug_logger("Received DATA packet with smaller Seq: " + str(pkt.SeqNo) +  ", " + str(self.recvSeq) + "expected.".format(self.recvSeq),'red')
        self.sendAck(self.transport)



    def recvAckPkt(self, pkt):
        self.debug_logger("Received ACK packet with Ack Num: " +
                      str(pkt.AckNo),'blue')
        latestAckNumber = pkt.AckNo
        #selective
        if latestAckNumber in self.sentDataCache:
            if len(self.sendingDataBuffer) > 0:
                (nextAck, dataPkt) = self.sendingDataBuffer.pop(0)
                self.debug_logger("Sending next packet " + str(nextAck) + " in sendingDataBuffer...",'blue')
                self.sentDataCache[nextAck] = (dataPkt, time.time())
                self.transport.write(dataPkt.__serialize__())
            self.debug_logger("Received ACK for dataSeq: {!r}, removing".format(self.sentDataCache[latestAckNumber][0].SeqNo),'blue')
            del self.sentDataCache[latestAckNumber]
        # for ackNumber in list(self.sentDataCache):
        #     # cumulative
        #     if ackNumber <= latestAckNumber:
        #         if len(self.sendingDataBuffer) > 0:
        #             (nextAck, dataPkt) = self.sendingDataBuffer.pop(0)
        #             self.debug_logger("Sending next packet " + str(nextAck) + " in sendingDataBuffer...",'blue')
        #             self.sentDataCache[nextAck] = (dataPkt, time.time())
        #             self.transport.write(dataPkt.__serialize__())
        #         self.debug_logger("Received ACK for dataSeq: {!r}, removing".format(self.sentDataCache[ackNumber][0].SeqNo),'blue')
        #         del self.sentDataCache[ackNumber]


    async def checkTimeout(self):
        while not self.isClosing():
            for ackNumber in self.sentDataCache:
                (dataPkt, timestamp) = self.sentDataCache[ackNumber]
                currentTime = time.time()
                if currentTime - timestamp >= self.TIMEOUT:
                    self.debug_logger("Resending packet " + str(dataPkt.SeqNo) + " in cache...",'red')
                    self.transport.write(dataPkt.__serialize__())
                    self.sentDataCache[ackNumber] = (dataPkt, currentTime)
            await asyncio.sleep(self.SCAN_INTERVAL)


    def debug_logger(self, text,color):
        if self.DEBUG_MODE:
            print(colored(type(self).__name__ + ": " + text,color))


