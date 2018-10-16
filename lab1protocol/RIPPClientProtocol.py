import asyncio
from .RIPPPacket import RIPPPacket
from .RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
import time

from termcolor import colored


class ClientProtocol(RIPPProtocol):
    def __init__(self):
        super().__init__()
        self.transport = None
        self.state = self.STATE_CLIENT_INITIAL_SYN
        self.debug_logger("Initialized client with state " +
                      self.STATE_DESC[self.state],'green')

    def connection_made(self, transport):
        self.transport = transport
        super().connection_made(transport)
        if self.state == self.STATE_CLIENT_INITIAL_SYN:
            # Send Syn
            self.sendSyn(self.transport)
            self.sendSeq += 1
            self.state = self.STATE_CLIENT_SYN_SNT

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    if ("SYN" in pkt.Type) and ("ACK" in pkt.Type) and (self.state == self.STATE_CLIENT_SYN_SNT):
                            # check ack num
                            if (pkt.AckNo >= self.sendSeq):
                                self.debug_logger("Received SYN-ACK packet with sequence number " +
                                              str(pkt.SeqNo) + ", ack number " +
                                              str(pkt.AckNo),'green')
                                self.state = self.STATE_CLIENT_TRANSMISSION
                                self.recvSeq = pkt.SeqNo + 1
                                self.sendAck(self.transport)
                                higherTransport = RIPPTransport(self.transport,self)

                                self.higherProtocol().connection_made(higherTransport)
                                self.tasks.append(asyncio.ensure_future(self.checkTimeout()))
                            else:
                                self.debug_logger("Client: Wrong SYN_ACK packet: ACK number: {!r}, expected: {!r}".format(
                                    pkt.AckNo, self.sendSeq + 1),'red')

                    elif ("DATA" in pkt.Type) and (self.state == self.STATE_CLIENT_TRANSMISSION):
                        self.processDataPkt(pkt)

                    elif ("ACK" in pkt.Type) and (self.state == self.STATE_CLIENT_TRANSMISSION):
                        self.processAckPkt(pkt)

                    elif (("FIN" in pkt.Type) and (self.state == self.STATE_CLIENT_TRANSMISSION)) or \
                            (("FIN" in pkt.Type) and (self.state == self.STATE_CLIENT_FIN_WAIT)):
                        self.debug_logger("Received FIN packet with sequence number " +
                              str(pkt.SeqNo),'green')
                        self.state = self.STATE_CLIENT_FIN_WAIT
                        self.recvSeq = pkt.SeqNo + 1
                        self.sendFinAck(self.transport)
                        time.sleep(2)
                        self.state = self.STATE_CLIENT_CLOSED
                        self.transport.close()

                    elif ("FIN" in pkt.Type) and ("ACK" in pkt.Type) and (self.state == self.STATE_CLIENT_FIN_WAIT):
                        # server's ack for client's fin
                        if pkt.AckNo == (self.sendSeq + 1):
                            print("Received FIN_ACK packet with ack number " + str(pkt.AckNo))
                            self.state = self.STATE_CLIENT_CLOSED
                            self.transport.close()

                    else:
                        self.debug_logger("Client: Wrong packet: seq num {!r}, type {!r}".format(
                            pkt.SeqNo, pkt.Type),'red')
                else:
                    self.debug_logger("Wrong packet checksum: " + str(pkt.Checksum),'red')
            else:
                self.debug_logger("Wrong packet class type: {!r}".format(str(type(pkt))),'red')

    def connection_lost(self, exc):
        self.debug_logger("Connection closing...",'red')
        self.higherProtocol().connection_lost(exc)
        self.transport = None

    def shutdown(self):
        self.debug_logger("Client is preparing for FIN...",'red')
        self.state = self.STATE_CLIENT_FIN_WAIT
        # self.sendFin(self.transport)
        self.transport.close()



    def isClosing(self):
        return self.state == self.STATE_CLIENT_FIN_WAIT or self.state == self.STATE_CLIENT_CLOSED

