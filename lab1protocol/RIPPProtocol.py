import asyncio
import random
import time
import os
from .Timer import Timer

from playground.network.common import StackingProtocol
from .RIPPPacket import RIPPPacket
#from termcolor import colored


class RIPPProtocol(StackingProtocol):
    # Parameters
    WINDOW_SIZE = 50
    TIMEOUT = 0.5
    POP_TIMEOUT = 0.4
    MAX_TIMEOUT = 4
    DEBUG_MODE = True
    MTU = 1500

    # State
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
        self.syn_pkt = None
        self.syn_ack_pkt = None
        self.timer_dict = {}
        self.loop = asyncio.get_event_loop()


    def sendSyn(self,transport):
        self.transport = transport
        #create SYN Packet
        synPkt = RIPPPacket()
        synPkt.Type = synPkt.SYN
        synPkt.SeqNo = self.sendSeq
        synPkt.updateChecksum()
        self.debug_logger ("Sending SYN packet. Seq:{!r} ".format(self.sendSeq),'green')
        self.syn_pkt = synPkt.__serialize__()
        transport.write(self.syn_pkt)


    def sendSynAck(self, transport, synAck_seqNum):
        # create SYN-ACK Packet
        synAckPkt = RIPPPacket()
        synAckPkt.Type = synAckPkt.SYN + synAckPkt.ACK
        synAckPkt.SeqNo = synAck_seqNum
        synAckPkt.AckNo = self.recvSeq
        synAckPkt.updateChecksum()
        self.debug_logger("Sending SYN-ACK packet. Seq:{!r}, Ack: {!r}".format(synAck_seqNum,self.recvSeq),'green')
        #add
        self.syn_ack_pkt = synAckPkt.__serialize__()
        transport.write(self.syn_ack_pkt)

    def sendAck(self, transport):
        # create ACK Packet
        ackPkt = RIPPPacket()
        ackPkt.Type = ackPkt.ACK
        ackPkt.AckNo = self.recvSeq
        ackPkt.updateChecksum()
        self.debug_logger("Sending ACK packet. Ack:{!r}, current state: {!r} ".format(self.recvSeq,self.state),'green')
        transport.write(ackPkt.__serialize__())

    def sendRetransAck(self, transport, ackNum):
        # create ACK Packet for retransmitted packet
        ackPkt = RIPPPacket()
        ackPkt.Type = ackPkt.ACK
        ackPkt.AckNo = ackNum
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
            self.sendAck(self.transport)

        elif pkt.SeqNo == self.recvSeq:
            self.debug_logger("Received DATA packet.  Seq:{!r}".format(pkt.SeqNo),'blue')
            self.recvSeq = pkt.SeqNo + len(pkt.Data)
            self.sendAck(self.transport)
            self.higherProtocol().data_received(pkt.Data)
            while self.recvSeq in self.receivedDataBuffer:
                nextPkt = self.receivedDataBuffer.pop(self.recvSeq)
                self.recvSeq = nextPkt.SeqNo + len(nextPkt.Data)
                self.higherProtocol().data_received(nextPkt.Data)
                self.sendAck(self.transport)

        elif pkt.SeqNo > self.recvSeq:
            self.debug_logger("Received Data packet with bigger Seq:{!r} , {!r} expected.".format(pkt.SeqNo,self.recvSeq),'blue')
            self.receivedDataBuffer[pkt.SeqNo] = pkt
        else:
            self.debug_logger("Received DATA packet with smaller Seq:{!r}, {!r} expected.".format(pkt.SeqNo,self.recvSeq),'red')
            ackNum = pkt.SeqNo + len(pkt.Data)
            self.sendRetransAck(self.transport,ackNum)


    def recvAckPkt(self, pkt):
        self.debug_logger("Received ACK packet. Ack:{!r} WIND:{!r}".format(pkt.AckNo,self.WINDOW_SIZE),'blue')
        latestAckNumber = pkt.AckNo

        #selective
        # while latestAckNumber in list(self.timer_dict):
        #     self.timer_dict[latestAckNumber].cancel()
        #     del self.timer_dict[latestAckNumber]
        #     break
        # while latestAckNumber in list(self.sentDataBuffer):
        #     del self.sentDataBuffer[latestAckNumber]
        #     break

        #acumulative
        acks = list(self.timer_dict.keys())
        for ack in acks:
            if ack <= latestAckNumber:
                print("cancel ack: {}".format(ack))
                (self.timer_dict[ack]).cancel()
                self.timer_dict.pop(ack)

        for ackNumber in list(self.sentDataBuffer):
            if ackNumber <= latestAckNumber:
                self.debug_logger(
                    "Received ACK for packet with Seq: {!r}, removing".format(self.sentDataBuffer[ackNumber][0].SeqNo),
                    'blue')
                del self.sentDataBuffer[ackNumber]

    def data_timeout(self,ackNo):
        while ackNo in list(self.sentDataBuffer):
            (dataPkt, timestamp) = self.sentDataBuffer[ackNo]
            current_time = time.time()
            if current_time - timestamp < self.MAX_TIMEOUT:
                self.transport.write(dataPkt.__serialize__())
                self.debug_logger("Retransmit data packet with SeqNo: " + str(dataPkt.SeqNo),'blue')
                self.sentDataBuffer[ackNo] = (dataPkt, timestamp)
                timer = Timer(self.TIMEOUT, self.loop, self.data_timeout, ackNo)
                self.timer_dict[ackNo] = timer
            break


    def debug_logger(self, text,color):
        if self.DEBUG_MODE:
            print(type(self).__name__ + ": " + text)
            #print(colored(type(self).__name__ + ": " + text,color))

    def close_timers(self):
        self.debug_logger("Cancel all the timers.", 'green')
        for k,v in self.timer_dict.items():
            v.cancel()

