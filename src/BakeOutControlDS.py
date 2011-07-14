#    "$Name:  $";
#    "$Header:  $";
#=============================================================================
#
# file :        BakeOutControlDS.py
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

import fandango
import PyTango
if 'PyUtil' not in dir(PyTango): #For PyTango7-3 backward compatibility
    PyTango.PyUtil = PyTango.Util
    PyTango.PyDeviceClass = PyTango.DeviceClass
    PyTango.Device_3Impl = PyTango.Device_4Impl

import serial
import sys
import threading
import time
from decimal import Decimal
from threading import Event, Lock

from ElotechStepper import *

MAX_ERRORS = 5

#===============================================================================
# BakeOutControllDS Class Description
#
#    This device can be used to do a simple control of a Bake Out process.<br/>
#    <p>
#    The ControllerType property tells the kind of temperature controller to use; 
#    Elotech-Bestec and Eurotherm (over MODBUS) protocols are supported, 
#    CommsDevice specifies the device to be used for communications.
#    From this controller we will read the Temperature_x (for x being the zone number)
#    and Temperature_SetPoint attributes, but it will not be modified by the device server.
#    </p><p>
#    Using the PressureAttribute property a pressure value will be read from other
#    Tango Device and showed as Pressure attribute. If the value readed exceeds the
#    Pressure_SetPoint value (either attribute or property); then a command (Stop) 
#    will be executed to stop the Temperature Controller device. <br>
#    This interlock action will be performed in the CheckPressure command.
#    </p><p>
#    The State and Status will be updated depending of the Status register of the 
#    Temperature Controller; this status will be read and updated using the CheckStatus
#    command.
#    </p>
#
#===============================================================================
# Device States Description:
#
#    DevState.OFF :
#    DevState.DISABLE :
#    DevState.UNKNOWN :
#    DevState.ALARM :
#    DevState.ON :
#
#===============================================================================

class BakeOutControlDS(PyTango.Device_4Impl):
    """
    Wiki available at http://redmine.cells.es/wiki/frontendbk/BakeOutControl

    This documentation matches the 4th release of the BakeOutControlDS, which has been modified to use dynamic attributes and be thread-safe.
    
    To do so a _dyn-attr()_ method replaced the previous read_?_N methods for *_Outputs, Programs, Zones,_* ... In this dyn_attr method can be verified the types of the attributes. Although the most important are:
    
    * Temperature_X: Temperature measured on each thermocouple
    * Output_X: Actual output value for a channel
    * Output_X_Limit: Max output allowed, RW
    
    * Program_X: A 3x64 RW image containing rows of *temperature,ramp,time* tuples. (temperature==1200 is used means not-initialized value).
    * Program_X_Params: This 4 values array returns the *startTemperature,startTime,pauseTime,finishTime* for every program (any value==0 means not initialized yet).
    * Program_X_Zones: An array containing the zones assigned to each program (numbers from 1 to 8).
    
    The Programs and Zones are set by the GUI, but Program Params are modified only by the device server. startTemperature is used to adjust the ramping time; startTime and finishTime are used to store when the program started and if it already finished; pauseTime is actually not used (although may be used once the Pause() command will be added).
    
    The Controller and Stepper classes are threads, which has been modified to catch unexpected exceptions and show them as Status of the BakeOutControlDS (with state==FAULT). The Stepper will try to configure Temperature and Ramp before enabling the Zone outputs. The Ramp and Temperature will be resent every minute.
    
    h2. State Machine
    
    * UNKNOWN: More than MAX_ERRORS communication errors received
    * OFF: None of the Zones is active
    * ON: Some Zones active, no programs running.
    * RUNNING: Zones active and programmed.
    * ALARM: Zones programmed but not running.
    * DISABLE: The Zones have been deactivated due to a Pressure interlock.
    * FAULT: An unexpected exception occurred.

    CheckPressure polling is needed to trigger Pressure interlocks.
    CheckStatus polling is needed to keep State and Status fields up to date.
    """
    def checksum(self, x, y):
        res = 256 - x - y - 32
        while ( res <= 0 ): res += 256
        
        return "%02X" % res
    
    def controller(self):
        if ( self._c ):
            return self._c
        raise AttributeError
        
    def elotech_checksum(self, args):
        res = 256 - sum([int(i, 16) for i in args])
        while ( res <= 0 ): res += 256
        
        return "%02X" % res
    
    def elotech_value(self, value):
        v = Decimal(str(value))
        v = v.as_tuple()
        mantissa = "%04X" % int(("-" if v[0] else "") + "".join(map(str, v[1])))
        exponent = "%02X" % int(self.int2bin(v[2]), 2)        
        
        return mantissa[:2], mantissa[-2:], exponent 
    
    def init_serial(self):
        self.serialLock.acquire()
        if ( hasattr(self, "_serial") and self._serial ): 
            self.serial().close()
        self._serial = serial.Serial()
        self._serial.baudrate = 9600
        self._serial.bytesize = 7
        self._serial.parity = "E"
        self._serial.stopbits = 1
        self._serial.timeout = 0
        self._serial.port = self.CommsDevice
        self._serial.xonxoff = 0
        self._serial.rtscts = 0
        self._serial.open()
        self.serialLock.release()
        
    def int2bin(self, n, count=8):
        return "".join([str((n >> y) & 1) for y in range(count - 1, -1, -1)])
    
    def listen(self):
        retries,waittime = 5,1e-3*self.Timeout
        sleeper = Event()
        sleeper.wait(waittime/retries)
        s = self.serial().readline()
        if ( not s ):
            ts = retries
            while ( not s and ts ):
                sleeper.wait(waittime/retries)
                s = self.serial().readline()
                ts -= 1
        s += self.serial().readline()
        
        return s
    
    def modbus(self):
        if ( self._modbus ):
            return self._modbus
        raise AttributeError
    
    def queue(self):
        if ( self._q ):
            return self._q
        raise AttributeError
  
    def setSerial(self, serial):
        self._serial = serial

    def serial(self):
        if ( self._serial ):
            return self._serial
        raise AttributeError
    
    ###########################################################################
    # Ouputs and Limits attributes

    def outputAttr(self, zone, attr):
        if self.Trace: print "In " + self.get_name() + ".outputAttr(%s)"%zone
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.SEND
            code = "%02X" % ElotechParameter.OUTPUT
            if self.Trace: print "\tdevice = %s, instruction = %s, code = %s"%(device,instruction,code)
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        ans = self.threadDict.get((device, zone, instruction, code))
        if ( ans ):
            data = int(ans[9:13], 16)
        else:
            data = 0
        
        if ( data ):
            attr.set_value_date_quality(data, time.time(), PyTango.AttrQuality.ATTR_CHANGING)
        else:
            attr.set_value(data)
            
    def limitAttr(self, zone, attr):
        if self.Trace: print "In " + self.get_name() + ".limitAttr(%s)"%zone
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.SEND 
            code = "%02X" % ElotechParameter.OUTPUT_LIMIT
            if self.Trace: print "\tdevice = %s, instruction = %s, code = %s"%(device,instruction,code)
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        ans = self.threadDict.get((device, zone, instruction, code))
        if ( ans ):
            data = int(ans[9:13], 16)
        else:
            data = 100
        
        attr.set_value(data)
        
    def setLimitAttr(self, zone, attr):
        if self.Trace: print "In " + self.get_name() + ".setLimitAttr(%s)"%zone
        data = []
        attr.get_write_value(data)
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.ACPT
            code = "%02X" % ElotechParameter.OUTPUT_LIMIT
            if self.Trace: print "\tdevice = %s, instruction = %s, code = %s"%(device,instruction,code)
            value = data[0]
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        self.SendCommand([device, zone, instruction, code, value])
        
    ###########################################################################
    # Methods to manage temperatures

    def tempAllTime(self):
        return self._tempAllTime
    
    def temperatureAttr(self, zone, attr=None):
        if self.Trace: print "In " + self.get_name() + ".temperatureAttr(%s)"%zone
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.SEND
            code = "%02X" % ElotechParameter.TEMP
            if self.Trace: print "\tdevice = %s, instruction = %s, code = %s"%(device,instruction,code)
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        
        ans = self.threadDict.get((device, zone, instruction, code))
        if ( ans ):
            data = float(int(ans[9:13], 16)*10**int(ans[13:15], 16))
            if data: self.error_count = 0
        else:
            #data = TEMP_DEFAULT
            self.error_count+=1
            raise Exception,'DataNotReceived'
        
        self.setTemperature(zone, data)
        
        if ( attr ):
            attr.set_value(data)
        
        return data
    
    def temps(self):
        return [v[1] for v in self._temps.values()]
    
    def tempMax(self):
        return self._tempMax
    
    def setTempAllTime(self):
        self._tempAllTime = long(time.time())
        
    def setTemperature(self, key, value):
        self._temps[key] = (time.time(),value)
        
    def temperatureSpAttr(self,zone,attr=None):
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device,instruction,code = 1,"%02X" % ElotechInstruction.SEND,"%02X" % ElotechParameter.SETPOINT
            if self.Trace:  print "\tdevice = %s, instruction = %s, code = %s"%(device,instruction,code)
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        
        ans = self.threadDict.get((device, zone, instruction, code))
        if ( ans ): 
            error_count,data = 0,float(int(ans[9:13], 16)*10**int(ans[13:15], 16))
        else:
            self.error_count+=1
            raise Exception,'DataNotReceived'
        if ( attr ): attr.set_value(data)
        return data
        
    def setTempMax(self, tempMax):
        self._tempMax = tempMax

    ###########################################################################
    # Methods to manage the Programming of bakeouts
    # Zones = dict(int:[]); keeps the zones managed by each program

    def update_program_properties(self):
        try:
            print '%s.update_program_properties(%s)'%(self.get_name(),self._programs.items())
            PyTango.Util.instance().get_database().put_device_property(self.get_name(),{
            'Programs':['%d:%s'%(i,','.join(str(f) for f in p)) for i,p in self._programs.items()],
            'Params':['%d:%s'%(i,','.join(str(f) for f in p)) for i,p in self._pParams.items()]
            })
        except:
            print traceback.format_exc()

    def setProgram(self, key, value):
        self._programs[key] = value
    
    def program(self, key):
        return self._programs.get(key)
    
    def setProgramAttr(self, programNo, attr):
        data = []
        attr.get_write_value(data)
        print "In " + self.get_name() + ".setProgramAttr(%s)"%str(data)
        if data is None or ( len(data) == 0 or len(data) % 3 != 0 ):
            raise ValueError
        self.setProgram(programNo, data)
        self.setParams(programNo, list(PARAMS_DEFAULT))
 
    def programAttr(self, programNo, attr):
        print "In " + self.get_name() + ".programAttr()"
        data = self.program(programNo) or []
        dim_x = 3
        dim_y = len(data) / 3    
        attr.set_value(data, dim_x, dim_y)
        
    def setParams(self, key, value):
        self._pParams[key] = value
        
    def params(self, key):
        return self._pParams.get(key)
                
    def paramsAttr(self, programNo, attr):
        print "In " + self.get_name() + ".paramsAttr()"
        data = self.params(programNo) or []
        attr.set_value(data)
        
    def zoneCount(self):
        return self._zoneCount
        
    def zones(self, key):
        return self._pZones.get(key)
        
    def setZones(self, key, value):
        self._pZones[key] = value
 
    def zonesAttr(self, programNo, attr):
        print "In " + self.get_name() + ".zonesAttr()"
        data = self.zones(programNo) or []
        attr.set_value(data)

    def setZonesAttr(self, programNo, attr):
        data = []
        attr.get_write_value(data)
        print "In " + self.get_name() + ".setZonesAttr(%s)"%str(data)
        dataSet = set(data)
        dataSet.intersection_update(i for i in range(1, self.zoneCount() + 1))
        for otherSet in [self.zones(pNo) for pNo in range(1, self.zoneCount() + 1) if pNo != programNo]:
            if ( dataSet.intersection(otherSet) ):
                dataSet.difference_update(otherSet)
        self.setZones(programNo, sorted(dataSet))

    ###########################################################################

    def update_properties(self, property_list=[]):
        property_list = property_list or self.get_device_class().device_property_list.keys()
        if ( not hasattr(self, "db") or not self.db ):
            self.db = PyTango.Database()
        props = dict([(key, getattr(self, key)) for key in property_list if hasattr(self, key)])
        for key, value in props.items():
            print "\tUpdating property %s = %s" % (key, value)
            self.db.put_device_property(self.get_name(), {key:isinstance(value, list) and value or [value]})
      
    def dyn_attr(self):
        """
        It is called after init_device in the Tango layer side.
        It creates the attributes needed to manage each channel (8 by default).
        """
        for i in range(1,self.NChannels+1):
            #"Output_1":[[PyTango.DevShort, PyTango.SCALAR, PyTango.READ]],
            attrib,format,unit = PyTango.Attr('Output_%d'%((i)),PyTango.DevShort, PyTango.READ),'%1.1f','%'
            print 'Creating attribute %s ...'%attrib
            props = PyTango.UserDefaultAttrProp(); props.set_format(format); props.set_unit(unit)
            attrib.set_default_properties(props)
            rfun = (lambda s,a,index=i: self.outputAttr(index,a))
            self.add_attribute(attrib,rfun,None,(lambda s,req_type,index=i: True))
            
            #"Output_1_Limit":[[PyTango.DevShort, PyTango.SCALAR, PyTango.READ_WRITE],{"min value": 0,"max value": 100}],            
            attrib,format,unit = PyTango.Attr('Output_%d_Limit'%((i)),PyTango.DevShort, PyTango.READ_WRITE),'%1.1f','%'
            print 'Creating attribute %s ...'%attrib
            props = PyTango.UserDefaultAttrProp(); props.set_min_value('0'); props.set_max_value('100'); props.set_format(format); props.set_unit(unit)
            attrib.set_default_properties(props)
            rfun = (lambda s,a,index=i: self.limitAttr(index,a))
            wfun = (lambda s,a,index=i: self.setLimitAttr(index,attr))
            self.add_attribute(attrib,rfun,wfun,(lambda s,req_type,index=i: True))
            
            #"Program_1":[[PyTango.DevDouble, PyTango.IMAGE, PyTango.READ_WRITE, 3, 64]], 
            attrib = PyTango.ImageAttr('Program_%d'%((i)),PyTango.DevDouble, PyTango.READ_WRITE,3,64)
            print 'Creating attribute %s ...'%attrib
            rfun = (lambda s,a,index=i: self.programAttr(index,a))
            wfun = (lambda s,a,index=i: self.setProgramAttr(index,a))
            self.add_attribute(attrib,rfun,wfun,(lambda s,req_type,index=i: True))
            
            #"Program_1_Params":[[PyTango.DevDouble, PyTango.SPECTRUM, PyTango.READ, 4]],
            attrib = PyTango.SpectrumAttr('Program_%d_Params'%((i)),PyTango.DevDouble, PyTango.READ,4)
            print 'Creating attribute %s ...'%attrib
            rfun = (lambda s,a,index=i: self.paramsAttr(index,a))
            self.add_attribute(attrib,rfun,None,(lambda s,req_type,index=i: True))
            
            #"Program_1_Zones":[[PyTango.DevShort, PyTango.SPECTRUM, PyTango.READ_WRITE, 8]],
            attrib = PyTango.SpectrumAttr('Program_%d_Zones'%((i)),PyTango.DevShort, PyTango.READ_WRITE,8)
            print 'Creating attribute %s ...'%attrib
            rfun = (lambda s,a,index=i: self.zonesAttr(index,a))
            wfun = (lambda s,a,index=i: self.setZonesAttr(index,a))
            self.add_attribute(attrib,rfun,wfun,(lambda s,req_type,index=i: True))
            
            #"Temperature_1":[[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ]],
            attrib,format,unit = PyTango.Attr('Temperature_%d'%((i)),PyTango.DevDouble, PyTango.READ),'%1.1f',''
            print 'Creating attribute %s ...'%attrib
            props = PyTango.UserDefaultAttrProp(); props.set_format(format); props.set_unit(unit)
            attrib.set_default_properties(props)
            rfun = (lambda s,a,index=i: self.temperatureAttr(index,a))
            self.add_attribute(attrib,rfun,None,(lambda s,req_type,index=i: True))
                
            #"Temperature_1_Setpoint":[[PyTango.DevDouble, PyTango.SCALAR, PyTango.READ_WRITE]],
            attrib,format,unit = PyTango.Attr('Temperature_%d_Setpoint'%((i)),PyTango.DevDouble, PyTango.READ),'%1.1f',''
            print 'Creating attribute %s ...'%attrib
            props = PyTango.UserDefaultAttrProp(); props.set_format(format); props.set_unit(unit)
            attrib.set_default_properties(props)
            rfun = (lambda s,a,index=i: self.temperatureSpAttr(index,a))
            #wfun = (lambda s,a,index=i: self.setTemperatureSpAttr(index,a))
            self.add_attribute(attrib,rfun,wfun,(lambda s,req_type,index=i: True))
            
            print "%s.dyn_attr() finished" % (self.get_name())
            
#------------------------------------------------------------------------------ 
#    Device constructor
#------------------------------------------------------------------------------ 
    def __init__(self, cl, name):
        print "In __init__()"        
        PyTango.Device_3Impl.__init__(self, cl, name)
        
        self.NChannels = 8
        self.error_count = 0
        self._modbus = None
        self._serial = None
        self._zoneCount = 1
        self._programs = None
        self._pParams = None
        self._pZones = None
        self._temps = None
        self._pressure = 0.
        self._pressureTime = 0
        self._statusTime = 0
        self.MIN_CHECK_INTERVAL = 10.
        self._tempMax = 0.
        self._tempAllTime = long(0)
        self.serialLock = threading.Lock()
        self.threadDict = None
        self.Trace = False
        
        BakeOutControlDS.init_device(self)
        
#------------------------------------------------------------------------------ 
#    Device destructor
#------------------------------------------------------------------------------ 
    def delete_device(self):
        print "In " + self.get_name() + ".delete_device()"        
        if ( self.ControllerType.lower() == "elotech" and self.serial() ):
            
            try:
                self.serialLock.acquire() 
                self.serial().close()
            finally: 
                self.serialLock.release()
            
#------------------------------------------------------------------------------ 
#    Device initialization
#------------------------------------------------------------------------------ 
    def init_device(self):
        print "In " + self.get_name() + ".init_device()"        
        self.set_state(PyTango.DevState.OFF)
        self.get_device_properties(self.get_device_class())
        #self.update_properties()
        
        try: 
            print 'PressureAttribute: %s'%self.PressureAttribute
            self.pressureAttr = PyTango.AttributeProxy(self.PressureAttribute)
        except Exception: 
            import traceback
            print traceback.format_exc()
            self.pressureAttr = None
            raise Exception("PressureAttributeProxyError")
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                print "\tUsing an eurotherm controller..."
                self._modbus = PyTango.DeviceProxy(self.CommsDevice)
                self._modbus.ping()
                self._temps = {}
            elif ( self.ControllerType.lower() == "elotech" ):
                print "\tUsing an elotech controller..."
                self.init_serial()
                self._zoneCount = 8
                self._programs = dict.fromkeys((i for i in range(1, self._zoneCount + 1)), PROGRAM_DEFAULT)
                self._pParams = dict((i, list(PARAMS_DEFAULT)) for i in range(1, self._zoneCount + 1))
                self._pZones = dict.fromkeys((i for i in range(1, self._zoneCount + 1)), list())
                self._temps = dict.fromkeys((i for i in range(1, self._zoneCount + 1)), (0,TEMP_DEFAULT))
                if getattr(self,'_c',None) is None:
                    self._c = Controller(self)
                    self._q = self._c.queue()
                    self._c.setDaemon(True)
                    self._c.start()
            else:
                raise Exception("UnknownController: %s" % self.ControllerType)
        except Exception, e:
#            self._modbus = None
#            self._serial = None
            raise Exception("InitError", e)
            
        if self.threadDict is None:
            print "\tInitializing serial threadDict"
            self.threadDict = fandango.ThreadDict(
                read_method = self.SendCommand,
                trace=self.Trace)
            # Every command has [device = 1, zone = 1-8, instruction = SEND(read)/ACPT(write), code = OUTPUT/TEMPERATURE/RAMP/...]
            POLL_PERIOD = 5.
            commands = ([(1,z+1,"%02X" % ElotechInstruction.SEND,"%02X" % ElotechParameter.OUTPUT) for z in range(self._zoneCount)]+
                        [(1,z+1,"%02X" % ElotechInstruction.SEND,"%02X" % ElotechParameter.TEMP) for z in range(self._zoneCount)]+
                        [(1,z+1,"%02X" % ElotechInstruction.SEND,"%02X" % ElotechParameter.ZONE_ON_OFF) for z in range(self._zoneCount)])
            [self.threadDict.append(c,period=POLL_PERIOD) for c in commands]
            self.threadDict.set_timewait(max((1e-3*self.Timewait,POLL_PERIOD/len(commands))))
            commands = ([(1,z+1,"%02X" % ElotechInstruction.SEND,"%02X" % ElotechParameter.OUTPUT_LIMIT) for z in range(self._zoneCount)]+
                        [(1,z+1,"%02X" % ElotechInstruction.SEND,"%02X" % ElotechParameter.SETPOINT) for z in range(self._zoneCount)])
            [self.threadDict.append(c,period=3.*POLL_PERIOD) for c in commands]
            self.threadDict.start()
        
        print "\tDevice server " + self.get_name() + " awaiting requests..."
        
#------------------------------------------------------------------------------ 
#    Always excuted hook method
#------------------------------------------------------------------------------ 
    def always_executed_hook(self):
#        print "In " + self.get_name() + ".always_executed_hook()"        
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                self.modbus().ping()
            if self.get_state()!=PyTango.DevState.FAULT:
                if (self.error_count>MAX_ERRORS):
                    self.set_state(PyTango.DevState.UNKNOWN)
                    self.set_status('Unable to communicate with device\n%d communication errors'%self.error_count)
                if self.error_count<=0 and self.get_state()==PyTango.DevState.UNKNOWN:
                    self.set_state(PyTango.DevState.ON)
        except:
            print 'Exception in always_executed_hook():'
            print traceback.format_exc()
            self.set_state(PyTango.DevState.UNKNOWN)
            
#------------------------------------------------------------------------------ 
#    Read Attribute Hardware
#------------------------------------------------------------------------------ 
    def read_attr_hardware(self, data):
#        print "In " + self.get_name() + ".read_attr_hardware()"        
        pass
        
#===============================================================================
# 
#    BakeOutControlDS read/write attribute methods
# 
#===============================================================================

    ###############################################################################
    # Output,Limit,Programs,Params and Temperature Attributes are managed using dynamic attributes
    ###############################################################################

#------------------------------------------------------------------------------ 
#    Read Pressure attribute
#------------------------------------------------------------------------------
    def read_Pressure(self, attr):
        print "In " + self.get_name() + ".read_Pressure()"
        if ( not self.pressureAttr ):
            raise Exception("PressureAttributeError")
        
        self.CheckPressure()
        attr.set_value(self._pressure)
        
#------------------------------------------------------------------------------ 
#    Read Pressure_SetPoint attribute
#------------------------------------------------------------------------------
    def read_Pressure_SetPoint(self, attr):
        print "In " + self.get_name() + ".read_Pressure_SetPoint()"
        data = self.PressureSetPoint
        attr.set_value(data)

#------------------------------------------------------------------------------ 
#    Write Pressure_SetPoint attribute
#------------------------------------------------------------------------------
    def write_Pressure_SetPoint(self, attr):
        print "In " + self.get_name() + ".write_Pressure_SetPoint()"
        data = []
        attr.get_write_value(data)
        self.PressureSetPoint = float(data[0])
        self.update_properties(['PressureSetPoint'])

#------------------------------------------------------------------------------ 
#    Read Temperature_All attribute
#------------------------------------------------------------------------------
    def read_Temperature_All(self, attr=None):
        print "In " + self.get_name() + ".read_Temperature_All()"
        if ( self.ControllerType.lower() == "eurotherm" ):
            #data = float(self.modbus().ReadHoldingRegisters([1, 1])[0])
            data = list(self.modbus().ReadHoldingRegisters([1, 1]))
#            print "Recv MODBUS: %s" % data
        elif ( self.ControllerType.lower() == "elotech" ):
            data = []                        
            for zone in range(1, self.zoneCount() + 1):
                ans = self.temperatureAttr(zone)
                data.append(ans)
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)

        self.setTempAllTime()
        for key, value in enumerate(data):
            self.setTemperature(key, value)
        
        if ( attr ):
            attr.set_value(data, len(data))
        
        return data

#------------------------------------------------------------------------------ 
#    Read Temperature_Max attribute
#------------------------------------------------------------------------------
    def read_Temperature_Max(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Max()"
        if ( self.ControllerType.lower() == "eurotherm" ):
            self.setTempMax((self.read_Temperature_All() or [-1])[0])
        elif ( self.ControllerType.lower() == "elotech" ):
            if ( self.tempAllTime() < long(time.time()) - 60 ):
                ans = self.read_Temperature_All()
            else:
                ans = self.temps()
            self.setTempMax(max([value for value in ans if value != TEMP_DEFAULT]))
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)            
        attr.set_value(self.tempMax())
        

#------------------------------------------------------------------------------ 
#    Read Temperature_SetPoint attribute
#------------------------------------------------------------------------------
    def read_Temperature_SetPoint(self, attr):
        print "In " + self.get_name() + ".read_Temperature_SetPoint()"
        data = self.TemperatureSetPoint
        attr.set_value(data)
        
#    read_Temperature_SetPoint()

#------------------------------------------------------------------------------ 
#    Write Temperature_SetPoint attribute
#------------------------------------------------------------------------------
    def write_Temperature_SetPoint(self, attr):
        print "In " + self.get_name() + ".write_Temperature_SetPoint()"
        data = []
        attr.get_write_value(data)
        self.TemperatureSetPoint = float(data[0])
        self.update_properties(['TemperatureSetPoint'])
        

#===============================================================================
# 
#    BakeOutControlDs command methods
#
#===============================================================================
#------------------------------------------------------------------------------ 
#    CheckPressure command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def CheckPressure(self):
        print "In " + self.get_name() + ".CheckPressure() at %s"%time.ctime()
        
        try:
            if time.time()<(self._pressureTime+self.MIN_CHECK_INTERVAL): 
                value = self._pressure
            else:
                print '\tDeviceProxy().read_attribute(%s)'%self.PressureAttribute
                av = self.pressureAttr.read()
                self._pressure = value = av.value
                self._pressureTime = av.time.totime() #time.time()
            if ( value > self.PressureSetPoint ):
                self.CheckStatus()
                if self.get_state()!=PyTango.DevState.OFF:
                    self.queue().put((0, ControllerCommand.STOP))
                    replies = 3
                    while ( replies ):
                        self.CheckStatus(force=True)
                        if ( self.get_state() not in (PyTango.DevState.OFF,PyTango.DevState.FAULT) ):
                            msg = 'Disabled due to pressure interlock (%1.2e) at %s\n'%(value,time.ctime())
                            print msg
                            self.set_status(msg)
                            self.set_state(PyTango.DevState.DISABLE)
                            break
                        replies -= 1
                        Event().wait(1.)
                    if ( not replies ):
                        msg = 'Device unresponsive to Stop command after pressure interlock!'
                        print msg
                        self.set_status(msg)
                        self.set_state(PyTango.DevState.FAULT)
            return value
        except Exception:
            print traceback.format_exc()
            raise Exception("PressureAttributeError")
    
    
#------------------------------------------------------------------------------ 
#    CheckStatus command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def CheckStatus(self,force=False,alarm=False):
        print "In " + self.get_name() + ".CheckStatus() at %s"%time.ctime()
        self.error_count = 0
        statusStr = ""
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                raise NotImplementedError
            elif ( self.ControllerType.lower() == "elotech" ):
                if force and time.time()<(self._statusTime+self.MIN_CHECK_INTERVAL):
                    print '\tStatus will be verified at most every %s seconds'%self.MIN_CHECK_INTERVAL
                    return self.get_status().rstrip()
                self._statusTime = time.time()
                if self.get_state()!=PyTango.DevState.FAULT:
                    status = [[False,False,False]]*self.zoneCount()
                    device = 1
                    instruction = "%02X" % ElotechInstruction.SEND
                    code = "%02X" % ElotechParameter.ZONE_ON_OFF
                    for zone in range(1, self.zoneCount() + 1):
                        ans = self.threadDict.get((device, zone, instruction, code))
                        if ( ans ):
                            status[zone - 1] = [bool(int(ans[11:13])), False, 0]
                        else: self.error_count+=1
                    for programNo in range(1, self.zoneCount() + 1):
                        params = self.params(programNo)
                        for zone in self.zones(programNo):
                            status[zone - 1][1] = bool(params[1] and not params[3])
                            status[zone - 1][2] = programNo
                    
                    for zone in range(1, self.zoneCount() + 1):
                        ON, Programmed, programNo  = status[zone - 1]
                        statusStr += "Zone %d is" % zone
                        if ( ON ):
                            statusStr += " ON"
                            if ( Programmed ):
                                statusStr += "| RUNNING"
                                if ( programNo ):
                                    statusStr += " program %d" % programNo
                            else:
                                statusStr += " | Not Programmed"
                        else:
                            statusStr += " OFF"
                            if ( Programmed ):
                                statusStr += " | Programmed, SHOULD BE RUNNING"
                                if ( programNo ):
                                    statusStr += " program %d" % programNo
                                alarm = True
                        statusStr += "\n"
                    if (self.error_count>MAX_ERRORS):
                        self.set_state(PyTango.DevState.UNKNOWN)
                        statusStr = 'Unable to communicate with device\n'+statusStr
                        statusStr += '\n %d communication errors'%self.error_count
                    elif ( alarm ):
                        statusStr += " | ALARM (program doesnt match!)"
                        self.set_state(PyTango.DevState.ALARM)
                    else:
                        if any(st[0] for st in status):
                            if any(st[1] for st in status):
                                statusStr = 'Bakeout Programs Running\n'+statusStr
                                self.set_state(PyTango.DevState.RUNNING)
                            else:
                                statusStr = 'Bakeout is ON\n'+statusStr
                                self.set_state(PyTango.DevState.ON)
                        elif self.get_state()!=PyTango.DevState.DISABLE:
                            statusStr = 'Bakeout is OFF\n'+statusStr
                            self.set_state(PyTango.DevState.OFF)
                    self.set_status(statusStr)
                    print '\tState=%s, Status=%s' % (self.get_state(),self.get_status())
                else:
                    self.set_status('The device suffered an unrecoverable exception, it has to be restarted')
        except Exception,e:
            print traceback.format_exc()
            raise e
        return statusStr.rstrip()
        
    
#------------------------------------------------------------------------------ 
#    Reset command
#
#    Description:
#
#------------------------------------------------------------------------------     
    def Reset(self):
        print "In " + self.get_name() + ".Reset()"

        self.set_state(PyTango.DevState.ON)
        
    
#------------------------------------------------------------------------------ 
#    SendCommand command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def SendCommand(self, command, retries=3):
        if self.Trace: print "In " + self.get_name() + ".SendCommand(%s)"%str(command)
        if self.error_count >= MAX_ERRORS: retries = 1
        reply = ''
        command = [c for c in command] #Converting hashable tuples to lists
        self.serialLock.acquire()
        try:
            while not reply and retries:
                retries-=1
                if ( self.ControllerType.lower() == "eurotherm" ):
                    reply = str(self.modbus().ReadHoldingRegisters([int(command[0]), int(command[1])])[0])
                    if self.Trace: print "\tRecv MODBUS: %s" % reply
                elif ( self.ControllerType.lower() == "elotech" ):
                    if ( len(command) < 4 or len(command) > 5):
                        raise ValueError
                    else:
                        package = []
                        for i,c in enumerate(command):
                            if ( i < 2 ): package.append("%02X" % int(c))
                            elif ( i < 4 ): package.append(c)
                            elif ( i == 4 ): package.append(self.elotech_value(c))
                        package.append(self.elotech_checksum(package))
                        sndCmd = "\n" + "".join(package) + "\r"
                        if self.Trace: "\tSend block: %s" % sndCmd.strip()
                        self.serial().flush() ##Needed to avoid errors parsing outdated strings!
                        self.serial().write(sndCmd)
                        ans = self.listen()
                        self.serial().flush() ##Needed to avoid errors parsing outdated strings!
                        if ( ans ):
                            try:
                                if self.Trace: print "\tRecv block: %s" % ans.strip()
                                err =  ElotechError.whatis(int(ans[7:9], 16)) if len(ans)>7 else ans ##It will raise KeyError if no error is found
                                msg = 'SendCommandException:%s'%(err)
                                if not retries: raise Exception(msg)
                                else: print 'Exception(%s): %d retries left'%(msg,retries)
                            except KeyError:
                                pass ##No errors, so we continue ...
                            #if ans[-2:]!=self.elotech_checksum(ans[:-2]): #Checksum calcullation may not match with expected one
                                #raise Exception('ChecksumFailed! %s!=%s'%(ans[-2:],self.elotech_checksum(ans[:-2])))
                            if sndCmd.strip()[:4]!=ans.strip()[:4]:
                                msg = 'AnswerDontMatchZone! send(%s)!=%s'%(sndCmd.strip(),ans.strip())
                                if not retries: raise Exception(msg)
                                else: print 'Exception(%s): %d retries left'%(msg,retries)
                            else:
                                reply = str(ans)
                        else:
                            if not retries: raise Exception("ConnectionError")
                            else: print 'Exception("ConnectionError"): %d retries left'%retries
                else:
                    raise Exception("UnknownController: %s" % self.ControllerType) 
            return reply
        except Exception,e:
            print ('Exception in %s.SendCommand(%s): %s' % (self.get_name(),command,traceback.format_exc()))
        finally:
            self.serialLock.release()

#------------------------------------------------------------------------------ 
#    Start command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def Start(self, programNo):
        print "In " + self.get_name() + ".Start()"
        try:
            self.update_program_properties()
            self.queue().put((programNo, ControllerCommand.START))
        except:
            print traceback.format_exc()
            
    
#------------------------------------------------------------------------------ 
#    Stop command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def Stop(self, zone):
        print "In " + self.get_name() + ".Stop()"
        self.queue().put((zone, ControllerCommand.STOP))

#===============================================================================
#
# BakeOutControlDSClass class definition
#
#===============================================================================
class BakeOutControlDSClass(PyTango.PyDeviceClass):
#    Class Properties    
    class_property_list = {
        }

#    Device Properties
    device_property_list = {
        "ControllerType":
            [PyTango.DevString, 
            " ", 
            [""] ], 
        "CommsDevice":
            [PyTango.DevString, 
            "", 
            [""] ], 
        "PressureAttribute":
            [PyTango.DevString, 
            "", 
            [""] ], 
        "PressureSetPoint":
            [PyTango.DevDouble, 
            "", 
            [ 2.e-4 ] ], 
        "TemperatureSetPoint":
            [PyTango.DevDouble, 
            "", 
            [ 250 ] ],
        "Trace":
            [PyTango.DevBoolean,
            "This controls the standard output of the device",
            [ False ] ],
        "Timewait":
            [PyTango.DevLong,
            "Time to wait, in milliseconds, between serial communications",
            [ 100 ] ],
        "Timeout":
            [PyTango.DevLong,
            "Timeout, in milliseconds, for an answer from the controller",
            [ 250 ] ],            
        "ProgramParams":
            [PyTango.DevVarStringArray, 
            "", 
            [ ] ],
        "Programs":
            [PyTango.DevVarStringArray, 
            "", 
            [ ] ],
        }

#    Command definitions
    cmd_list = {
        "CheckPressure":
            [[PyTango.DevVoid, ""], 
            [PyTango.DevDouble, ""],
            {
                'Polling period':15000,
            } ],  
        "CheckStatus":
            [[PyTango.DevVoid, ""], 
            [PyTango.DevString, ""],
            {
                'Polling period':15000,
            } ],  
        "Reset":
            [[PyTango.DevVoid, ""], 
            [PyTango.DevVoid, ""]], 
        "SendCommand":
            [[PyTango.DevVarStringArray, ""], 
            [PyTango.DevString, ""]],
        "Start":
            [[PyTango.DevShort, ""],
             [PyTango.DevVoid, ""]],
        "Stop":
            [[PyTango.DevShort, ""],
             [PyTango.DevVoid, ""]]             
        }

#    Attribute definitions
    attr_list = {
        #"Output_1":
            #[[PyTango.DevShort, 
            #PyTango.SCALAR, 
            #PyTango.READ]],
        #"Output_1_Limit":
            #[[PyTango.DevShort, 
            #PyTango.SCALAR, 
            #PyTango.READ_WRITE],
            #{"min value": 0,
             #"max value": 100}],
        #"Program_1":
            #[[PyTango.DevDouble, 
            #PyTango.IMAGE, 
            #PyTango.READ_WRITE, 3, 64]], 
        #"Program_1_Params":
            #[[PyTango.DevDouble, 
            #PyTango.SPECTRUM, 
            #PyTango.READ, 4]],
        #"Program_1_Zones":
            #[[PyTango.DevShort, 
            #PyTango.SPECTRUM, 
            #PyTango.READ_WRITE, 8]],
        #"Temperature_1":
            #[[PyTango.DevDouble, 
            #PyTango.SCALAR, 
            #PyTango.READ]],
        "Pressure":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Pressure_SetPoint":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Temperature_All":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 8]],         
        "Temperature_Max":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Temperature_SetPoint":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        }

#------------------------------------------------------------------------------ 
#    BakeOutControlDsClass Constructor
#------------------------------------------------------------------------------ 
    def __init__(self, name):
        PyTango.PyDeviceClass.__init__(self, name)
        self.set_type(name);
        print "In BakeOutControlDSClass constructor"

#    __init__()

    def dyn_attr(self,dev_list):
        print 'In BakeOutControlDSClass.dyn_attr(%s)'%dev_list
        for dev in dev_list:
            dev.dyn_attr()
 
#BakeOutControlDSClass()
 
#===============================================================================
#
# BakeOutControlDS class main method    
#
#===============================================================================
if __name__ == "__main__":
    try:
        py = PyTango.PyUtil(sys.argv)
        py.add_TgClass(BakeOutControlDSClass, BakeOutControlDS, "BakeOutControlDS")

        U = PyTango.Util.instance()
        U.server_init()
        U.server_run()

    except PyTango.DevFailed, e:
        print "Received a DevFailed exception:", e
    except Exception, e:
        print "An unforeseen exception occured...", e
