import asyncio
from .RIPPPacket import RIPPPacket
from .RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
import time


class ClientProtocol(RIPPProtocol):
    def __init__(self):
        super().__init__()
        self.transport = None
        self.state = self.CLIENT_INITIAL_SYN
        self.debug_logger("RIPP Client started. State: " + self.CLIENT_INITIAL_SYN,'green')

    def connection_made(self, transport):
        self.transport = transport
        super().connection_made(transport)
        if self.state == self.CLIENT_INITIAL_SYN:
            # Send Syn
            self.sendSyn(self.transport)
            self.sendSeq += 1
            self.state = self.CLIENT_SYN_SNT

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    if ("SYN" in pkt.Type) and ("ACK" in pkt.Type) and (self.state == self.CLIENT_SYN_SNT):
                            # check ack num
                            if pkt.AckNo >= self.sendSeq:
                                self.debug_logger("Received SYN-ACK packet. Seq:{!r} , Ack: {!r} ".format(pkt.SeqNo, pkt.AckNo),'green')
                                self.state = self.CLIENT_ESTABLISHED
                                self.recvSeq = pkt.SeqNo + 1
                                self.sendAck(self.transport)
                                higherTransport = RIPPTransport(self.transport,self)

                                self.higherProtocol().connection_made(higherTransport)
                                self.tasks.append(asyncio.ensure_future(self.checkTimeout()))
                            else:
                                self.debug_logger("Received wrong SYN-ACK packet: Ack: {!r}, expected: {!r}".format(
                                    pkt.AckNo, self.sendSeq + 1),'red')

                    elif ("DATA" in pkt.Type) and (self.state == self.CLIENT_ESTABLISHED):
                        self.recvDataPkt(pkt)

                    elif ("ACK" in pkt.Type) and (self.state == self.CLIENT_ESTABLISHED):
                        self.recvAckPkt(pkt)

                    elif (("FIN" in pkt.Type) and (self.state == self.CLIENT_ESTABLISHED)) or \
                            (("FIN" in pkt.Type) and (self.state == self.CLIENT_FIN_WAIT)):

                        self.debug_logger("Received FIN packet. Seq: {!r}".format(pkt.SeqNo),'green')
                        self.state = self.CLIENT_FIN_WAIT
                        self.recvSeq = pkt.SeqNo + 1
                        self.sendFinAck(self.transport)
                        time.sleep(2)
                        self.state = self.CLIENT_CLOSED
                        self.transport.close()

                    elif ("FIN" in pkt.Type) and ("ACK" in pkt.Type) and (self.state == self.CLIENT_FIN_WAIT):
                        # server's ack for client's fin
                        if pkt.AckNo == (self.sendSeq + 1):
                            self.debug_logger("Received FIN-ACK packet. Ack: {!r}".format(pkt.AckNo),'green')
                            self.state = self.CLIENT_CLOSED
                            self.transport.close()

                    else:
                        self.debug_logger("Wrong packet. Seq: {!r}, Type {!r}".format(pkt.SeqNo, pkt.Type),'red')
                else:
                    self.debug_logger("Wrong packet checksum: {!r}".format(pkt.Checksum),'red')
            else:
                self.debug_logger("Wrong packet class type: {!r}".format(str(type(pkt))),'red')

    def connection_lost(self, exc):
        self.debug_logger("Connection closed.",'red')
        self.higherProtocol().connection_lost(exc)
        self.transport = None

    def shutdown(self):
        self.debug_logger("Client is shutting down...",'red')
        self.state = self.CLIENT_FIN_WAIT
        #self.sendFin(self.transport)
        self.transport.close()


    def isClosing(self):
        return self.state == self.CLIENT_FIN_WAIT or self.state == self.CLIENT_CLOSED

