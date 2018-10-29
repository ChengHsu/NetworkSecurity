from playground.network.common import StackingTransport
from .RIPPPacket import RIPPPacket
import time
from .Timer import Timer
from .Timer import PopTimer
import asyncio


class RIPPTransport(StackingTransport):

	def __init__(self, transport, protocol=None):
		super().__init__(transport)
		self.protocol = protocol
		self.pop_timer = None

	def force_to_pop(self):
		if len(self.protocol.sendingDataBuffer) > 0:
			(nextAck, dataPkt) = self.protocol.sendingDataBuffer.pop(0)
			self.protocol.debug_logger("Sending data packet {} in sendingDataBuffer...".format(nextAck),'blue')
			self.protocol.transport.write(dataPkt.__serialize__())
			self.protocol.sentDataBuffer[nextAck] = (dataPkt, time.time())
			timer = Timer(self.protocol.TIMEOUT,self.protocol.loop, self.protocol.data_timeout, nextAck)
			self.protocol.timer_dict[nextAck] = timer
			self.pop_timer = PopTimer(self.protocol.POP_TIMEOUT,self.protocol.loop, self.force_to_pop)

	def write(self, data):
		if not self.protocol.isClosing():

			curr_size = 0
			pktNo = 0
			sentData = None
			#Chunky
			while curr_size < len(data):
				if curr_size + self.protocol.MTU < len(data):
					sentData = data[curr_size: curr_size + self.protocol.MTU]
				else:
					sentData = data[curr_size:]
				curr_size += len(sentData)

				# create a data packet
				dataPkt = RIPPPacket()
				dataPkt.Type = dataPkt.DATA
				dataPkt.SeqNo = self.protocol.sendSeq
				dataPkt.Data = sentData
				dataPkt.updateChecksum()

				pktNo += 1
				ackNumber = self.protocol.sendSeq + len(sentData)

				# Window is not full
				if len(self.protocol.sentDataBuffer) <= self.protocol.WINDOW_SIZE:
					self.protocol.debug_logger("Sending packet {!r}, sequence number: {!r}".format(pktNo,dataPkt.SeqNo),'blue')
					self.protocol.transport.write(dataPkt.__serialize__())
					self.protocol.sentDataBuffer[ackNumber] = (dataPkt,time.time())
					# Set data pkt retransmission timer
					timer = Timer(self.protocol.TIMEOUT, self.protocol.loop, self.protocol.data_timeout,ackNumber)
					self.protocol.timer_dict[ackNumber] = timer
					#Set pop timer
					self.pop_timer = PopTimer(self.protocol.POP_TIMEOUT, self.protocol.loop, self.force_to_pop)

				# Window is full, sending to sendingDataBuffer
				else:
					self.protocol.debug_logger(
						"RIIPTransport: Buffering packet {!r}, sequence number: {!r}".format(pktNo,dataPkt.SeqNo), 'blue')
					self.protocol.sendingDataBuffer.append((ackNumber, dataPkt))

				self.protocol.sendSeq += len(sentData)
			self.protocol.debug_logger(
				"RIPPTransport: Data transmission completed, sent: {!r} packets".format(pktNo), 'blue')

		else:
			self.protocol.debug_logger("RIPPTransport: Failed to write.", 'red')


	def close(self):
		if not self.protocol.isClosing():
			self.protocol.shutdown(0)
			self.pop_timer.cancel()
		else:
			self.protocol.debug_logger("RIIPTransport: Protocol is in closing state.", 'red')
