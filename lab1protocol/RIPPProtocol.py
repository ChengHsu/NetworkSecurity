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

    # State definitions
    STATE_DESC = {
        0: "DEFAULT",

        100: "SERVER_LISTEN",
        101: "SERVER_SYN_RCVD",
        102: "SERVER_TRANSMISSION",
        103: "SERVER_FIN_WAIT",
        104: "SERVER_CLOSED",

        200: "CLIENT_INITIAL_SYN",
        201: "CLIENT_SYN_ACK",
        202: "CLIENT_TRANSMISSION",
        203: "CLIENT_FIN_WAIT",
        204: "CLIENT_CLOSED"
    }

    STATE_DEFAULT = 0

    STATE_SERVER_LISTEN = 100
    STATE_SERVER_SYN_RCVD = 101
    STATE_SERVER_TRANSMISSION = 102

    STATE_SERVER_FIN_WAIT = 103
    STATE_SERVER_CLOSED = 104

    STATE_CLIENT_INITIAL_SYN = 200
    STATE_CLIENT_SYN_SNT = 201
    STATE_CLIENT_TRANSMISSION = 202
    STATE_CLIENT_FIN_WAIT = 203
    STATE_CLIENT_CLOSED = 204

    def __init__(self):
        super().__init__()
        self.state = self.STATE_DEFAULT
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
        synPkt.Type = synPkt.TYPE_SYN
        synPkt.SeqNo = self.sendSeq
        synPkt.updateChecksum()
        self.debug_logger ("Sending SYN packet with seq number " + str(self.sendSeq),'green')
        transport.write(synPkt.__serialize__())


    def sendSynAck(self, transport, synAck_seqNum):
        # create SYN-ACK Packet
        synAckPkt = RIPPPacket()
        synAckPkt.Type = synAckPkt.TYPE_SYN + synAckPkt.TYPE_ACK
        synAckPkt.SeqNo = synAck_seqNum
        synAckPkt.AckNo = self.recvSeq
        synAckPkt.updateChecksum()
        self.debug_logger("Sending SYN_ACK packet with seq number " + str(synAck_seqNum) +
                      ", ack number " + str(self.recvSeq),'green')
        transport.write(synAckPkt.__serialize__())

    def sendAck(self, transport):
        # create ACK Packet
        ackPkt = RIPPPacket()
        ackPkt.Type = ackPkt.TYPE_ACK
        ackPkt.AckNo = self.recvSeq
        ackPkt.updateChecksum()
        self.debug_logger("Sending ACK packet with ack number " + str(self.recvSeq) +
              ", current state " + self.STATE_DESC[self.state],'green')
        transport.write(ackPkt.__serialize__())

    def sendFin(self, transport):
        # create FIN Packet
        finPkt = RIPPPacket()
        finPkt.Type = finPkt.TYPE_FIN
        finPkt.SeqNo = self.sendSeq
        finPkt.updateChecksum()
        self.debug_logger("Sending FIN packet with sequence number " + str(self.sendSeq) +
                      ", current state " + self.STATE_DESC[self.state],'green')
        transport.write(finPkt.__serialize__())

    def sendFinAck(self, transport):
        # create FIN Packet
        finAckPkt = RIPPPacket()
        finAckPkt.Type = finAckPkt.TYPE_FIN + finAckPkt.TYPE_ACK
        finAckPkt.AckNo = self.recvSeq
        finAckPkt.updateChecksum()
        self.debug_logger("Sending FIN_ACK packet with seq number " + str(self.sendSeq) +
                    ", ack number " + str(self.recvSeq) + ", current state " + self.STATE_DESC[self.state],'green')
        transport.write(finAckPkt.__serialize__())

    def processDataPkt(self, pkt):
        if self.isClosing():
            self.debug_logger("Closing, ignored data packet with seq " + str(pkt.SeqNo),'red')
        elif pkt.SeqNo == self.recvSeq:  # in order
            self.debug_logger("Received DATA packet with sequence number " +
                  str(pkt.SeqNo),'blue')
            self.recvSeq = pkt.SeqNo + len(
                pkt.Data)
            self.higherProtocol().data_received(pkt.Data)

            while self.recvSeq in self.receivedDataBuffer:
                nextPkt = self.receivedDataBuffer.pop(self.recvSeq)
                self.r = nextPkt.SeqNo + len(nextPkt.Data)
                self.higherProtocol().data_received(nextPkt.Data)
        elif pkt.SeqNo > self.recvSeq:
            self.debug_logger("Received DATA packet with higher sequence number " +
                  str(pkt.SeqNo) + ", put it into buffer.",'blue')
            self.receivedDataBuffer[pkt.SeqNo] = pkt
        else:
            self.debug_logger("ERROR: Received DATA packet with lower sequence number " +
                  str(pkt.SeqNo) + ",current ack_num is : {!r}, discard it.".format(
                        self.recvSeq),'red')
        self.sendAck(self.transport)



    def processAckPkt(self, pkt):
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


