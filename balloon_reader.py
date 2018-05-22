'''
Balloon Reader is a process to read in from a board sensor that communicates with several (up to 4) drifting balloons for the summer research project
'''
import time
import sys
import Queue
import threading
import socket
import logging
import argparse
import serial


sys.path.insert(0,'../PyUAS')
sys.path.insert(0,'../PyUAS/protobuf')
import PyPacket
import PyPackets_pb2
import assorted_lib
#import PyPacketLogger doesn't exist until we push the code from desktop

shutdown_event = threading.Event()
msg_queue = Queue.Queue()

def write_buffer(drifter,remote_data,rem_id,rssi):
    if remote_data is not None:
        drifter.packetNum = 1
        drifter.ID = str(rem_id)
        drifter.rssi = float(rssi)
        drifter.time = float(remote_data[9])
        drifter.LLA_Pos.x = float(remote_data[3])
        drifter.LLA_Pos.y = float(remote_data[4])
        drifter.LLA_Pos.z = float(remote_data[5])
        drifter.pthsensor.pressure = float(remote_data[6])
        drifter.pthsensor.temperature = float(remote_data[7])
        drifter.pthsensor.humidity = float(remote_data[8])
        drifter.battery.voltage = float(remote_data[10])
        drifter.Vel.x = float(remote_data[12])
        drifter.Vel.y = float(remote_data[11])
        drifter.Vel.z = 0

    else:
        drifter.packetNum = 1
        drifter.ID = str(0)
        drifter.rssi = 0
        drifter.time = 0
        drifter.LLA_Pos.x = 0
        drifter.LLA_Pos.y = 0
        drifter.LLA_Pos.z = 0
        drifter.pthsensor.pressure = 0
        drifter.pthsensor.temperature = 0
        drifter.pthsensor.humidity = 0
        drifter.battery.voltage = 0
        drifter.Vel.x = 0
        drifter.Vel.y = 0
        drifter.Vel.z = 0

     
def ParseData(fn,counter,myID):
    balloon_msg = PyPackets_pb2.Balloon_Sensor_Set_Msg()        
    balloon_msg.packetNum = counter
    balloon_msg.ID = myID
    balloon_msg.time = time.time()
    
    #drifnum = nballoon
    #size of each data packet is ~218 bytes +/- 2 bytes
    drifnum = 1 #fn.inWaiting()/218
    balloon_msg.NumberOfBalloons = drifnum
    drifterStrs = []
    if fn is not None:
        for i in range(drifnum):
            drifterStrs.append(fn.readline())
            drifter = balloon_msg.balloon.add()
            #print("This is the length of the data sample %i" % len(drifterStrs[0]))
            raw = drifterStrs[i].split()
            #print("This is the size of the split string %i" % len(raw))
            if len(raw) == 0:
                return None

            ms_since_boot = raw[1]
            rem_id = raw[2]
            rssi = raw[3]
            rnge = raw[4]
            azimuth = raw[5]
            raw_data = raw[6]

            local_data = raw[7].split(',')
            loc_vel = local_data[4]
            loc_course = local_data[5]
            loc_date = local_data[6]
            loc_time = local_data[7]

            remote_data = raw[8].split(',')

            balloon_msg.receiverLLA_Pos.x = float(local_data[1])
            balloon_msg.receiverLLA_Pos.y = float(local_data[2])
            balloon_msg.receiverLLA_Pos.z = float(local_data[3])

            write_buffer(drifter,remote_data,rem_id,rssi)
    else:
        for i in range(drifnum):
            drifter = balloon_msg.balloon.add()
            write_buffer(drifter,None,0,0)
            balloon_msg.receiverLLA_Pos.x = 0.0
            balloon_msg.receiverLLA_Pos.y = 1.0
            balloon_msg.receiverLLA_Pos.z = 2.0
    
    return balloon_msg.SerializeToString()
        
class WritingThread(threading.Thread):
    def __init__(self, socket, NMPort,Logmode):
        threading.Thread.__init__(self)
        self.socket = socket
        self.NM_PORT = NMPort
		
        #Create logger
        self.logger = logging.getLogger("BalloonReader:WritingThread")
        self.logger.setLevel(Logmode)
        myhandler = logging.StreamHandler()
        self.logger.addHandler(myhandler)
        self.logger.info("Writing Thread has started")
  
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
                self.logger.info("Sent Message to Network Manager")
    				
        #End of while loop
        self.socket.close()
        #Log message
        self.logger.info("Closing Writing Thread")
		
class ReadFromSensor(threading.Thread):
	def __init__(self,serialPort,readrate,myIDnum,Logmode):
         threading.Thread.__init__(self)
        #Create loggers and put them here     
         self.logger = logging.getLogger("BalloonReader:SensorThread")
         self.logger.setLevel(Logmode)
         myhandler = logging.StreamHandler()
         self.logger.addHandler(myhandler)
         self.logger.info("Sensor Thread has started")
     
         #self.serialPortname = serialPort
         if serialPort is None:
             self.fn = None
         else:
            self.fn = serial.Serial(port = serialPort,timeout=1)
         #check that this opened and throw a critical error otherwise
         self.readrate = readrate
         
         thisid = PyPacket.PacketID(PyPacket.PacketPlatform.AIRCRAFT,myIDnum)
         self.MYID = str(thisid.getBytes())
         
         self.PyPkt = PyPacket.PyPacket()
         self.PyPkt.setDataType(PyPacket.PacketDataType.PKT_BALLOON_SENSOR_SET)
         self.PyPkt.setID(thisid.getBytes())

	
	def run(self):
         counter = 0
         
         while not shutdown_event.is_set():
             counter += 1
             datastr = ParseData(self.fn,counter,self.MYID)
             if datastr is not None:
                 self.PyPkt.setData(datastr)
                 msg_queue.put(self.PyPkt.getPacket())
                 self.logger.info("Packet Built and added to Queue")
             else:
                 time.sleep(0.1)
             #log message for pyPacketlogger when added
        #endof while loop
        #send log message ending loop
		
		
'''
main runtime
'''
if __name__ == "__main__":
	#create logger
	
	#Arguments?
    parser = argparse.ArgumentParser(description='Balloon Sensor Reader for Drifters')
    parser.add_argument("COMMPORT",type=str)
    parser.add_argument("BALLOON",type=int)
	
    args = parser.parse_args()
	
    COMMPORT = args.COMMPORT
    if COMMPORT == "None":
        COMMPORT = None
    
    numid = args.BALLOON
    NM_PORT = 16000 #hardcoded for now
    SensorRate = 1 #1 second 
	
    #Create socket
    s_out = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	
    #start each of the threads
    Logmode = logging.DEBUG
    Sensor = ReadFromSensor(COMMPORT,SensorRate,numid,Logmode)
    Sensor.start()
    wthread = WritingThread(s_out,NM_PORT,Logmode)
    wthread.start()

    while threading.active_count() > 3:
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            shutdown_event.set()
            #log messages
			
    sys.exit()