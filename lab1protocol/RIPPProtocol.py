import asyncio
import random
import time

from playground.network.common import StackingProtocol
from .RIPPPacket import RIPPPacket
from termcolor import colored


class RIPPProtocol(StackingProtocol):
    # Constants
    WINDOW_SIZE = 150
    TIMEOUT = 3
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
        self.sentDataBuffer = {}
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
        self.debug_logger ("Sending SYN packet. Seq:{!r} ".format(self.sendSeq),'green')
        transport.write(synPkt.__serialize__())


    def sendSynAck(self, transport, synAck_seqNum):
        # create SYN-ACK Packet
        synAckPkt = RIPPPacket()
        synAckPkt.Type = synAckPkt.SYN + synAckPkt.ACK
        synAckPkt.SeqNo = synAck_seqNum
        synAckPkt.AckNo = self.recvSeq
        synAckPkt.updateChecksum()
        self.debug_logger("Sending SYN-ACK packet. Seq:{!r}, Ack: {!r}".format(synAck_seqNum,self.recvSeq),'green')
        transport.write(synAckPkt.__serialize__())

    def sendAck(self, transport):
        # create ACK Packet
        ackPkt = RIPPPacket()
        ackPkt.Type = ackPkt.ACK
        ackPkt.AckNo = self.recvSeq
        ackPkt.updateChecksum()
        self.debug_logger("Sending ACK packet. Ack:{!r}, current state: {!r} ".format(self.recvSeq,self.state),'green')
        transport.write(ackPkt.__serialize__())

    def sendFin(self, transport):
        # create FIN Packet
        finPkt = RIPPPacket()
        finPkt.Type = finPkt.FIN
        finPkt.SeqNo = self.sendSeq
        finPkt.updateChecksum()
        self.debug_logger("Sending FIN packet. Seq:{!r}, current state:{!r}".format(self.sendSeq,self.state),'green')
        transport.write(finPkt.__serialize__())

    def sendFinAck(self, transport):
        # create FIN Packet
        finAckPkt = RIPPPacket()
        finAckPkt.Type = finAckPkt.FIN + finAckPkt.ACK
        finAckPkt.AckNo = self.recvSeq
        finAckPkt.updateChecksum()
        self.debug_logger("Sending FIN_ACK packet. Seq:{!r}, Ack:{!r}, current state:{!r}".format(self.sendSeq,self.recvSeq,self.state),'green')
        transport.write(finAckPkt.__serialize__())

    def recvDataPkt(self, pkt):
        if self.isClosing():
            self.debug_logger("Closing, discarded data packet.  Seq:{!r}".format(pkt.SeqNo),'red')
        elif pkt.SeqNo == self.recvSeq:
            self.debug_logger("Received DATA packet.  Seq:{!r}".format(pkt.SeqNo),'blue')
            self.recvSeq = pkt.SeqNo + len(
                pkt.Data)
            self.higherProtocol().data_received(pkt.Data)

            while self.recvSeq in self.receivedDataBuffer:
                nextPkt = self.receivedDataBuffer.pop(self.recvSeq)
                self.r = nextPkt.SeqNo + len(nextPkt.Data)
                self.higherProtocol().data_received(nextPkt.Data)
        elif pkt.SeqNo > self.recvSeq:
            self.debug_logger("Received Data packet with bigger Seq:{!r} , {!r} expected.".format(pkt.SeqNo,self.recvSeq),'blue')
            self.receivedDataBuffer[pkt.SeqNo] = pkt
        else:
            self.debug_logger("Received DATA packet with smaller Seq:{!r}, {!r} expected.".format(pkt.SeqNo,self.recvSeq),'red')
        self.sendAck(self.transport)



    def recvAckPkt(self, pkt):
        self.debug_logger("Received ACK packet. Ack:{!r}".format(pkt.AckNo),'blue')
        latestAckNumber = pkt.AckNo
        #selective
        # if latestAckNumber in self.sentDataBuffer:
        #     if len(self.sendingDataBuffer) > 0:
        #         (nextAck, dataPkt) = self.sendingDataBuffer.pop(0)
        #         self.debug_logger("Sending next packet " + str(nextAck) + " in sendingDataBuffer...",'blue')
        #         self.sentDataBuffer[nextAck] = (dataPkt, time.time())
        #         self.transport.write(dataPkt.__serialize__())
        #     self.debug_logger("Received ACK for dataSeq: {!r}, removing".format(self.sentDataBuffer[latestAckNumber][0].SeqNo),'blue')
        #     del self.sentDataBuffer[latestAckNumber]
        for ackNumber in list(self.sentDataBuffer):
            # cumulative
            if ackNumber <= latestAckNumber:
                if len(self.sendingDataBuffer) > 0:
                    (nextAck, dataPkt) = self.sendingDataBuffer.pop(0)
                    self.debug_logger("Sending next packet " + str(nextAck) + " in sendingDataBuffer...",'blue')
                    self.sentDataBuffer[nextAck] = (dataPkt, time.time())
                    self.transport.write(dataPkt.__serialize__())
                self.debug_logger("Received ACK for packet with Seq: {!r}, removing".format(self.sentDataBuffer[ackNumber][0].SeqNo),'blue')
                del self.sentDataBuffer[ackNumber]


    async def checkTimeout(self):
        while not self.isClosing():
            for ackNumber in self.sentDataBuffer:
                (dataPkt, timestamp) = self.sentDataBuffer[ackNumber]
                currentTime = time.time()
                if currentTime - timestamp >= self.TIMEOUT:
                    self.debug_logger("Resending packet " + str(dataPkt.SeqNo) + " in cache...",'red')
                    self.transport.write(dataPkt.__serialize__())
                    self.sentDataBuffer[ackNumber] = (dataPkt, currentTime)
            await asyncio.sleep(self.SCAN_INTERVAL)


    def debug_logger(self, text,color):
        if self.DEBUG_MODE:
            print(colored(type(self).__name__ + ": " + text,color))


