import Queue
import threading
import time
from BakeoutEnumeration import *

COMMAND = {"STOP": 0x00,
           "START": 0x01,
           "PAUSE": 0x02,
           "FEED": 0x03}          

class BakeoutController(threading.Thread):
    def __init__(self, bakeoutControlDS, name="Bakeout-Controller"):
        threading.Thread.__init__(self, name=name)

        self._ds = bakeoutControlDS
        self._noZones = self._ds.zoneCount()
        self._programs = dict.fromkeys((i for i in range(1, self._noZones + 1)))
        self._pSteppers = dict.fromkeys((i for i in range(1, self._noZones + 1)))
        self._sE = dict((i, threading.Event()) for i in range(1, self._noZones + 1))
        self._q = Queue.Queue()
        
    #---------------------------------------------------------------- __init__()
        
    def run(self):            
        while ( True ):      
            programNo, command = self._q.get()
            
            if ( command == COMMAND.get("STOP") ):
                for progNo in (programNo and (programNo,) or range(1, self._noZones + 1)):
                    if ( self._pSteppers.get(progNo) ):
                        print "\t", time.strftime("%H:%M:%S"), "%s: Stopping bakeout program %d" % (self.getName(), progNo)                
                        self._programs[progNo] = None
                        self._sE.get(progNo).set()
            
            elif ( command == COMMAND.get("START") ):               
                flatProgram = self._ds.getProgram(programNo)
                if ( flatProgram == PROGRAM_DEFAULT ):
                    print "\t", time.strftime("%H:%M:%S"), "Err: Program %d not saved" % programNo
                else:
                    zones = self._ds.getZones(programNo)
                    if ( not zones ):
                        print "\t", time.strftime("%H:%M:%S"), "Err: Zones for program %d not saved" % programNo
                    else:
                        print "\t", time.strftime("%H:%M:%S"), "%s: Starting bakeout program %d for zones %s" % (self.getName(), programNo, zones)                                                            
                        program = self.unflattenProgram(flatProgram)
                        self._programs[programNo] = program
                        step = self._programs.get(programNo).pop()
                        stepper = BakeoutStepper(self, programNo, step, zones)
                        self._pSteppers[programNo] = stepper
                        stepper.start()
            
            elif ( command == COMMAND.get("PAUSE") ):
                """ pause zone stepper """
            
            elif ( command == COMMAND.get("FEED") ):
                if ( self._programs.get(programNo) ):
                    print "\t", time.strftime("%H:%M:%S"), "%s: Feeding program %d stepper with:" % (self.getName(), programNo),                
                    step = self._programs.get(programNo).pop()              
                    self._pSteppers.get(programNo).setStep(step)
                    print step
                else:
                    print "\t", time.strftime("%H:%M:%S"), "%s: Finishing bakeout program %d" % (self.getName(), programNo)
                    self._programs[programNo] = None
                    self._pSteppers.get(programNo).setStep(None)
                    self._pSteppers[programNo] = None
                
                self._sE.get(programNo).set()
                
            self._q.task_done()
            
    #--------------------------------------------------------------------- run()
     
    def isAlive(self, programNo):
        return bool(self._pSteppers.get(programNo)) and self._pSteppers.get(programNo).isAlive()

    #----------------------------------------------------------------- isAlive()
                
    def getDeviceServer(self):
        return self._ds
    
    #--------------------------------------------------------- getDeviceServer()
               
    def getEvent(self, programNo):
        return self._sE.get(programNo)
    
    #---------------------------------------------------------------- getEvent()
    
    def getQueue(self):
        return self._q
    
    #---------------------------------------------------------------- getQueue()
      
    def unflattenProgram(self, flatProgram):
        if ( flatProgram == PROGRAM_DEFAULT ):
            program = PROGRAM_DEFAULT
        else:
            program = []
            for i in reversed(range(len(flatProgram) / 3)):
                program.append([item for item in flatProgram[i * 3:(i + 1) * 3]])
            
        return program
    
    #-------------------------------------------------------- unflattenProgram()
    
#----------------------------------------------------------- BakeoutController()

class BakeoutStepper(threading.Thread):
    def __init__(self, bakeoutController, programNo, step, zones):
        threading.Thread.__init__(self, name="Bakeout-Program-%s" % programNo)

        self._ds = bakeoutController.getDeviceServer()
        self._q = bakeoutController.getQueue()
        self._e = bakeoutController.getEvent(programNo)
        self._pNo = programNo
        self._step = step
        self._z = zones
        
        params = self._ds.getParams(programNo)
        self._sTemp = params[0] = self.maxDiff(step[0], zones)
        params[1] = time.time()
        params[2] = params[3] = 0.
        self._ds.setParams(programNo, params)
        
    #---------------------------------------------------------------- __init__()
        
    def run(self):
        for zone in self._z:
            start_command = [1, zone,
                             ELOTECH_ISTR.get("ACPT"),
                             ELOTECH_PARAM.get("ZONE_ON_OFF"),
                             1]
            self._ds.SendCommand(start_command)
                    
        while ( self._step ):
            print "\t", time.strftime("%H:%M:%S"), "%s: Starting bakeout" % self.getName(), self._step
            self._temp = self._step[0]
            self._ramp = self._step[1]
            self._time = 60. * (self._step[2] + abs(self._sTemp - self._temp) / self._ramp)
            self._sTemp = self._temp
            
            for zone in self._z:
                ramp_command = [1, zone,
                                ELOTECH_ISTR.get("ACPT"),
                                ELOTECH_PARAM.get("RISE"),
                                self._ramp]
                self._ds.SendCommand(ramp_command)
            for zone in self._z:                
                temp_command = [1, zone,
                                ELOTECH_ISTR.get("ACPT"),
                                ELOTECH_PARAM.get("SETPOINT"),
                                self._temp]
                self._ds.SendCommand(temp_command)

            print "\t", time.strftime("%H:%M:%S"), "%s: Baking zones %s for %f minutes" % (self.getName(), self._z, self._time / 60. )
            self._e.wait(self._time)
            print "\t", time.strftime("%H:%M:%S"), "%s: Step done" % self.getName()            
            self._e.clear()
            print "\t", time.strftime("%H:%M:%S"), "%s: Awaiting feed" % self.getName()
            self._q.put((self._pNo, COMMAND.get("FEED")))
            self._e.wait()
            self._e.clear()
            
        print "\t", time.strftime("%H:%M:%S"), "%s: Stopping bakeout" % self.getName()
        for zone in self._z:
            stop_command = [1, zone,
                            ELOTECH_ISTR.get("ACPT"),
                            ELOTECH_PARAM.get("ZONE_ON_OFF"),
                            0]
            self._ds.SendCommand(stop_command)

        params = self._ds.getParams(self._pNo)
        params[3] = time.time()
        self._ds.setParams(self._pNo, params)
            
        print "\t", time.strftime("%H:%M:%S"), "%s: Done" % self.getName()
        
    #--------------------------------------------------------------------- run()
        
    def setStep(self, step):
        self._step = step
        
    #----------------------------------------------------------------- setStep()
    
    def maxDiff(self, temp, zones):
        _ta = [self._ds.getTemperatureAttr(z) for z in zones]
        _t = [t for t in _ta if t != 1200.]
        _dt = [abs(temp - t) for t in _t]
        return _dt and _t[_dt.index(max(_dt))] or TEMP_DEFAULT
    
    #----------------------------------------------------------------- maxDiff()
     
#-------------------------------------------------------------- BakeoutStepper()
    