import Queue
import threading
from BakeoutEnumeration import *

COMMAND = {"STOP": 0x00,
           "START": 0x01,
           "PAUSE": 0x02,
           "FEED": 0x03}          

class BakeoutController(threading.Thread):
    def __init__(self, bakeoutControlDS, name="Thread-BakeoutController"):
        threading.Thread.__init__(self, name=name)

        self._ds = bakeoutControlDS
        self._noZones = self._ds.zoneCount()
        self._programs = dict.fromkeys((i for i in range(1, self._noZones + 1)))
        self._steppers = dict.fromkeys((i for i in range(1, self._noZones + 1)))
        self._es = dict((i, threading.Event()) for i in range(1, self._noZones + 1))
        self._q = Queue.Queue()
        
    #---------------------------------------------------------------- __init__()
        
    def run(self):            
        while ( True ):      
            zone, command = self._q.get()
            
            if ( command == COMMAND.get("STOP") ):
                for zone in (zone and (zone,) or range(1, self._noZones + 1)):
                    if ( self._steppers.get(zone) ):
                        print "\tController: Stopping bakeout for zone %d" % zone                
                        self._ds.setProgramStopTempTime(zone)                        
                        self._programs[zone] = None
                        self._es.get(zone).set()
            
            elif ( command == COMMAND.get("START") ):               
                flatProgram = self._ds.getProgram(zone)
                if ( flatProgram == NO_PROGRAM ):
                    print "\tErr: No program saved for zone %d" % zone
                else:
                    print "\tController: Starting bakeout for zone %d" % zone                                                            
                    start_command = [1, zone,
                                     ELOTECH_ISTR.get("ACPT"),
                                     ELOTECH_PARAM.get("ZONE_ON_OFF"),
                                     1]
                    self._ds.SendCommand(start_command)
                                                            
                    self._programs[zone] = self.unflattenProgram(flatProgram)
                    stepper = BakeoutStepper(self, zone)
                    stepper.start()
                    self._steppers[zone] = stepper
            
            elif ( command == COMMAND.get("PAUSE") ):
                """ pause zone stepper """
            
            elif ( command == COMMAND.get("FEED") ):
                print "\tController: Feeding zone %d stepper with:" % zone,                
                if ( self._programs.get(zone) ):
                    step = self._programs.get(zone).pop()              
                    self._steppers.get(zone).setStep(step)
                    print step
                else:
                    self._programs[zone] = None
                    self._steppers.get(zone).setStep(None)
                    self._steppers[zone] = None
                    print "None"
                
                self._es.get(zone).set()
                
            self._q.task_done()
            
    #--------------------------------------------------------------------- run()
     
    def isAlive(self, zone):
        if ( zone ):
            return bool(self._steppers.get(zone)) and self._steppers.get(zone).isAlive()
        elif ( any( bool(self._steppers.get(zone)) and self._steppers.get(zone).isAlive() for zone in range(1, self._noZones + 1)) ):
            return True
        else:
            return False
        
    #----------------------------------------------------------------- isAlive()
                
    def getDeviceServer(self):
        return self._ds
    
    #--------------------------------------------------------- getDeviceServer()
               
    def getEvent(self, zone):
        return self._es.get(zone)
    
    #---------------------------------------------------------------- getEvent()
    
    def getQueue(self):
        return self._q
    
    #---------------------------------------------------------------- getQueue()
    
    def unflattenProgram(self, flatProgram):
        program = []
        for i in reversed(range(len(flatProgram) / 4)):
            program.append([item for item in flatProgram[i * 4:(i + 1) * 4]])
            
        return program
    
    #-------------------------------------------------------- unflattenProgram()
    
#----------------------------------------------------------- BakeoutController()

class BakeoutStepper(threading.Thread):
    def __init__(self, bakeoutController, zone):
        threading.Thread.__init__(self)

        self._c = bakeoutController
        self._z = zone
        self._step = None
        self._ds = self._c.getDeviceServer()
        self._q = self._c.getQueue()
        self._e = self._c.getEvent(self._z)
        
    #---------------------------------------------------------------- __init__()
        
    def run(self):
        self._ds.setProgramStartTempTime(self._z)
        while ( True ):
            self._e.clear()
            self._q.put((self._z, COMMAND.get("FEED")))
            print "\tStepper %s: Awaiting feed" % self.getName()
            self._e.wait()
            self._e.clear()
            print "\tStepper %s: Starting bakeout" % self.getName(), self._step
            
            if ( not self._step ):
                break
            
            self.temp = self._step[0]
            self.ramp = self._step[1]
            self.time = self._step[3]
            
            ramp_command = [1, self._z,
                            ELOTECH_ISTR.get("ACPT"),
                            ELOTECH_PARAM.get("RISE"),
                            self.ramp]
            self._ds.SendCommand(ramp_command)
            
            temp_command = [1, self._z,
                            ELOTECH_ISTR.get("ACPT"),
                            ELOTECH_PARAM.get("SETPOINT"),
                            self.temp]
            self._ds.SendCommand(temp_command)

            print "\tStepper %s: Bakingout for %f minutes" % (self.getName(), self.time / 60. )
            self._e.wait(self.time)
            print "\tStepper %s: Step done" % self.getName()            

        print "\tStepper %s: Stopping bakeout" % self.getName()
        stop_command = [1, self._z,
                        ELOTECH_ISTR.get("ACPT"),
                        ELOTECH_PARAM.get("ZONE_ON_OFF"),
                        0]
        self._ds.SendCommand(stop_command)
        print "\tStepper %s: Done" % self.getName()
        self._ds.setProgramStopTempTime(self._z)
        
    #--------------------------------------------------------------------- run()
        
    def getZone(self):
        return self._z
    
    #----------------------------------------------------------------- getZone()
        
    def setStep(self, step):
        self._step = step
        
    #----------------------------------------------------------------- setStep()
        
#-------------------------------------------------------------- BakeoutStepper()
    