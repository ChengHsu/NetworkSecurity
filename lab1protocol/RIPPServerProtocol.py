import asyncio
from .RIPPPacket import RIPPPacket
from .RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
from .Timer import Timer
import time

class ServerProtocol(RIPPProtocol):
    def __init__(self):
        super().__init__()
        self.state = self.SERVER_LISTEN
        self.debug_logger("RIPP Server with state " + self.SERVER_LISTEN, 'green')

    def connection_made(self, transport):
        self.transport = transport
        super().connection_made(transport)

    def data_received(self, data):
        # Set stop timer
        stop_timer = Timer(30,self.loop,self.shutdown,0)

        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    # SYN
                    if ("SYN" in pkt.Type) and (self.state == self.SERVER_LISTEN):
                        self.debug_logger("Received SYN packet. Seq: {!r} ".format(pkt.SeqNo),'blue')
                        self.state = self.SERVER_SYN_RCVD
                        self.recvSeq = pkt.SeqNo + 1
                        synAck_seq = self.sendSeq
                        self.sendSynAck(self.transport, synAck_seq)
                        self.sendSeq += 1

                    # ACK for SYN-ACK
                    elif ("ACK" in pkt.Type) and (self.state == self.SERVER_SYN_RCVD):

                        if pkt.AckNo == self.sendSeq:
                            self.debug_logger("Received ACK for SYN-ACK packet. Ack:{!r} ".format(pkt.AckNo),'blue')
                            self.state = self.SERVER_ESTABLISHED
                            higherTransport = RIPPTransport(self.transport,self)
                            self.higherProtocol().connection_made(higherTransport)

                        else:
                            self.debug_logger(
                                "Wrong ACK packet. ACK: {!r}, expected: {!r}".format(
                                    pkt.AckNo, self.sendSeq + 1),'red')

                    # DATA
                    elif ("DATA" in pkt.Type) and (self.state == self.SERVER_ESTABLISHED or self.state == self.SERVER_LISTEN):
                        self.recvDataPkt(pkt)

                    # ACK
                    elif ("ACK" in pkt.Type) and (self.state != self.SERVER_CLOSED):
                        self.recvAckPkt(pkt)

                    # FIN
                    elif (("FIN" in pkt.Type) and (self.state == self.SERVER_ESTABLISHED)) or \
                            (("FIN" in pkt.Type) and (self.state == self.SERVER_FIN_WAIT)):
                        # After receiving FIN, sending FIN-ACk and close
                        self.debug_logger("Received FIN packet. Seq:{!r} ".format(pkt.SeqNo),'blue')

                        self.state = self.SERVER_FIN_WAIT
                        self.recvSeq = pkt.SeqNo + 1
                        self.sendFinAck(self.transport)
                        time.sleep(2)
                        self.state = self.STATE_SERVER_CLOSED
                        self.transport.close()

                    # FIN-ACK
                    elif ("FIN" in pkt.Type) and ("ACK" in pkt.Type) and (self.state == self.SERVER_FIN_WAIT):
                        if pkt.AckNo == (self.sendSeq + 1):
                            self.debug_logger("Received FIN_ACK packet. Ack:{!r}".format(pkt.AckNo),'blue')
                            self.state = self.STATE_SERVER_CLOSED
                            self.transport.close()

                    else:
                        self.debug_logger("Wrong Pkt with Seq: {!r}. Type: {!r}. Current State:{!r}".format(pkt.SeqNo,pkt.Type,self.state),'red')
                else:
                    self.debug_logger("Wrong packet. Seq:{!r}. Checksum:{!r}".format(pkt.SeqNo,pkt.Checksum),'red')
            else:
                self.debug_logger("Wrong packet class type: {!r}".format(str(type(pkt))),'red')

    def connection_lost(self, exc):
        self.debug_logger("Connection closed...",'red')
        self.higherProtocol().connection_lost(exc)
        self.transport = None
        self.loop.stop()

    def shutdown(self,arg):
        self.debug_logger("Server is shutting down...",'red')
        self.close_timers()
        self.state = self.SERVER_FIN_WAIT
        self.transport.close()

    def isClosing(self):
        return self.state == self.SERVER_FIN_WAIT or self.state == self.SERVER_CLOSED


