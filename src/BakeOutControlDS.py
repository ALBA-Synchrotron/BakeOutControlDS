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
from Queue import Queue
try:
    from tau.core.utils import Enumeration
except:
    from PyTango_utils.dicts import Enumeration

MAX_ERRORS = 5
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
class BakeOutControlDS(PyTango.Device_3Impl):
    _sndCmdLock = Lock()

    def checksum(self, x, y):
        res = 256 - x - y - 32
        while ( res <= 0 ): res += 256
        
        return "%02X" % res
    
#    checksum()

    def controller(self):
        if ( self._c ):
            return self._c
        raise AttributeError
        
#    controller()
        
    def elotech_checksum(self, args):
        res = 256 - sum([int(i, 16) for i in args])
        while ( res <= 0 ): res += 256
        
        return "%02X" % res
    
#    elotech_checksum()
     
    def elotech_value(self, value):
        v = Decimal(str(value))
        v = v.as_tuple()
        mantissa = "%04X" % int(("-" if v[0] else "") + "".join(map(str, v[1])))
        exponent = "%02X" % int(self.int2bin(v[2]), 2)        
        
        return mantissa[:2], mantissa[-2:], exponent 
    
#    elotech_value()
 
    def init_serial(self):
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
        
        
#    init_serial()
 
    def int2bin(self, n, count=8):
        return "".join([str((n >> y) & 1) for y in range(count - 1, -1, -1)])
    
#    int2bin()

    def limitAttr(self, zone, attr):
        print "In " + self.get_name() + ".limitAttr()"      
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.SEND 
            code = "%02X" % ElotechParameter.OUTPUT_LIMIT
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        ans = self.SendCommand([device, zone, instruction, code])
        if ( ans ):
            data = int(ans[9:13], 16)
        else:
            data = 100
        
        attr.set_value(data)
        
#    limitAttr()
            
    def listen(self):
        sleeper = Event()
        sleeper.wait(.05)        
        s = self.serial().readline()
        if ( not s ):
            ts = 5 
            while ( not s and ts ):
                sleeper.wait(.05)
                s = self.serial().readline()
                ts -= 1
        s += self.serial().readline()
        
        return s
    
#    listen()

    def modbus(self):
        if ( self._modbus ):
            return self._modbus
        raise AttributeError
    
#    modbus()
  
    def outputAttr(self, zone, attr):
        print "In " + self.get_name() + ".outputAttr()"        
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.SEND
            code = "%02X" % ElotechParameter.OUTPUT
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        ans = self.SendCommand([device, zone, instruction, code])
        if ( ans ):
            data = int(ans[9:13], 16)
        else:
            data = 0
        
        if ( data ):
            attr.set_value_date_quality(data, time.time(), PyTango.AttrQuality.ATTR_CHANGING)
        else:
            attr.set_value(data)
        
#    outputAttr()
 
    def params(self, key):
        return self._pParams.get(key)
                
#    params()
      
    def paramsAttr(self, programNo, attr):
        print "In " + self.get_name() + ".paramsAttr()"
        data = self.params(programNo)
        attr.set_value(data)
        
#    paramsAttr()

    def pressure(self):
        return self._pressure
    
#    pressure()
  
    def program(self, key):
        return self._programs.get(key)
    
#    program()
 
    def programAttr(self, programNo, attr):
        print "In " + self.get_name() + ".programAttr()"
        data = self.program(programNo)        
        dim_x = 3
        dim_y = len(data) / 3    
        attr.set_value(data, dim_x, dim_y)
        
#    programAttr()
        
    def queue(self):
        if ( self._q ):
            return self._q
        raise AttributeError
    
#    queue()
 
    def serial(self):
        if ( self._serial ):
            return self._serial
        raise AttributeError
    
#    serial()
   
    def setLimitAttr(self, zone, attr):
        print "In " + self.get_name() + ".setLimitAttr()"          
        data = []
        attr.get_write_value(data)
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.ACPT
            code = "%02X" % ElotechParameter.OUTPUT_LIMIT
            value = data[0]
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        self.SendCommand([device, zone, instruction, code, value])
        
#    setLimitAttr()
  
    def setParams(self, key, value):
        self._pParams[key] = value
        
#    setParams()

    def setPressure(self, pressure):
        self._pressure = pressure
        
#    setPressure()

    def setPressureTime(self):
        self._pressureTime = long(time.time())
        
#    setPressureTime()

    def setProgram(self, key, value):
        self._programs[key] = value
    
#    setProgram()    

    def setProgramAttr(self, programNo, attr):
        print "In " + self.get_name() + ".setProgramAttr()"
        data = []
        attr.get_write_value(data)
        if ( len(data) == 0 or len(data) % 3 != 0 ):
            raise ValueError
        self.setProgram(programNo, data)
        self.setParams(programNo, list(PARAMS_DEFAULT))
        
#    setProgramAttr()

    def setSerial(self, serial):
        self._serial = serial
        
#    setSerial()

    def setTempAllTime(self):
        self._tempAllTime = long(time.time())
        
#    setTempAllTime()
  
    def setTemperature(self, key, value):
        self._temps[key] = value
        
#    setTemperature()

    def setTempMax(self, tempMax):
        self._tempMax = tempMax
        
#    setTempMax()

    def setZones(self, key, value):
        self._pZones[key] = value
    
#    setZones()
 
    def setZonesAttr(self, programNo, attr):
        print "In " + self.get_name() + ".setZonesAttr()"
        data = []
        attr.get_write_value(data)
        dataSet = set(data)
        dataSet.intersection_update(i for i in range(1, self.zoneCount() + 1))
        for otherSet in [self.zones(pNo) for pNo in range(1, self.zoneCount() + 1) if pNo != programNo]:
            if ( dataSet.intersection(otherSet) ):
                dataSet.difference_update(otherSet)
        self.setZones(programNo, sorted(dataSet))
        
#    setZonesAttr()
 
    def tempAllTime(self):
        return self._tempAllTime
    
#    tempAllTime()
      
    def temperatureAttr(self, zone, attr=None):
        print "In " + self.get_name() + ".temperatureAttr()"
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = "%02X" % ElotechInstruction.SEND
            code = "%02X" % ElotechParameter.TEMP
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)
        
        ans = self.SendCommand([device, zone, instruction, code])
        if ( ans ):
            data = float(int(ans[9:13], 16)*10**int(ans[13:15], 16))
        else:
            #data = TEMP_DEFAULT
            raise Exception,'DataNotReceived'
        
        self.setTemperature(zone, data)
        
        if ( attr ):
            attr.set_value(data)
        
        return data
    
#    temperatureAttr()

    def temps(self):
        return self._temps.values()
    
#    temps()

    def tempMax(self):
        return self._tempMax
    
#    tempMax()
 
    def update_properties(self, property_list=[]):
        property_list = property_list or self.get_device_class().device_property_list.keys()
        if ( not hasattr(self, "db") or not self.db ):
            self.db = PyTango.Database()
        props = dict([(key, getattr(self, key)) for key in property_list if hasattr(self, key)])
        for key, value in props.items():
            print "\tUpdating property %s = %s" % (key, value)
            self.db.put_device_property(self.get_name(), {key:isinstance(value, list) and value or [value]})
            
#    update_properties()
       
    def zoneCount(self):
        return self._zoneCount
    
#    zoneCount()
        
    def zones(self, key):
        return self._pZones.get(key)
    
#    zones()
        
    def zonesAttr(self, programNo, attr):
        print "In " + self.get_name() + ".zonesAttr()"
        data = self.zones(programNo)        
        attr.set_value(data)
    
#    zonesAttr()
      
#------------------------------------------------------------------------------ 
#    Device constructor
#------------------------------------------------------------------------------ 
    def __init__(self, cl, name):
        print "In __init__()"        
        PyTango.Device_3Impl.__init__(self, cl, name)
        BakeOutControlDS.init_device(self)
        
#    __init__()

#------------------------------------------------------------------------------ 
#    Device destructor
#------------------------------------------------------------------------------ 
    def delete_device(self):
        print "In " + self.get_name() + ".delete_device()"        
        if ( self.ControllerType.lower() == "elotech" and self.serial() ):
            self.serial().close()
            
#    delete_device()

#------------------------------------------------------------------------------ 
#    Device initialization
#------------------------------------------------------------------------------ 
    def init_device(self):
        print "In " + self.get_name() + ".init_device()"        
        self.set_state(PyTango.DevState.ON)
        self.get_device_properties(self.get_device_class())
        self.update_properties()
        self._zoneCount = 1
        self._programs = None
        self._pParams = None
        self._pZones = None
        self._temps = None
        self._pressure = 0.
        self._pressureTime = long(0)
        self._tempMax = 0.
        self._tempAllTime = long(0)
        
        try: 
            self.pressureAttr = PyTango.AttributeProxy(self.PressureAttribute)
        except Exception: 
            self.pressureAttr = None
            raise Exception("PressureAttributeProxyError")
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                print "\tUsing an eurotherm controller..."
                self._modbus = PyTango.DeviceProxy(self.CommsDevice)
                self._modbus.ping()
            elif ( self.ControllerType.lower() == "elotech" ):
                print "\tUsing an elotech controller..."
                self.init_serial()
                self._serial.open()
                self._zoneCount = 8
                self._programs = dict.fromkeys((i for i in range(1, self._zoneCount + 1)), PROGRAM_DEFAULT)
                self._pParams = dict((i, list(PARAMS_DEFAULT)) for i in range(1, self._zoneCount + 1))
                self._pZones = dict.fromkeys((i for i in range(1, self._zoneCount + 1)), list())
                self._temps = dict.fromkeys((i for i in range(1, self._zoneCount + 1)), TEMP_DEFAULT)
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
        
        print "\tDevice server " + self.get_name() + " awaiting requests..."
        
#    init_device()

#------------------------------------------------------------------------------ 
#    Always excuted hook method
#------------------------------------------------------------------------------ 
    def always_executed_hook(self):
#        print "In " + self.get_name() + ".always_executed_hook()"        
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                self.modbus().ping()  
        except:
            self.set_state(PyTango.DevState.UNKNOWN)
            
#    always_executed_hook()

#------------------------------------------------------------------------------ 
#    Read Attribute Hardware
#------------------------------------------------------------------------------ 
    def read_attr_hardware(self, data):
#        print "In " + self.get_name() + ".read_attr_hardware()"        
        pass
        
#    read_attr_hardware()

#===============================================================================
# 
#    BakeOutControlDS read/write attribute methods
# 
#===============================================================================
#------------------------------------------------------------------------------ 
#    Read Output_1 attribute
#------------------------------------------------------------------------------ 
    def read_Output_1(self, attr):
        self.outputAttr(1, attr)
        
#    read_Output_1()
 
#------------------------------------------------------------------------------ 
#    Read Output_2 attribute
#------------------------------------------------------------------------------ 
    def read_Output_2(self, attr):
        self.outputAttr(2, attr)
        
#    read_Output_2()
 
#------------------------------------------------------------------------------ 
#    Read Output_3 attribute
#------------------------------------------------------------------------------ 
    def read_Output_3(self, attr):
        self.outputAttr(3, attr)
        
#    read_Output_3()
 
#------------------------------------------------------------------------------ 
#    Read Output_4 attribute
#------------------------------------------------------------------------------
    def read_Output_4(self, attr):
        self.outputAttr(4, attr)
        
#    read_Output_4()
 
#------------------------------------------------------------------------------ 
#    Read Output_5 attribute
#------------------------------------------------------------------------------
    def read_Output_5(self, attr):
        self.outputAttr(5, attr)
        
#    read_Output_5()
 
#------------------------------------------------------------------------------ 
#    Read Output_6 attribute
#------------------------------------------------------------------------------
    def read_Output_6(self, attr):
        self.outputAttr(6, attr)
        
#    read_Output_6()
 
#------------------------------------------------------------------------------ 
#    Read Output_7 attribute
#------------------------------------------------------------------------------
    def read_Output_7(self, attr):
        self.outputAttr(7, attr)
        
#    read_Output_7()
 
#------------------------------------------------------------------------------ 
#    Read Output_8 attribute
#------------------------------------------------------------------------------
    def read_Output_8(self, attr):
        self.outputAttr(8, attr)
        
#    read_Output_8()

#------------------------------------------------------------------------------ 
#    Read Output_1_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_1_Limit(self, attr):
        self.limitAttr(1, attr)
        
#    read_Output_1_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_1_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_1_Limit(self, attr):
        self.setLimitAttr(1, attr)
        
#    write_Output_1_Limit()

#------------------------------------------------------------------------------ 
#    Read Output_2_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_2_Limit(self, attr):
        self.limitAttr(2, attr)
        
#    read_Output_2_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_2_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_2_Limit(self, attr):
        self.setLimitAttr(2, attr)
        
#    write_Output_2_Limit()

#------------------------------------------------------------------------------ 
#    Read Output_3_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_3_Limit(self, attr):
        self.limitAttr(3, attr)
        
#    read_Output_3_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_3_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_3_Limit(self, attr):
        self.setLimitAttr(3, attr)
        
#    write_Output_3_Limit()

#------------------------------------------------------------------------------ 
#    Read Output_4_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_4_Limit(self, attr):
        self.limitAttr(4, attr)
        
#    read_Output_4_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_4_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_4_Limit(self, attr):
        self.setLimitAttr(4, attr)
        
#    write_Output_4_Limit()

#------------------------------------------------------------------------------ 
#    Read Output_5_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_5_Limit(self, attr):
        self.limitAttr(5, attr)
        
#    read_Output_5_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_5_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_5_Limit(self, attr):
        self.setLimitAttr(5, attr)
        
#    write_Output_5_Limit()

#------------------------------------------------------------------------------ 
#    Read Output_6_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_6_Limit(self, attr):
        self.limitAttr(6, attr)
        
#    read_Output_6_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_6_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_6_Limit(self, attr):
        self.setLimitAttr(6, attr)
        
#    write_Output_6_Limit()

#------------------------------------------------------------------------------ 
#    Read Output_7_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_7_Limit(self, attr):
        self.limitAttr(7, attr)
        
#    read_Output_7_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_7_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_7_Limit(self, attr):
        self.setLimitAttr(7, attr)
        
#    write_Output_7_Limit()

#------------------------------------------------------------------------------ 
#    Read Output_8_Limit attribute
#------------------------------------------------------------------------------
    def read_Output_8_Limit(self, attr):
        self.limitAttr(8, attr)
        
#    read_Output_8_Limit()

#------------------------------------------------------------------------------ 
#    Write Output_8_Limit attribute
#------------------------------------------------------------------------------
    def write_Output_8_Limit(self, attr):
        self.setLimitAttr(8, attr)
        
#    write_Output_8_Limit()

#------------------------------------------------------------------------------ 
#    Read Pressure attribute
#------------------------------------------------------------------------------
    def read_Pressure(self, attr):
        print "In " + self.get_name() + ".read_Pressure()"
        if ( not self.pressureAttr ):
            raise Exception("PressureAttributeError")
        
        self.setPressureTime()
        self.setPressure(self.CheckPressure())
        attr.set_value(self.pressure())
        
#    read_Pressure()

#------------------------------------------------------------------------------ 
#    Read Pressure_SetPoint attribute
#------------------------------------------------------------------------------
    def read_Pressure_SetPoint(self, attr):
        print "In " + self.get_name() + ".read_Pressure_SetPoint()"
        data = self.PressureSetPoint
        attr.set_value(data)

#    read_Pressure_SetPoint()

#------------------------------------------------------------------------------ 
#    Write Pressure_SetPoint attribute
#------------------------------------------------------------------------------
    def write_Pressure_SetPoint(self, attr):
        print "In " + self.get_name() + ".write_Pressure_SetPoint()"
        data = []
        attr.get_write_value(data)
        self.PressureSetPoint = float(data[0])
        self.update_properties()
        
#    write_Pressure_SetPoint()

#------------------------------------------------------------------------------ 
#    Read Program_1 attribute
#------------------------------------------------------------------------------        
    def read_Program_1(self, attr):
        print "In " + self.get_name() + ".read_Program_1()"
        self.programAttr(1, attr)
        
#    read_Program_1()
  
#------------------------------------------------------------------------------ 
#    Write Program_1 attribute
#------------------------------------------------------------------------------
    def write_Program_1(self, attr):
        print "In " + self.get_name() + ".write_Program_1()"
        self.setProgramAttr(1, attr)
        
#    write_Program_1()

#------------------------------------------------------------------------------ 
#    Read Program_2 attribute
#------------------------------------------------------------------------------        
    def read_Program_2(self, attr):
        print "In " + self.get_name() + ".read_Program_2()"
        self.programAttr(2, attr)
        
#    read_Program_2()
         
#------------------------------------------------------------------------------ 
#    Write Program_2 attribute
#------------------------------------------------------------------------------
    def write_Program_2(self, attr):
        print "In " + self.get_name() + ".write_Program_2()"
        self.setProgramAttr(2, attr)
        
#    write_Program_2()

#------------------------------------------------------------------------------ 
#    Read Program_3 attribute
#------------------------------------------------------------------------------ 
    def read_Program_3(self, attr):
        print "In " + self.get_name() + ".read_Program_3()"
        self.programAttr(3, attr)
        
#    read_Program_3()
        
#------------------------------------------------------------------------------ 
#    Write Program_3 attribute
#------------------------------------------------------------------------------
    def write_Program_3(self, attr):
        print "In " + self.get_name() + ".write_Program_3()"
        self.setProgramAttr(3, attr)
        
#    write_Program_3()

#------------------------------------------------------------------------------ 
#    Read Program_4 attribute
#------------------------------------------------------------------------------ 
    def read_Program_4(self, attr):
        print "In " + self.get_name() + ".read_Program_4()"
        self.programAttr(4, attr)
        
#    read_Program_4()
       
#------------------------------------------------------------------------------ 
#    Write Program_4 attribute
#------------------------------------------------------------------------------
    def write_Program_4(self, attr):
        print "In " + self.get_name() + ".write_Program_4()"
        self.setProgramAttr(4, attr)
        
#    write_Program_4()

#------------------------------------------------------------------------------ 
#    Read Program_5 attribute
#------------------------------------------------------------------------------ 
    def read_Program_5(self, attr):
        print "In " + self.get_name() + ".read_Program_5()"
        self.programAttr(5, attr)
        
#    read_Program_5()
        
#------------------------------------------------------------------------------ 
#    Write Program_5 attribute
#------------------------------------------------------------------------------
    def write_Program_5(self, attr):
        print "In " + self.get_name() + ".write_Program_5()"
        self.setProgramAttr(5, attr)
        
#    write_Program_5()

#------------------------------------------------------------------------------ 
#    Read Program_6 attribute
#------------------------------------------------------------------------------  
    def read_Program_6(self, attr):
        print "In " + self.get_name() + ".read_Program_6()"
        self.programAttr(6, attr)
        
#    read_Program_6()
        
#------------------------------------------------------------------------------ 
#    Write Program_6 attribute
#------------------------------------------------------------------------------
    def write_Program_6(self, attr):
        print "In " + self.get_name() + ".write_Program_6()"
        self.setProgramAttr(6, attr)
        
#    write_Program_6()

#------------------------------------------------------------------------------ 
#    Read Program_7 attribute
#------------------------------------------------------------------------------ 
    def read_Program_7(self, attr):
        print "In " + self.get_name() + ".read_Program_7()"
        self.programAttr(7, attr)
        
#    read_Program_7()
        
#------------------------------------------------------------------------------ 
#    Write Program_7 attribute
#------------------------------------------------------------------------------
    def write_Program_7(self, attr):
        print "In " + self.get_name() + ".write_Program_7()"
        self.setProgramAttr(7, attr)
        
#    write_Program_7()

#------------------------------------------------------------------------------ 
#    Read Program_8 attribute
#------------------------------------------------------------------------------ 
    def read_Program_8(self, attr):
        print "In " + self.get_name() + ".read_Program_8()"
        self.programAttr(8, attr)
        
#    read_Program_8()

#------------------------------------------------------------------------------ 
#    Write Program_8 attribute
#------------------------------------------------------------------------------
    def write_Program_8(self, attr):
        print "In " + self.get_name() + ".write_Program_8()"
        self.setProgramAttr(8, attr)
        
#    write_Program_8()

#------------------------------------------------------------------------------ 
#    Read Program_1_Params attribute
#------------------------------------------------------------------------------      
    def read_Program_1_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_1_Params()"
        self.paramsAttr(1, attr)
        
#    read_Program_1_Params()

#------------------------------------------------------------------------------ 
#    Read Program_2_Params attribute
#------------------------------------------------------------------------------       
    def read_Program_2_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_2_Params()"
        self.paramsAttr(2, attr)

#    read_Program_2_Params()

#------------------------------------------------------------------------------ 
#    Read Program_3_Params attribute
#------------------------------------------------------------------------------
    def read_Program_3_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_3_Params()"
        self.paramsAttr(3, attr)

#    read_Program_3_Params()

#------------------------------------------------------------------------------ 
#    Read Program_4_Params attribute
#------------------------------------------------------------------------------
    def read_Program_4_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_4_Params()"
        self.paramsAttr(4, attr)

#    read_Program_4_Params()

#------------------------------------------------------------------------------ 
#    Read Program_5_Params attribute
#------------------------------------------------------------------------------       
    def read_Program_5_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_5_Params()"
        self.paramsAttr(5, attr)

#    read_Program_5_Params()

#------------------------------------------------------------------------------ 
#    Read Program_6_Params attribute
#------------------------------------------------------------------------------ 
    def read_Program_6_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_6_Params()"
        self.paramsAttr(6, attr)

#    read_Program_6_Params()

#------------------------------------------------------------------------------ 
#    Read Program_7_Params attribute
#------------------------------------------------------------------------------
    def read_Program_7_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_7_Params()"
        self.paramsAttr(7, attr)
        
#    read_Program_7_Params()

#------------------------------------------------------------------------------ 
#    Read Program_8_Params attribute
#------------------------------------------------------------------------------        
    def read_Program_8_Params(self, attr):
        print "In " + self.get_name() + ".read_Program_8_Params()"
        self.paramsAttr(8, attr)
        
#    read_Program_8_Params()

#------------------------------------------------------------------------------ 
#    Read Program_1_Zones attribute
#------------------------------------------------------------------------------       
    def read_Program_1_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_1_Zones()"
        self.zonesAttr(1, attr)
        
#    read_Program_1_Zones()
        
#------------------------------------------------------------------------------ 
#    Write Program_1_Zones attribute
#------------------------------------------------------------------------------
    def write_Program_1_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_1_Zones()"
        self.setZonesAttr(1, attr)
        
#    write_Program_1_Zones()
 
#------------------------------------------------------------------------------ 
#    Read Program_2_Zones attribute
#------------------------------------------------------------------------------       
    def read_Program_2_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_2_Zones()"
        self.zonesAttr(2, attr)
        
#    read_Program_2_Zones()
        
#------------------------------------------------------------------------------ 
#    Write Program_2_Zones attribute
#------------------------------------------------------------------------------
    def write_Program_2_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_2_Zones()"
        self.setZonesAttr(2, attr)
        
#    write_Program_2_Zones()
 
#------------------------------------------------------------------------------ 
#    Read Program_3_Zones attribute
#------------------------------------------------------------------------------
    def read_Program_3_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_3_Zones()"
        self.zonesAttr(3, attr)
        
#    read_Program_3_Zones()
        
#------------------------------------------------------------------------------ 
#    Write Program_3_Zones attribute
#------------------------------------------------------------------------------
    def write_Program_3_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_3_Zones()"
        self.setZonesAttr(3, attr)
        
#    write_Program_3_Zones()
 
#------------------------------------------------------------------------------ 
#    Read Program_4_Zones attribute
#------------------------------------------------------------------------------
    def read_Program_4_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_4_Zones()"
        self.zonesAttr(4, attr)
         
#    read_Program_4_Zones()
        
#------------------------------------------------------------------------------ 
#    Write Program_4_Zones attribute
#------------------------------------------------------------------------------
    def write_Program_4_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_4_Zones()"
        self.setZonesAttr(4, attr)
        
#    write_Program_4_Zones()
       
#------------------------------------------------------------------------------ 
#    Read Program_5_Zones attribute
#------------------------------------------------------------------------------
    def read_Program_5_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_5_Zones()"
        self.zonesAttr(5, attr)
         
#    read_Program_5_Zones()
    
#------------------------------------------------------------------------------ 
#    Write Program_5_Zones attribute
#------------------------------------------------------------------------------
    def write_Program_5_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_5_Zones()"
        self.setZonesAttr(5, attr)
        
#    write_Program_5_Zones()
 
#------------------------------------------------------------------------------ 
#    Read Program_6_Zones attribute
#------------------------------------------------------------------------------
    def read_Program_6_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_6_Zones()"
        self.zonesAttr(6, attr)
        
#    read_Program_6_Zones()
        
#------------------------------------------------------------------------------ 
#    Write Program_6_Zones attribute
#------------------------------------------------------------------------------
    def write_Program_6_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_6_Zones()"
        self.setZonesAttr(6, attr)
        
#    write_Program_6_Zones()
 
#------------------------------------------------------------------------------ 
#    Read Program_7_Zones attribute
#------------------------------------------------------------------------------
    def read_Program_7_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_7_Zones()"
        self.zonesAttr(7, attr)
        
#    read_Program_7_Zones()
 
#------------------------------------------------------------------------------ 
#    Write Program_7_Zones attribute
#------------------------------------------------------------------------------         
    def write_Program_7_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_7_Zones()"
        self.setZonesAttr(7, attr)
       
#    write_Program_7_Zones()
       
#------------------------------------------------------------------------------ 
#    Read Program_8_Zones attribute
#------------------------------------------------------------------------------
    def read_Program_8_Zones(self, attr):
        print "In " + self.get_name() + ".read_Program_8_Zones()"
        self.zonesAttr(8, attr)
        
#    read_Program_8_Zones()

#------------------------------------------------------------------------------ 
#    Write Program_8_Zones attribute
#------------------------------------------------------------------------------          
    def write_Program_8_Zones(self, attr):
        print "In " + self.get_name() + ".write_Program_8_Zones()"
        self.setZonesAttr(8, attr)
        
#    write_Program_8_Zones()
 
#------------------------------------------------------------------------------ 
#    Read Temperature_1 attribute
#------------------------------------------------------------------------------
    def read_Temperature_1(self, attr):
        print "In " + self.get_name() + ".read_Temperature_1()"
        self.temperatureAttr(1, attr)
        
#    read_Temperature_1()
 
#------------------------------------------------------------------------------ 
#    Read Temperature_2 attribute
#------------------------------------------------------------------------------
    def read_Temperature_2(self, attr):
        print "In " + self.get_name() + ".read_Temperature_2()"
        self.temperatureAttr(2, attr)
        
#    read_Temperature_2()
   
#------------------------------------------------------------------------------ 
#    Read Temperature_3 attribute
#------------------------------------------------------------------------------
    def read_Temperature_3(self, attr):
        print "In " + self.get_name() + ".read_Temperature_3()"
        self.temperatureAttr(3, attr)
        
#    read_Temperature_3()
   
#------------------------------------------------------------------------------ 
#    Read Temperature_4 attribute
#------------------------------------------------------------------------------
    def read_Temperature_4(self, attr):
        print "In " + self.get_name() + ".read_Temperature_4()"
        self.temperatureAttr(4, attr)
        
#    read_Temperature_4()
   
#------------------------------------------------------------------------------ 
#    Read Temperature_5 attribute
#------------------------------------------------------------------------------
    def read_Temperature_5(self, attr):
        print "In " + self.get_name() + ".read_Temperature_5()"
        self.temperatureAttr(5, attr)
        
#    read_Temperature_5()
   
#------------------------------------------------------------------------------ 
#    Read Temperature_6 attribute
#------------------------------------------------------------------------------
    def read_Temperature_6(self, attr):
        print "In " + self.get_name() + ".read_Temperature_6()"
        self.temperatureAttr(6, attr)
        
#    read_Temperature_6()
   
#------------------------------------------------------------------------------ 
#    Read Temperature_7 attribute
#------------------------------------------------------------------------------
    def read_Temperature_7(self, attr):
        print "In " + self.get_name() + ".read_Temperature_7()"
        self.temperatureAttr(7, attr)
        
#    read_Temperature_7()
   
#------------------------------------------------------------------------------ 
#    Read Temperature_8 attribute
#------------------------------------------------------------------------------
    def read_Temperature_8(self, attr):
        print "In " + self.get_name() + ".read_Temperature_8()"
        self.temperatureAttr(8, attr)
        
#    read_Temperature_8()
  
#------------------------------------------------------------------------------ 
#    Read Temperature_All attribute
#------------------------------------------------------------------------------
    def read_Temperature_All(self, attr=None):
        print "In " + self.get_name() + ".read_Temperature_All()"
        if ( self.ControllerType.lower() == "eurotherm" ):
            data = float(self.modbus().ReadHoldingRegisters([1, 1])[0])
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
    
#    read_Temperature_All()

#------------------------------------------------------------------------------ 
#    Read Temperature_Max attribute
#------------------------------------------------------------------------------
    def read_Temperature_Max(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Max()"
        if ( self.ControllerType.lower() == "eurotherm" ):
            self.setTempMax(self.read_Temperature_All())
        elif ( self.ControllerType.lower() == "elotech" ):
            if ( self.tempAllTime() < long(time.time()) - 60 ):
                ans = self.read_Temperature_All()
            else:
                ans = self.temps()
            self.setTempMax(max([value for value in ans if value != TEMP_DEFAULT]))
        else:
            raise Exception("UnknownController: %s" % self.ControllerType)            
        attr.set_value(self.tempMax())
        
#    read_Temperature_Max()

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
        self.update_properties()
        
#    write_Temperature_SetPoint()

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
        print "In " + self.get_name() + ".CheckPressure()"
        
        try:
            value = self.pressureAttr.read().value
            if ( value > self.PressureSetPoint ):
                self.queue().put((0, ControllerCommand.STOP))
                replies = 3
                while ( replies ):
                    self.CheckStatus()
                    if ( self.get_state() != PyTango.DevState.ON ):
                        self.set_state(PyTango.DevState.DISABLE)
                        break
                    replies -= 1
                    Event().wait(.01)
                if ( not replies ):
                    self.set_state(PyTango.DevState.ALARM)
                        
            return value
        except Exception:
            raise Exception("PressureAttributeError")
    
#    CheckPressure()
    
#------------------------------------------------------------------------------ 
#    CheckStatus command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def CheckStatus(self):
        print "In " + self.get_name() + ".CheckStatus()"
        error_count = 0
        
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError
        elif ( self.ControllerType.lower() == "elotech" ):
            status = [False]*self.zoneCount()
            device = 1
            instruction = "%02X" % ElotechInstruction.SEND
            code = "%02X" % ElotechParameter.ZONE_ON_OFF
            for zone in range(1, self.zoneCount() + 1):
                ans = self.SendCommand([device, zone, instruction, code])
                if ( ans ):
                    status[zone - 1] = [bool(int(ans[11:13])), False, 0]
                else: error_count+=1
            for programNo in range(1, self.zoneCount() + 1):
                params = self.params(programNo)
                for zone in self.zones(programNo):
                    status[zone - 1][1] = bool(params[1] and not params[3])                 
                    status[zone - 1][2] = programNo
            
            alarm = False
            statusStr = ""
            for zone in range(1, self.zoneCount() + 1):
                s, r, p = status[zone - 1]
                statusStr += "Zone %d is" % zone
                if ( s ):
                    statusStr += " ON"
                    if ( r ):
                        statusStr += " | RUNNING"
                        if ( p ):
                            statusStr += " program %d" % p
                    else:
                        statusStr += " | ALARM!"
                        alarm = True
                else:
                    statusStr += " OFF"
                    if ( r ):
                        statusStr += " | SHOULD BE RUNNING"
                        if ( p ):
                            statusStr += " program %d" % p
                        statusStr += " | ALARM!"
                        alarm = True
                statusStr += "\n"
        
        if (error_count>MAX_ERRORS):
            self.set_state(PyTango.DevState.UNKNOWN)
        elif ( alarm ):
            self.set_state(PyTango.DevState.ALARM)
        else:
            if ( any(st[0] for st in status) ):
                self.set_state(PyTango.DevState.RUNNING)
            else:
                self.set_state(PyTango.DevState.ON)
        return statusStr.rstrip()
        
#    CheckStatus()      
    
#------------------------------------------------------------------------------ 
#    Reset command
#
#    Description:
#
#------------------------------------------------------------------------------     
    def Reset(self):
        print "In " + self.get_name() + ".Reset()"

        self.set_state(PyTango.DevState.ON)
        
#    Reset()
    
#------------------------------------------------------------------------------ 
#    SendCommand command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def SendCommand(self, command):
        print "In " + self.get_name() + ".SendCommand()"
        
        self._sndCmdLock.acquire()
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                reply = str(self.modbus().ReadHoldingRegisters([int(command[0]), int(command[1])])[0])
                print "\tRecv MODBUS: %s" % reply
            elif ( self.ControllerType.lower() == "elotech" ):
                if ( len(command) < 4 or len(command) > 5):
                    raise ValueError
                else:
                    package = []
                    for i in range(len(command)):
                        if ( i < 2 ):
                            command[i] = ["%02X" % int(command[i])]
                        elif ( i < 4 ):
                            command[i] = [command[i]]
                        elif ( i == 4 ):
                            command[i] = self.elotech_value(command[i])
                        package.extend(command[i])            
                    package.append(self.elotech_checksum(package))
                    sndCmd = "\n" + "".join(package) + "\r"
                    print "\tSend block: %s" % sndCmd.strip()
                    self.serial().write(sndCmd)
                    ans = self.listen()
                    self.serial().flush() ##Needed to avoid errors parsing outdated strings!
                    if ( ans ):
                        try:
                            print "\tRecv block: %s" % ans.strip()
                            raise Exception(ElotechError.whatis(int(ans[7:9], 16))) ##It will raise KeyError if no error is found
                        except KeyError:
                            pass ##No errors, so we continue ...
                        #if ans[-2:]!=self.elotech_checksum(ans[:-2]): #Checksum calcullation may not match with expected one
                            #raise Exception('ChecksumFailed! %s!=%s'%(ans[-2:],self.elotech_checksum(ans[:-2])))
                        if sndCmd.strip()[:4]!=ans.strip()[:4]:
                            raise Exception('AnswerDontMatchZone! %s!=%s'%(ans.strip()[:4],sndCmd.strip()[:4]))
                    else:
                        raise Exception("ConnectionError")
                    reply = str(ans)
            else:
                raise Exception("UnknownController: %s" % self.ControllerType) 
            
            return reply
        except Exception,e:
            print ('Exception in %s.SendCommand: %s' % (self.get_name(),str(e)))
        finally:
            self._sndCmdLock.release()
            
#    SendCommand()
    
#------------------------------------------------------------------------------ 
#    Start command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def Start(self, programNo):
        print "In " + self.get_name() + ".Start()"

        self.queue().put((programNo, ControllerCommand.START))
            
#    Start()
    
#------------------------------------------------------------------------------ 
#    Stop command
#
#    Description:
#
#------------------------------------------------------------------------------ 
    def Stop(self, zone):
        print "In " + self.get_name() + ".Stop()"
        
        self.queue().put((zone, ControllerCommand.STOP))
                
#    Stop()

#BakeOutControlDS()

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
        
#    __init__()
              
    def device(self):
        return self._ds
    
#    device()

    def event(self, programNo):
        return self._events.get(programNo)
    
#    event()
 
    def isRunning(self, programNo):
        if ( programNo ):
            return bool(self.stepper(programNo)) and self.stepper(programNo).isAlive()
        else:
            if any( [bool(self.stepper(programNo)) and self.stepper(programNo).isAlive() for programNo in range(self._programCount)] ):
                return True
            return False

#    isRunning()
                 
    def program(self, programNo):
        return self._programs.get(programNo)
        
#    program()

    def programCount(self):
        return self._programCount
    
#    programCount()
      
    def queue(self):
        return self._q
    
#    queue()
       
    def run(self):            
        while ( True ):      
            programNo, command = self.queue().get()
            
            if ( command == ControllerCommand.STOP ):
                for progNo in (programNo and (programNo,) or range(1, self.programCount() + 1)):
                    if ( self.isRunning(progNo) ):
                        print "\t", time.strftime("%H:%M:%S"), "%s: Stopping bakeout program %d" % (self.getName(), progNo)                
                        self.setProgram(progNo, None)
                        self.event(progNo).set()
            elif ( command == ControllerCommand.START ):               
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
                            step = program.pop()
                            stepper = Stepper(self, programNo, step, zones)
                            self.setStepper(programNo, stepper)
                            stepper.start()
            elif ( command == ControllerCommand.PAUSE ):
                raise NotImplementedError
            elif ( command == ControllerCommand.FEED ):
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
            self.queue().task_done()
            Event().wait(.01)
#    run()

    def setProgram(self, programNo, program):
        self._programs[programNo] = program
        
#    setProgram()
 
    def setStepper(self, programNo, stepper):
        self._steppers[programNo] = stepper
        
#    setStepper()
    
    def stepper(self, programNo):
        return self._steppers.get(programNo)
        
#    stepper()        
    
    def unflattenProgram(self, flatProgram):
        if ( flatProgram == PROGRAM_DEFAULT ):
            program = PROGRAM_DEFAULT
        else:
            program = []
            for i in reversed(range(len(flatProgram) / 3)):
                program.append([item for item in flatProgram[i * 3:(i + 1) * 3]])
            
        return program
    
#    unflattenProgram()
   
#Controller()

#===============================================================================
# 
# Stepper class definition
# 
#===============================================================================
class Stepper(threading.Thread):
    def __init__(self, controller, programNo, step, zones):
        threading.Thread.__init__(self, name="Bakeout-Program-%s" % programNo)

        self._ds = controller.device()
        self._q = controller.queue()
        self._event = controller.event(programNo)
        self._programNo = programNo
        self._step = step
        self._zones = zones
        
        params = self._ds.params(programNo)
        self._sTemp = params[0] = self.maxDiff(step[0], zones)
        params[1] = time.time()
        params[2] = params[3] = 0.
        self._ds.setParams(programNo, params)
        
#    __init__()

    def execute(self, command):
        self._ds.SendCommand(command)
        
#    execute()
        
    def event(self):
        return self._event
        
#    event()

    def feed(self):
        self._q.put((self._programNo, ControllerCommand.FEED))
        
#    feed()
        
    def isFinished(self):
        return not bool(self._step)
    
#    isFinished()

    def maxDiff(self, temp, zones):
        ta = [self._ds.temperatureAttr(z) for z in zones]
        ts = [t for t in ta if t != TEMP_DEFAULT]
        dt = [abs(temp - t) for t in ts]
        return dt and ts[dt.index(max(dt))] or TEMP_DEFAULT
    
#    maxDiff()
 
    def params(self):
        return self._ds.params(self._programNo)
    
#    params()

    def ramp(self):
        return self._step[1]
    
#    ramp()        
         
    def run(self):
        for zone in self.zones():
            start_command = [1, zone,
                             "%02X" % ElotechInstruction.ACPT,
                             "%02X" % ElotechParameter.ZONE_ON_OFF,
                             1]
            self.execute(start_command)
        while ( not self.isFinished() ):
            print "\t", time.strftime("%H:%M:%S"), "%s: Starting bakeout" % self.getName(), self._step
            temp = self.temp()
            ramp = self.ramp()
            timeout = 60. * (60. * self.time() + abs(self.startTemp() - temp) / ramp)
            self.setStartTemp(temp)
            for zone in self.zones():
                ramp_command = [1, zone,
                                "%02X" % ElotechInstruction.ACPT,
                                "%02X" % ElotechParameter.RAMP,
                                ramp]
                self.execute(ramp_command)
            for zone in self.zones():                
                temp_command = [1, zone,
                                "%02X" % ElotechInstruction.ACPT,
                                "%02X" % ElotechParameter.SETPOINT,
                                temp]
                self.execute(temp_command)
            print "\t", time.strftime("%H:%M:%S"), "%s: Baking zones %s for %f minutes" % (self.getName(), self.zones(), timeout / 60. )
            self.event().wait(timeout)
            self.event().clear()
            print "\t", time.strftime("%H:%M:%S"), "%s: Awaiting feed" % self.getName()
            self.feed()
            self.event().wait()
            self.event().clear()
        print "\t", time.strftime("%H:%M:%S"), "%s: Stopping bakeout" % self.getName()
        for zone in self.zones():
            stop_command = [1, zone,
                            "%02X" % ElotechInstruction.ACPT,
                            "%02X" % ElotechParameter.ZONE_ON_OFF,
                            0]
            self.execute(stop_command)
        params = self.params()
        params[3] = time.time()
        self.setParams(params)
        print "\t", time.strftime("%H:%M:%S"), "%s: Done" % self.getName()
        
#    run()
 
    def setParams(self, params):
        self._ds.setParams(self._programNo, params)
        
#    setParams()        
   
    def setStartTemp(self, temp):
        self._sTemp = temp
        
#    setStartTemp()

    def setStep(self, step):
        self._step = step
        
#    setStep()

    def startTemp(self):
        return self._sTemp
   
#    startTemp()
 
    def temp(self):
        return self._step[0]
    
#    temp()        

    def time(self):
        return self._step[2]
    
#    time()        

    def zones(self):
        return self._zones
    
#    zones()
 
#Stepper()

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
        }

#    Command definitions
    cmd_list = {
        "CheckPressure":
            [[PyTango.DevVoid, ""], 
            [PyTango.DevDouble, ""]],
        "CheckStatus":
            [[PyTango.DevVoid, ""], 
            [PyTango.DevString, ""]],  
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
        "Output_1":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_2":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_3":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_4":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_5":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_6":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_7":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_8":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Output_1_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],
        "Output_2_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],
        "Output_3_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],
        "Output_4_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],
        "Output_5_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],
        "Output_6_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],
        "Output_7_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],
        "Output_8_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE],
            {"min value": 0,
             "max value": 100}],                                                                                                                                                                                         
        "Pressure":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Pressure_SetPoint":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Program_1":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]], 
        "Program_2":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]], 
        "Program_3":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]], 
        "Program_4":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]], 
        "Program_5":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]], 
        "Program_6":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]], 
        "Program_7":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]], 
        "Program_8":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3, 64]],
        "Program_1_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]],
        "Program_2_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]], 
        "Program_3_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]], 
        "Program_4_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]], 
        "Program_5_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]],             
        "Program_6_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]], 
        "Program_7_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]], 
        "Program_8_Zones":
            [[PyTango.DevShort, 
            PyTango.SPECTRUM, 
            PyTango.READ_WRITE, 8]],                 
        "Program_1_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]],
        "Program_2_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]], 
        "Program_3_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]], 
        "Program_4_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]], 
        "Program_5_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]],             
        "Program_6_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]], 
        "Program_7_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]], 
        "Program_8_Params":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 4]],            
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
        "Temperature_1":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Temperature_2":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_3":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_4":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_5":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],             
        "Temperature_6":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_7":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_8":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]]           
        }

#------------------------------------------------------------------------------ 
#    BakeOutControlDsClass Constructor
#------------------------------------------------------------------------------ 
    def __init__(self, name):
        PyTango.PyDeviceClass.__init__(self, name)
        self.set_type(name);
        print "In BakeOutControlDSClass constructor"

#    __init__()
 
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
