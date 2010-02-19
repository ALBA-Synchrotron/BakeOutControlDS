import threading
import Queue
from BakeOutEnumeration import *

COMMAND = {"STOP": 0,
           "START": 1,
           "PAUSE": 2,
           "FEED": 3}

#===============================================================================
#
# BakeOutController Class
#
#===============================================================================
class BakeOutController(threading.Thread):
    def __init__(self, bakeoutcontrolds, name="Thread-BakeOutController"):
        threading.Thread.__init__(self, name=name)

        self._ds = bakeoutcontrolds
        self._programs = dict.fromkeys((i for i in range(1, self._ds.getNumberOfZones() + 1)))
        self._steppers = dict.fromkeys((i for i in range(1, self._ds.getNumberOfZones() + 1)))
        self._ctrlQ = Queue.Queue()
        
    def run(self):
        while ( True ):      
            zone, command = self._ctrlQ.get()
            if ( command == COMMAND.get("START") ):
                flatProgram = self._ds.getProgram(zone)
                if ( flatProgram != NO_PROGRAM ):
                    program = self.unflattenProgram(flatProgram)
                    stepper = BakeOutStepper(self, zone, program[0])
                    stepper.start()
                    program.pop(0)                   
                    self._steppers[zone] = stepper            
                    self._programs[zone] = program
            elif ( command == COMMAND.get("STOP") ):
                """ stop zone stepper """
                self._programs[zone] = None
            elif ( command == COMMAND.get("PAUSE") ):
                """ pause zone stepper """
            elif ( command == COMMAND.get("FEED") ):
                if ( self._programs.get(zone) ):
                    program = self._programs.get(zone)[0]                 
                    self._steppers.get(zone).setProgram(program)
                    self._programs.get(zone).pop(0)
                else:
                    self._steppers.get(zone).setProgram(None)
                    self._programs[zone] = None
                    self._steppers[zone] = None
                
    def unflattenProgram(self, flatProgram):
        program = []
        for i in range(len(flatProgram) / 3):
            program.append([item for item in flatProgram[i * 3:i * 3 + 3]])
            
        return program
    
    def getCtrlQ(self):
        return self._ctrlQ
    
    def getDs(self):
        return self._ds

class BakeOutStepper(threading.Thread):
    def __init__(self, bakeoutcontroller, zone, program=None):
        threading.Thread.__init__(self)

        self._ctrl = bakeoutcontroller
        self._ctrlQ = self._ctrl.getCtrlQ()
        self._ds = self._ctrl.getDs()
        self.zone = zone
        self._program = program
        
    def run(self):
        while ( self._program ):
            print "In BakeOutStepper" + self.getName() + ".run()", self._program
            self.temp = self._program[0]
            self.ramp = self._program[1]
            self.total_time = self._program[2] * 3600.
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
            self._program = None
            self._ctrlQ.put((self.zone, COMMAND.get("FEED")))
            threading.Event().wait(self.total_time)
        
    def setProgram(self, program):
        self._program = program