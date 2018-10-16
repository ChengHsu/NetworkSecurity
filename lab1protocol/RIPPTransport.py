from playground.network.common import StackingTransport
from .RIPPPacket import RIPPPacket
import time

class RIPPTransport(StackingTransport):
    CHUNK_SIZE = 1500

    def __init__(self, transport, protocol=None):
        super().__init__(transport)
        self.protocol = protocol

    def write(self, data):
        if self.protocol:
            if not self.protocol.isClosing():
                i = 0
                index = 0
                sentData = None
                while i < len(data):
                    if i + self.CHUNK_SIZE < len(data):
                        sentData = data[i: i + self.CHUNK_SIZE]
                    else:
                        sentData = data[i:]
                    i += len(sentData)

                    #create a data packet
                    dataPkt = RIPPPacket()
                    dataPkt.Type = dataPkt.TYPE_DATA
                    dataPkt.SeqNo = self.protocol.sendSeq
                    dataPkt.Data = sentData
                    dataPkt.updateChecksum()

                    index += 1
                    ackNumber = self.protocol.sendSeq + len(sentData)

                    if len(self.protocol.sentDataCache) <= self.protocol.WINDOW_SIZE:
                        self.protocol.debug_logger("Sending packet {!r}, sequence number: {!r}".format(index,
                                                                                               dataPkt.SeqNo),'blue')
                        self.protocol.transport.write(dataPkt.__serialize__())
                        self.protocol.sentDataCache[ackNumber] = (dataPkt, time.time())

                    else:
                        self.protocol.debug_logger("RIIPTransport: Buffering packet {!r}, sequence number: {!r}".format(index,
                                                                                                 dataPkt.SeqNo),'blue')
                        # Window is full, put pkt into sending buffer
                        self.protocol.sendingDataBuffer.append((ackNumber, dataPkt))
                    self.protocol.sendSeq += len(sentData)
                self.protocol.debug_logger("RIPPTransport: Batch transmission finished, number of packets sent: {!r}".format(index),'blue')
            else:
                self.protocol.debug_logger("RIPPTransport: protocol is closing, unable to write anymore.",'red')

        else:
            self.protocol.debug_logger("RIPPTransport: Undefined protocol, writing anyway...",'red')
            self.protocol.debug_logger("RIPPTransport: Write got {} bytes of data to pass to lower layer".format(len(data)),'blue')
            super().write(data)

    def close(self):
        if not self.protocol.isClosing():
            self.protocol.debug_logger("Protpcol shut down...",'red')
            self.protocol.shutdown()
        else:
            self.protocol.debug_logger("RIIPTransport: Protocol is already closing.",'red')