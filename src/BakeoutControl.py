import threading
import Queue
from BakeoutEnumeration import *

COMMAND = {"START_STOP": 0x00,
           "PAUSE": 0x01,
           "FEED": 0x02}          

#===============================================================================
#
# BakeoutController Class
#
#===============================================================================
class BakeoutController(threading.Thread):
    def __init__(self, bakeoutControlDS, name="Thread-BakeoutController"):
        threading.Thread.__init__(self, name=name)

        self._ds = bakeoutControlDS
        self._programs = dict.fromkeys((i for i in range(1, self._ds.getNumberOfZones() + 1)))
        self._steppers = dict.fromkeys((i for i in range(1, self._ds.getNumberOfZones() + 1)))
        self._es = dict((i, threading.Event()) for i in range(1, self._ds.getNumberOfZones() + 1))
        self._q = Queue.Queue()
        
    def run(self):
        while ( True ):      
            zone, command = self._q.get()
            
            if ( command == COMMAND.get("START_STOP") ):
                if ( self._steppers.get(zone) ):
                    print "\tController: Stopping bakeout"                    
                    self._programs[zone] = None
                    self._es.get(zone).set()
                    continue
                
                flatProgram = self._ds.getProgram(zone)
                if ( flatProgram == NO_PROGRAM ):
                    print "\tErr: No program saved for zone %s" % zone
                else:
                    print "\tController: Starting bakeout"                                                            
                    start_command = [1, zone,
                                   ELOTECH_ISTR.get("ACPT"),
                                   ELOTECH_PARAM.get("ZONE_TOGGLE"),
                                   1]
                    self._ds.SendCommand(start_command)
                                                            
                    self._programs[zone] = self.unflattenProgram(flatProgram)
                    stepper = BakeoutStepper(self, zone)
                    stepper.start()                    
                    self._steppers[zone] = stepper               
            
            elif ( command == COMMAND.get("PAUSE") ):
                """ pause zone stepper """
            
            elif ( command == COMMAND.get("FEED") ):
                print "\tController: Feeding stepper",                
                if ( self._programs.get(zone) ):
                    step = self._programs.get(zone).pop()              
                    self._steppers.get(zone).setStep(step)
                    print step
                else:
                    self._programs[zone] = None
                    self._steppers.get(zone).setStep(None)
                    self._steppers[zone] = None
                    print None
                
                self._es.get(zone).set()
                
            self._q.task_done()
     
    def getQueue(self):
        return self._q
    
    def getEventForZone(self, zone):
        return self._es.get(zone)
    
    def getDeviceServer(self):
        return self._ds
               
    def unflattenProgram(self, flatProgram):
        program = []
        for i in reversed(range(len(flatProgram) / 3)):
            program.append([item for item in flatProgram[i * 3:(i + 1) * 3]])
            
        return program

class BakeoutStepper(threading.Thread):
    def __init__(self, bakeoutController, zone):
        threading.Thread.__init__(self)

        self._c = bakeoutController
        self.zone = zone
        self._step = None

        self._ds = self._c.getDeviceServer()
        self._q = self._c.getQueue()
        self._e = self._c.getEventForZone(self.zone)
        
    def run(self):
        while ( True ):
            self._e.clear()
            self._q.put((self.zone, COMMAND.get("FEED")))
            print "\tStepper %s: Awaiting feed" % self.getName()
            self._e.wait()
            print "\tStepper %s: Starting bakeout" % self.getName(), self._step
            self._e.clear()
            
            if ( not self._step ): break
            
            self.temp = self._step[0]
            self.ramp = self._step[1]
            self.total_time = self._step[2] * 3600.
            
            ramp_command = [1, self.zone,
                            ELOTECH_ISTR.get("ACPT"),
                            ELOTECH_PARAM.get("RISE"),
                            self.ramp]
            self._ds.SendCommand(ramp_command)
            
            temp_command = [1, self.zone,
                            ELOTECH_ISTR.get("ACPT"),
                            ELOTECH_PARAM.get("SETPOINT"),
                            self.temp]
            self._ds.SendCommand(temp_command)

            self._e.wait(self.total_time)
            print "\tStepper %s: Step done" % self.getName()            

        print "\tStepper %s: Stopping bakeout" % self.getName()
        stop_command = [1, self.zone,
                       ELOTECH_ISTR.get("ACPT"),
                       ELOTECH_PARAM.get("ZONE_TOGGLE"),
                       0]
        self._ds.SendCommand(stop_command)
        print "\tStepper %s: Done" % self.getName()        
        
    def setStep(self, step):
        self._step = step