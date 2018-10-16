import asyncio
from .RIPPPacket import RIPPPacket
from .RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
import time

class ServerProtocol(RIPPProtocol):
    def __init__(self):
        super().__init__()
        self.state = self.STATE_SERVER_LISTEN
        self.debug_logger("Initialized server with state " +
                      self.STATE_DESC[self.state],'green')
    def connection_made(self, transport):
        self.transport = transport


    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    if ("SYN" in pkt.Type) and (self.state == self.STATE_SERVER_LISTEN):
                        self.debug_logger("Received SYN packet with seq number " +
                                      str(pkt.SeqNo),'blue')
                        self.state = self.STATE_SERVER_SYN_RCVD
                        self.recvSeq = pkt.SeqNo + 1
                        synAck_seq = self.sendSeq
                        self.sendSynAck(self.transport, synAck_seq)
                        self.sendSeq += 1

                    elif ("ACK" in pkt.Type) and (self.state == self.STATE_SERVER_SYN_RCVD):

                        if pkt.AckNo == self.sendSeq:
                            self.debug_logger("Received ACK packet with ack number " + str(pkt.AckNo),'blue')
                            # Do not change sendSeq; follow the specifications
                            # self.recvSeq = pkt.SeqNo + 1
                            self.state = self.STATE_SERVER_TRANSMISSION

                            higherTransport = RIPPTransport(self.transport,self)
                            self.higherProtocol().connection_made(higherTransport)
                            self.tasks.append(asyncio.ensure_future(self.checkTimeout()))
                        else:
                            self.debug_logger(
                                "Server: Wrong ACK packet: ACK number: {!r}, expected: {!r}".format(
                                    pkt.AckNo, self.sendSeq + 1),'red')

                    elif ("DATA" in pkt.Type) and (self.state == self.STATE_SERVER_TRANSMISSION):
                        self.processDataPkt(pkt)

                    elif ("ACK" in pkt.Type) and (self.state == self.STATE_SERVER_TRANSMISSION):
                        self.processAckPkt(pkt)

                    elif (("FIN" in pkt.Type) and (self.state == self.STATE_SERVER_TRANSMISSION)) or \
                            (("FIN" in pkt.Type) and (self.state == self.STATE_SERVER_FIN_WAIT)):
                        self.debug_logger("Received FIN packet with sequence number " +
                              str(pkt.SeqNo),'blue')
                        self.state = self.STATE_SERVER_FIN_WAIT
                        self.recvSeq = pkt.SeqNo + 1
                        self.sendFinAck(self.transport)
                        time.sleep(2)
                        self.state = self.STATE_SERVER_CLOSED
                        self.transport.close()

                    elif ("FIN" in pkt.Type) and ("ACK" in pkt.Type) and (self.state == self.STATE_SERVER_FIN_WAIT):
                        if pkt.AckNo == (self.sendSeq + 1):
                            self.debug_logger("Received FIN_ACK packet with ack number " + str(pkt.AckNo),'blue')
                            self.state = self.STATE_SERVER_CLOSED
                            self.transport.close()

                    else:
                        self.debug_logger("Server: Wrong packet: seq num {!r}".format(
                            pkt.SeqNo),'red')
                else:
                    self.debug_logger("Wrong packet checksum: " + str(pkt.Checksum),'red')
            else:
                self.debug_logger("Wrong packet class type: {!r}".format(str(type(pkt))),'red')

    def connection_lost(self, exc):
        self.debug_logger("Connection closing...",'red')
        self.higherProtocol().connection_lost(exc)
        self.transport = None

    def shutdown(self):
        self.debug_logger("Server is preparing for FIN...",'red')
        self.state = self.STATE_SERVER_FIN_WAIT
        #self.sendFin(self.transport)
        self.transport.close()



    def isClosing(self):
        return self.state == self.STATE_SERVER_FIN_WAIT or self.state == self.STATE_SERVER_CLOSED