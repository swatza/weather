'''
Balloon Reader is a process to read in from a board sensor that communicates with several (up to 4) drifting balloons for teh summer research project
'''
import time
import sys
import Queue
import threading
import socket
import logging
import argparse


sys.path.insert(0,'../PyUAS')
sys.path.insert(0,'../PyUAS/protobuf')
import PyPacket
import PyPackets_pb2
import assorted_lib
#import PyPacketLogger doesn't exist until we push the code from desktop

shutdown_event = Threading.Event()
msg_queue = Queue.Queue()

class WritingThread(threading.Thread):
	def __init__(self, socket, NMPort):
		threading.Thread.__init__(self)
		self.socket = socket
		self.NM_PORT = NMPort
		
		#Create logger
		
	def run(self):
	
		#Don't care about subscribers at this point
		while not shutdown_event.is_set():
			try:
				next_msg = msg_queue.get_nowait()
			except Queue.Empty:
				time.sleep(0.01)
			else:
				self.socket.sendto(next_msg,('localhost',self.NM_PORT))
				#Log message
				
		#End of while loop
		self.socket.close()
		#Log message 
		
class ReadFromSensor(threading.Thread):
	def __init__(self,serialPort,readrate):
		pass
	
	def run(self):
		pass
		
		
'''
main runtime
'''
if __name__ == "__main__":
	#create logger
	
	#Arguments?
	parser = argparse.ArgumentParser(desription='Balloon Sensor Reader for Drifters')
	parser.add_argument("COMMPORT",type=str)
	parser.add_argument("BALLON#",type=int)
	
	args = parser.parse_args()
	
	COMMPORT = args.COMMPORT
	
	NM_PORT = 16000 #hardcoded for now
	SensorRate = 1 #1 second 
	
	#Create socket
	s_out = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	
	#start each of the threads
	Sensor = ReadFromSensor(COMMPORT,SensorRate)
	Sensor.start()
	wthread = WritingThread(s_out,NM_PORT)
	wthread.start()

	while threading.active_count() > 1:
		try:
			time.sleep(1)
		except (KeyboardInterrupt, SystemExit):
			shutdown_event.set()
			#log messages
			
	sys.exit()