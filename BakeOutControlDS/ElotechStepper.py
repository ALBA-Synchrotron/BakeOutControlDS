#    "$Name:  $";
#    "$Header:  $";
#=============================================================================
#
# file :        stepper.py
#
# description : Python source for the BakeOutControlDS and its commands. 
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                BakeOutControlDS are implemented in this file.
#
# project :     TANGO Device Server
#
# $Author:  srubio@cells.es,
#           knowak@cells.es,
#           mniegowski@cells.es
#
# $Revision:  $
#
# $Log:  $
#
# copyleft :    ALBA Synchrotron Light Source
#               www.cells.es, Barcelona
#

import threading,time,serial
import traceback
from threading import Event, Lock
from Queue import Queue
import PyTango
from fandango.dicts import Enumeration

TEMP_ROOM = 25.
TEMP_DEFAULT = 1200.
PROGRAM_DEFAULT = list([TEMP_DEFAULT, 0., -1.])
PARAMS_DEFAULT = list([TEMP_DEFAULT, 0., 0., 0.])

ElotechInstruction = Enumeration(
"ElotechInstruction", (
    ("SEND", int("10", 16)),
    ("SEND_GROUP", int("15", 16)),
    ("ACPT", int("20", 16)),
    ("ACPT_SAVE", int("21", 16))    
))

ElotechParameter = Enumeration(
"ElotechParameter", (
    ("TEMP", int("10", 16)),
    ("SETPOINT", int("21", 16)),
    ("RAMP", int("2F", 16)),
    ("OUTPUT", int("60", 16)),
    ("OUTPUT_LIMIT", int("64", 16)),
    ("ZONE_ON_OFF", int("8F", 16))              
))

ElotechError = Enumeration(
"ElotechError", (
    ("ParityError", int("01", 16)),
    ("ChecksumError", int("02", 16)),
    ("ProcedureError", int("03", 16)),
    ("NonComplianceError", int("04", 16)),
    ("ZoneNumberError", int("05", 16)),
    ("ParameterReadOnlyError", int("06", 16)),
    ("PowerfailSaveError", int("FE", 16)),
    ("GeneralError", int("FF", 16))    
))

ControllerCommand = Enumeration(
"ControllerCommand", (
    "STOP",
    "START",
    "PAUSE",
    "FEED"
))


#===============================================================================
# 
# Controller class definition
# 
#===============================================================================
class Controller(threading.Thread):
    def __init__(self, bakeOutControlDS, name="Bakeout-Controller"):
        threading.Thread.__init__(self, name=name)

        self._ds = bakeOutControlDS
        self._programCount = self._ds.zoneCount()
        self._programs = dict.fromkeys((i for i in range(1, self._programCount + 1)))
        self._steppers = dict.fromkeys((i for i in range(1, self._programCount + 1)))
        self._events = dict((i, threading.Event()) for i in range(1, self._programCount + 1))
        self._q = Queue()
        
              
    def device(self):
        return self._ds
    
    def event(self, programNo):
        return self._events.get(programNo)
    
    def isRunning(self, programNo):
        if ( programNo ):
            return bool(self.stepper(programNo)) and self.stepper(programNo).isAlive()
        else:
            if any( [bool(self.stepper(programNo)) and self.stepper(programNo).isAlive() for programNo in range(self._programCount)] ):
                return True
            return False

    def program(self, programNo):
        return self._programs.get(programNo)
        
    def programCount(self):
        return self._programCount
    
    def queue(self):
        return self._q
    
    def run(self):            
        while ( True ):      
            print "In Controller(%s).run(), at %s, waiting for commands ..."%(self.device().get_name(),time.ctime())
            programNo,command = None,None
            try:
                programNo, command = self.queue().get()
                print "In Controller(%s).run(%s,%s)"%(self.device().get_name(),programNo,command)
                if ( command == ControllerCommand.STOP ):
                    print '\tReceived an STOP(%s) command'%programNo
                    for progNo in (programNo and (programNo,) or range(1, self.programCount() + 1)):
                        if ( self.isRunning(progNo) ):
                            print "\t", time.strftime("%H:%M:%S"), "%s: Stopping bakeout program %d" % (self.getName(), progNo)                
                            self.setProgram(progNo, None)
                            self.event(progNo).set()
                        else: 
                            # Elotech Zones will be stop if are not managed by any program!
                            print '\tProgram %d is not running, checking for active zones'%progNo
                            pzones = [z for k in range(1,self.device().zoneCount()+1) for z in self.device().zones(k) if self.isRunning(k)]
                            if progNo in pzones: 
                                print '\tZone %d is managed by a program, it must be stop using a program number'%progNo
                            else:
                                print '='*80
                                print 'Controller(%s).STOP(%d): Switching OFF zone'%(self.device().get_name(),progNo)
                                self.device().SendCommand([1, progNo,"%02X" % ElotechInstruction.ACPT,"%02X" % ElotechParameter.ZONE_ON_OFF,0])
                                print '='*80
                elif ( command == ControllerCommand.START ):
                    print '\tReceived an START command'
                    flatProgram = self.device().program(programNo)
                    if ( flatProgram == PROGRAM_DEFAULT ):
                        print "\t", time.strftime("%H:%M:%S"), "Err: Program %d not saved" % programNo
                    else:
                        zones = self.device().zones(programNo)
                        if ( not zones ):
                            print "\t", time.strftime("%H:%M:%S"), "Err: Zones for program %d not saved" % programNo
                        else:
                            print "\t", time.strftime("%H:%M:%S"), "%s: Starting bakeout program %d for zones %s" % (self.getName(), programNo, zones)                                                            
                            program = self.unflattenProgram(flatProgram)
                            self.setProgram(programNo, program)
                            program = self.program(programNo)
                            if ( program ):
                                if self.stepper(programNo) and self.stepper(programNo).isAlive():
                                    print 'PROGRAM %d SHOULD BE STOP BEFORE A NEW START'%programNo
                                else:
                                    step = program.pop()
                                    stepper = Stepper(self, programNo, step, zones)
                                    self.setStepper(programNo, stepper)
                                    stepper.start()
                elif ( command == ControllerCommand.PAUSE ):
                    print '\tReceived a PAUSE command'
                    raise NotImplementedError
                elif ( command == ControllerCommand.FEED ):
                    print '\tReceived a FEED command'
                    program = self.program(programNo)
                    if ( program ):
                        print "\t", time.strftime("%H:%M:%S"), "%s: Feeding program %d stepper with:" % (self.getName(), programNo),                
                        step = program.pop()
                        self.stepper(programNo).setStep(step)
                        print step
                    else:
                        print "\t", time.strftime("%H:%M:%S"), "%s: Finishing bakeout program %d" % (self.getName(), programNo)
                        self.setProgram(programNo, None)
                        self.stepper(programNo).setStep(None)
                        self.setStepper(programNo, None)
                    self.event(programNo).set()
            except:
                msg = 'In Controller().run: unable to process command(%s,%s)\n%s'%(programNo,command,traceback.format_exc())
                print msg
                self._ds.set_state(PyTango.DevState.FAULT)
                self._ds.set_status(msg)
            finally:
                self.queue().task_done()
            Event().wait(.01)

    def setProgram(self, programNo, program):
        self._programs[programNo] = program
        
    def setStepper(self, programNo, stepper):
        self._steppers[programNo] = stepper
        
    def stepper(self, programNo):
        return self._steppers.get(programNo)
        
    def unflattenProgram(self, flatProgram):
        if ( flatProgram == PROGRAM_DEFAULT ):
            program = PROGRAM_DEFAULT
        else:
            program = []
            for i in reversed(range(len(flatProgram) / 3)):
                program.append([item for item in flatProgram[i * 3:(i + 1) * 3]])
            
        return program
    
#===============================================================================
# 
# Stepper class definition
# 
#===============================================================================
class Stepper(threading.Thread):
    """
    The Stepper class processes the steps of a given program, taking them one by one from the controller queue.
    A call to feed() will tell the Controller to set a new Step or reset the existing one (program finished).
    """
    def __init__(self, controller, programNo, step, zones):
        threading.Thread.__init__(self, name="Bakeout-Program-%s" % programNo)

        self._ds = controller.device()
        self._q = controller.queue()
        self._event = controller.event(programNo)
        self._programNo = programNo
        self._step = step
        self._zones = zones
        
    def device(self):
        return self._ds
        
    def setStep(self, step):
        self._step = step
        
    def execute(self, command):
        self._ds.SendCommand(command)
        
    def feed(self):
        self._q.put((self._programNo, ControllerCommand.FEED))
        
    def isFinished(self):
        return not bool(self._step)
    
    def maxDiff(self, temp, zones):
        ta = [self._ds.temperatureAttr(z) for z in zones]
        ts = [t for t in ta if t != TEMP_DEFAULT]
        dt = [abs(temp - t) for t in ts]
        return dt and ts[dt.index(max(dt))] or TEMP_DEFAULT
        
    def programNo(self):
        return self._programNo
    
    def event(self):
        return self._event
    
    def zones(self):
        return self._zones    
    
    def params(self):
        return self._ds.params(self._programNo)
    
    def setParams(self, params):
        self._ds.setParams(self._programNo, params)
        
    def setStartTemp(self, temp):
        self._sTemp = temp
        
    def startTemp(self):
        return self._sTemp
   
    def temp(self):
        return self._step[0]
    
    def ramp(self):
        return self._step[1]
    
    def time(self):
        return self._step[2]
    
    def run(self):
        try:
            params = self.params()
            self._sTemp = params[0] = self.maxDiff(self.temp(), self.zones())
            while ( not self.isFinished() ):
                print "\tIn Stepper(%s).run(%s): %s" % (self.device().get_name(), time.strftime("%H:%M:%S"), self._step)
                temp = self.temp()
                ramp = self.ramp()
                timeout = 60. * (60. * self.time() + abs(self.startTemp() - temp) / ramp)
                
                self.setStartTemp(temp)
                t0 = time.time()
                print "\t", time.strftime("%H:%M:%S"), "Stepper(%s): Baking zones %s for %f minutes" % (self.device().get_name(), self.zones(), timeout / 60. )
                
                if temp:
                    #Sending the temp,ramp parameters for the received step
                    for zone in self.zones():
                        print '\tSending %d ramp parameters'%zone
                        ramp_command = [1, zone,"%02X" % ElotechInstruction.ACPT,"%02X" % ElotechParameter.RAMP,ramp]
                        self.execute(ramp_command)
                        print '\tSending zone %d temperature setpoints'%zone
                        temp_command = [1, zone,"%02X" % ElotechInstruction.ACPT,"%02X" % ElotechParameter.SETPOINT,temp]
                        self.execute(temp_command)
                        
                #Starting the bakeout
                if temp and not params[1]:
                    print '\tStarting the bakeout!'
                    params[1] = time.time()
                    params[2] = 0.
                    params[3] = 0.
                    self.setParams(params)
                    for zone in self.zones():
                        start_command = [1, zone,
                                    "%02X" % ElotechInstruction.ACPT,
                                    "%02X" % ElotechParameter.ZONE_ON_OFF,
                                    1]
                        self.execute(start_command)
                #Stopping the Bakeout
                elif temp<=0:
                    print 'Stepper: Switching OFF zones: %s'%(self.zones())
                    for zone in self.zones():
                        stop_command = [1, zone,
                                        "%02X" % ElotechInstruction.ACPT,
                                        "%02X" % ElotechParameter.ZONE_ON_OFF,
                                        0]
                        self.execute(stop_command)

                while not self.isFinished() and time.time()<(t0+timeout) and not self.event().is_set():
                    #This while will be waiting here until timeout time is reached
                    #The configuration will be verified every 60 seconds
                    try:
                        check = False
                        if params[1] and time.time()>t0+60.: #waiting one minute to allow the controller to update setpoints
                            try:
                                print '\tEllapsed %2.1f %% of step (%s,%s,%s),\n\tChecking %d zones temperature setpoints ...'%(100*(time.time()-t0)/timeout,temp,ramp,timeout,len(self.zones()))
                                for zone in self.zones():
                                    sp = self.device().temperatureSpAttr(zone)
                                    ans = self.device().threadDict.get((1,zone,"%02X" % ElotechInstruction.SEND,"%02X" % ElotechParameter.ZONE_ON_OFF))
                                    on = ans and bool(int(ans[11:13]))
                                    if not on or sp!=temp:
                                        print 'WARNING: The channel %d conditions (%s,%s) doesnt match with program (%s)!'%(on,sp,temp,self.programNo())
                                        check = True
                            except:
                                print 'Exception in %s.Stepper(%s,%s) at %s' % (self.device().get_name(),self._step,self.zones(),time.ctime())
                                print traceback.format_exc()
                                check = True
                        if check: self.device().CheckStatus(alarm=True)
                    except:
                        print 'Exception in %s.Stepper(%s,%s) at %s' % (self.device().get_name(),self._step,self.zones(),time.ctime())
                        print traceback.format_exc()
                    self.event().wait(60.)
                #Step finished, waiting for commands
                self.event().clear()
                print "\t", time.strftime("%H:%M:%S"), "%s: Awaiting feed" % self.device().get_name()
                self.feed()
                self.event().wait()
                self.event().clear()
            #Bakeout finished
            print "\t", time.strftime("%H:%M:%S"), "%s: Stopping bakeout stepper" % self.device().get_name()
        except:
            print traceback.format_exc()
            msg = 'Stepper(%s).run: unable to process step(%s,%s,%s)'%(self.programNo(),self.temp(),self.ramp(),self.time())
            print msg
            self._ds.set_state(PyTango.DevState.FAULT)
            self._ds.set_status(msg)
        finally:
            try:
                if params[1] and self.isFinished():
                    print '%s.Stepper(%s): Finished, but NOT Switching OFF zones automatically, option disabled'%(self.device().get_name(),self.programNo())
                    #print 'Stepper: Switching OFF zones: %s'%(self.zones())
                    #for zone in self.zones():
                        #stop_command = [1, zone,
                                        #"%02X" % ElotechInstruction.ACPT,
                                        #"%02X" % ElotechParameter.ZONE_ON_OFF,
                                        #0]
                        #self.execute(stop_command)
                else:
                    print 'Stepper program EXITED BUT NOT FINISHED!!!!'
            except:
                print 'In Stepper(%s).run: unable to stop channels\n%s'%(self.programNo(),traceback.format_exc())
            params = self.params()
            params[3] = time.time() #FinishTime = Now
            self.setParams(params)
            self.device().update_program_properties()
            
        print "\t", time.strftime("%H:%M:%S"), "%s: Done" % self.device().get_name()

