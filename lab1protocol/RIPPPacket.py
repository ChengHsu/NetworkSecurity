from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import STRING, UINT32, BUFFER
from playground.network.packet.fieldtypes.attributes import Optional
import hashlib


class RIPPPacket(PacketType):

    DEFINITION_IDENTIFIER = "RIPP.Packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Type", STRING),
        ("SeqNo", UINT32({Optional: True})),
        ("AckNo", UINT32({Optional: True})),
        ("Checksum", BUFFER({Optional: True})),
        ("Data", BUFFER({Optional: True}))
    ]

    # RIPPPacket type
    SYN = "SYN"
    ACK = "ACK"
    FIN = "FIN"
    DATA = "DATA"

    def __init__(self):
        super().__init__()
        self.Checksum = b""

    def calculateChecksum(self):
        oldChecksum = self.Checksum
        self.Checksum = b""
        bytes = self.__serialize__()
        self.Checksum = oldChecksum
        return hashlib.sha256(bytes).digest()

    def updateChecksum(self):
        self.Checksum = self.calculateChecksum()

    def verifyChecksum(self):
        return self.Checksum == self.calculateChecksum()


