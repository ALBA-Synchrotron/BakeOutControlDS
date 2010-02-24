import PyTango
import serial
import sys
import traceback
import time
from BakeoutControl import COMMAND, BakeoutController
from BakeoutEnumeration import *
from decimal import Decimal
from threading import Event


#===============================================================================
#
# BakeoutControlDS class definition
#
#===============================================================================
class BakeoutControlDS(PyTango.Device_3Impl):
#===============================================================================
# Device constructor
#===============================================================================
    def __init__(self, cl, name):
        PyTango.Device_3Impl.__init__(self, cl, name)
        BakeoutControlDS.init_device(self)

#===============================================================================
# Device destructor
#===============================================================================
    def delete_device(self):
        print "[Device delete_device method] for device", self.get_name()

        if ( self.ControllerType.lower() == "elotech" and self._serial ):
            print "delete_device(): Closing elotech serial line...",
            self._serial.close()
            print "done"

#===============================================================================
# Device initialization
#===============================================================================
    def init_device(self):
        print "In " + self.get_name() + ".init_device()"
        self.set_state(PyTango.DevState.ON)
        self.get_device_properties(self.get_device_class())
        self.update_properties()
        self._pressureVal = self._tempMax = None
        self._pressureTime = self._tempTime = 0
        self._temps = dict.fromkeys((i for i in range(1, 9)), 1200.)
        
        try: 
            self.pressureAttr = PyTango.AttributeProxy(self.PressureAttribute)
        except Exception, e: 
            self.pressureAttr = None
            print "Unable to create AttributeProxy for %s: %s" % (self.PressureAttribute, str(e))
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                print "\tUsing an eurotherm controller..."
                self.modbus = PyTango.DeviceProxy(self.CommsDevice)
                self.modbus.ping()
            elif ( self.ControllerType.lower() == "elotech" ):
                print "\tUsing an elotech controller..."
                self.init_serial()
                self._serial.open()
                self._noZones = 8
                self._programs = dict.fromkeys((i for i in range(1, self._noZones + 1)), NO_PROGRAM)
                self._pTimes = dict.fromkeys((i for i in range(1, self._noZones + 1)), 0.)
                self._pTemps = dict.fromkeys((i for i in range(1, self._noZones + 1)), 0.)                
                self._c = BakeoutController(self)
                self._c.setDaemon(True)
                self._c.start()
                self._q = self._c.getQueue()
                self._q.put((0, COMMAND.get("STOP")))                
            else:
                raise "UnknownController: %s" % self.ControllerType
        except Exception, e:
            PyTango.Except.throw_exception("BakeoutControlDS_initDeviceException", str(e), str(e))
            self.modbus = self._serial = None
        
        print "\tDevice server " + self.get_name() + " awaiting requests..."

#===============================================================================
# Always excuted hook method
#===============================================================================
    def always_executed_hook(self):
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                self.modbus.ping()  
        except:
            self.set_state(PyTango.DevState.FAULT)

#===============================================================================
# 
# BakeoutControlDS read/write attribute methods
#
#===============================================================================
#===============================================================================
# Read Attribute Hardware
#===============================================================================
    def read_attr_hardware(self, data):
        print "In " + self.get_name() + ".read_attr_hardware()"
    
#===============================================================================
# Read specified zone program from attribute
#===============================================================================
    def getProgramAttr(self, zone, attr):
        print "In " + self.get_name() + ".getProgramAttr()"
        
        data = self._programs.get(zone)        
        dim_x = 3
        dim_y = len(data) / 3    
        attr.set_value(data, dim_x, dim_y)   

#===============================================================================
# Write specified zone program to attribute
#===============================================================================
    def setProgramAttr(self, zone, attr):
        print "In " + self.get_name() + ".setProgramAttr()"
        
        data = []
        attr.get_write_value(data)
        if ( len(data) == 0 or len(data) %3 != 0 ): raise "DataLengthException"
        self._programs[zone] = data
    
#===============================================================================
# Read program execute time from attribute
#===============================================================================
    def getProgramTimeAttr(self, zone, attr):
        print "In " + self.get_name() + ".getProgramTimeAttr()"
        
        data = self._pTimes.get(zone)        
        attr.set_value(data)

#===============================================================================
# Read program execute temperature from attribute
#===============================================================================
    def getProgramTempAttr(self, zone, attr):
        print "In " + self.get_name() + ".getProgramTempAttr()"
        
        data = self._pTemps.get(zone)        
        attr.set_value(data)

#===============================================================================
# Read specified zone temperature from attribute   
#===============================================================================
    def getTemperatureAttr(self, zone, attr=None):
        print "In " + self.get_name() + ".getTemperatureAttr()"
        
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise "NotImplemented"        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = ELOTECH_ISTR.get("SEND")
            code = ELOTECH_PARAM.get("TEMP")
        else:
            raise "UnknownController: %s" % self.ControllerType
        
        ans = self.SendCommand([device, zone, instruction, code])
        if ( ans ):
            data = float(int(ans[9:13], 16)*10**int(ans[13:15], 16))
        else:
            data = None
        
        if ( attr ):
            attr.set_value(data)
        
        return data

#===============================================================================
# Read Pressure attribute
#===============================================================================
    def read_Pressure(self, attr):
        print "In " + self.get_name() + ".read_Pressure()"

        if ( not self.pressureAttr ):
            raise "WrongPressureAttribute(%s)" % (hasattr(self, "PressureAttribute") and str(self.PressureAttribute) or "")
        
        self._pressureTime = time.time()
        self._pressureVal = self.GetPressure()
        attr.set_value(self._pressureVal)

#===============================================================================
# Read Pressure_SetPoint attribute
#===============================================================================
    def read_Pressure_SetPoint(self, attr):
        print "In " + self.get_name() + ".read_Pressure_SetPoint()"

        data = self.PressureSetPoint
        attr.set_value(data)

#===============================================================================
# Write Pressure_SetPoint attribute
#===============================================================================
    def write_Pressure_SetPoint(self, attr):
        print "In " + self.get_name() + ".write_Pressure_SetPoint()"

        data = []
        attr.get_write_value(data)
        self.PressureSetPoint = float(data[0])
        self.update_properties()
        
#===============================================================================
# Read Program_Zone1 attribute
#===============================================================================
    def read_Program_Zone1(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone1()"
        
        self.getProgramAttr(1, attr)
  
#===============================================================================
# Write Program_Zone1 attribute
#===============================================================================
    def write_Program_Zone1(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone1()"
        
        self.setProgramAttr(1, attr)
        
#===============================================================================
# Read Program_Zone2 attribute
#===============================================================================
    def read_Program_Zone2(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone2()"
        
        self.getProgramAttr(2, attr)
         
#===============================================================================
# Write Program_Zone2 attribute
#===============================================================================
    def write_Program_Zone2(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone2()"
        
        self.setProgramAttr(2, attr)
 
#===============================================================================
# Read Program_Zone3 attribute
#===============================================================================
    def read_Program_Zone3(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone3()"
        
        self.getProgramAttr(3, attr)
        
#===============================================================================
# Write Program_Zone3 attribute
#===============================================================================
    def write_Program_Zone3(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone3()"
        
        self.setProgramAttr(3, attr)
 
#===============================================================================
# Read Program_Zone4 attribute
#===============================================================================
    def read_Program_Zone4(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone4()"
        
        self.getProgramAttr(4, attr)
       
#===============================================================================
# Write Program_Zone4 attribute
#===============================================================================
    def write_Program_Zone4(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone4()"
        
        self.setProgramAttr(4, attr)
 
#===============================================================================
# Read Program_Zone5 attribute
#===============================================================================
    def read_Program_Zone5(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone5()"
        
        self.getProgramAttr(5, attr)
        
#===============================================================================
# Write Program_Zone5 attribute
#===============================================================================
    def write_Program_Zone5(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone5()"
        
        self.setProgramAttr(5, attr)
  
#===============================================================================
# Read Program_Zone6 attribute
#===============================================================================
    def read_Program_Zone6(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone6()"
        
        self.getProgramAttr(6, attr)
        
#===============================================================================
# Write Program_Zone6 attribute
#===============================================================================
    def write_Program_Zone6(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone6()"
        
        self.setProgramAttr(6, attr)
 
#===============================================================================
# Read Program_Zone7 attribute
#===============================================================================
    def read_Program_Zone7(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone7()"
        
        self.getProgramAttr(7, attr)
        
#===============================================================================
# Write Program_Zone7 attribute
#===============================================================================
    def write_Program_Zone7(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone7()"
        
        self.setProgramAttr(7, attr)
 
#===============================================================================
# Read Program_Zone8 attribute
#===============================================================================
    def read_Program_Zone8(self, attr):
        print "In " + self.get_name() + ".read_Program_Zone8()"
        
        self.getProgramAttr(8, attr)

#===============================================================================
# Write Program_Zone8 attribute
#===============================================================================
    def write_Program_Zone8(self, attr):
        print "In " + self.get_name() + ".write_Program_Zone8()"
        
        self.setProgramAttr(8, attr)
       
#===============================================================================
# Read Program_Temp_Zone1 attribute
#===============================================================================
    def read_Program_Temp_Zone1(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone1()"
        
        self.getProgramTempAttr(1, attr)
       
#===============================================================================
# Read Program_Temp_Zone2 attribute
#===============================================================================
    def read_Program_Temp_Zone2(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone2()"
        
        self.getProgramTempAttr(2, attr)

#===============================================================================
# Read Program_Temp_Zone3 attribute
#===============================================================================
    def read_Program_Temp_Zone3(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone3()"
        
        self.getProgramTempAttr(3, attr)

#===============================================================================
# Read Program_Time_Zone4 attribute
#===============================================================================
    def read_Program_Temp_Zone4(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone4()"
        
        self.getProgramTempAttr(4, attr)
       
#===============================================================================
# Read Program_Time_Zone5 attribute
#===============================================================================
    def read_Program_Temp_Zone5(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone5()"
        
        self.getProgramTempAttr(5, attr)
 
#===============================================================================
# Read Program_Temp_Zone6 attribute
#===============================================================================
    def read_Program_Temp_Zone6(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone6()"
        
        self.getProgramTempAttr(6, attr)

#===============================================================================
# Read Program_Time_Zone7 attribute
#===============================================================================
    def read_Program_Temp_Zone7(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone7()"
        
        self.getProgramTempAttr(7, attr)
        
#===============================================================================
# Read Program_Time_Zone8 attribute
#===============================================================================
    def read_Program_Temp_Zone8(self, attr):
        print "In " + self.get_name() + ".read_Program_Temp_Zone8()"
        
        self.getProgramTempAttr(8, attr)
        
#===============================================================================
# Read Program_Time_Zone1 attribute
#===============================================================================
    def read_Program_Time_Zone1(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone1()"
        
        self.getProgramTimeAttr(1, attr)
       
#===============================================================================
# Read Program_Time_Zone2 attribute
#===============================================================================
    def read_Program_Time_Zone2(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone2()"
        
        self.getProgramTimeAttr(2, attr)

#===============================================================================
# Read Program_Time_Zone3 attribute
#===============================================================================
    def read_Program_Time_Zone3(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone3()"
        
        self.getProgramTimeAttr(3, attr)

#===============================================================================
# Read Program_Time_Zone4 attribute
#===============================================================================
    def read_Program_Time_Zone4(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone4()"
        
        self.getProgramTimeAttr(4, attr)
       
#===============================================================================
# Read Program_Time_Zone5 attribute
#===============================================================================
    def read_Program_Time_Zone5(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone5()"
        
        self.getProgramTimeAttr(5, attr)
 
#===============================================================================
# Read Program_Time_Zone6 attribute
#===============================================================================
    def read_Program_Time_Zone6(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone6()"
        
        self.getProgramTimeAttr(6, attr)

#===============================================================================
# Read Program_Time_Zone7 attribute
#===============================================================================
    def read_Program_Time_Zone7(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone7()"
        
        self.getProgramTimeAttr(7, attr)
        
#===============================================================================
# Read Program_Time_Zone8 attribute
#===============================================================================
    def read_Program_Time_Zone8(self, attr):
        print "In " + self.get_name() + ".read_Program_Time_Zone8()"
        
        self.getProgramTimeAttr(8, attr)

#===============================================================================
# Read Temperature_All attribute
#===============================================================================
    def read_Temperature_All(self, attr=None):
        print "In " + self.get_name() + ".read_Temperature_All()"
        
        self._tempTime = time.time()
        if ( self.ControllerType.lower() == "eurotherm" ):
            data = float(self.modbus.ReadHoldingRegisters([1, 1])[0])
            print "Recv MODBUS: %s" % data
        elif ( self.ControllerType.lower() == "elotech" ):
            data = []                        
            for zone in range(1, self._noZones + 1):
                result = self.getTemperatureAttr(zone)
                data.append(result)
        else:
            raise "UnknownController: %s" % self.ControllerType

        for i, value in enumerate(data):
            self._temps[i] = value
        
        if ( attr is not None ):
            attr.set_value(data, len(data))
        
        return data

#===============================================================================
# Read Temperature_Max attribute
#===============================================================================
    def read_Temperature_Max(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Max()"
                
        if ( self.ControllerType.lower() == "eurotherm" ):
            self._tempMax = self.read_Temperature_All()
        elif ( self.ControllerType.lower() == "elotech" ):
            if ( self._tempTime < time.time() - 60 ):
                ans = self.read_Temperature_All()
            else:
                ans = self._temps.values()
            self._tempMax = max([value for value in ans if value != 1200.0])
        else:
            raise "UnknownController: %s" % self.ControllerType            
        attr.set_value(self._tempMax)

#===============================================================================
# Read Temperature_SetPoint attribute
#===============================================================================
    def read_Temperature_SetPoint(self, attr):
        print "In " + self.get_name() + ".read_Temperature_SetPoint()"
        
        data = self.TemperatureSetPoint
        attr.set_value(data)

#===============================================================================
# Write Temperature_SetPoint attribute
#===============================================================================
    def write_Temperature_SetPoint(self, attr):
        print "In " + self.get_name() + ".write_Temperature_SetPoint()"

        data = []
        attr.get_write_value(data)
        self.TemperatureSetPoint = float(data[0])
        self.update_properties()
 
#===============================================================================
# Read Temperature_Zone1 attribute
#===============================================================================
    def read_Temperature_Zone1(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone1()"
        
        self.getTemperatureAttr(1, attr)
 
#===============================================================================
# Read Temperature_Zone2 attribute
#===============================================================================
    def read_Temperature_Zone2(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone2()"
        
        self.getTemperatureAttr(2, attr)
   
#===============================================================================
# Read Temperature_Zone3 attribute
#===============================================================================
    def read_Temperature_Zone3(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone3()"
        
        self.getTemperatureAttr(3, attr)
   
#===============================================================================
# Read Temperature_Zone4 attribute
#===============================================================================
    def read_Temperature_Zone4(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone4()"
        
        self.getTemperatureAttr(4, attr)
   
#===============================================================================
# Read Temperature_Zone5 attribute
#===============================================================================
    def read_Temperature_Zone5(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone5()"
        
        self.getTemperatureAttr(5, attr)
   
#===============================================================================
# Read Temperature_Zone6 attribute
#===============================================================================
    def read_Temperature_Zone6(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone6()"
        
        self.getTemperatureAttr(6, attr)
   
#===============================================================================
# Read Temperature_Zone7 attribute
#===============================================================================
    def read_Temperature_Zone7(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone7()"
        
        self.getTemperatureAttr(7, attr)
   
#===============================================================================
# Read Temperature_Zone8 attribute
#===============================================================================
    def read_Temperature_Zone8(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Zone8()"
        
        self.getTemperatureAttr(8, attr)
        
#===============================================================================
# 
# BakeoutControlDS command methods
#
#===============================================================================
#===============================================================================
# Reset command:
# 
# Description: Returns to initial state, forgets last alarm.
#===============================================================================
    def Reset(self):
        print "In " + self.get_name() + ".Reset()"

        self.set_state(PyTango.DevState.ON)

#===============================================================================
# GetPressure command:
# 
# Description: Reads the pressure value from the specified attribute.
#===============================================================================
    def GetPressure(self):
        print "In " + self.get_name() + ".GetPressure()"
        
        value = self.pressureAttr.read().value
        if ( value > self.PressureSetPoint ):
            self._q.put((0, COMMAND.get("STOP")))
            self.set_state(PyTango.DevState.DISABLE)
        
        return value

#===============================================================================
# SendCommand command:
# 
# Description: Communicates to the controller to update State and Status attributes.
#===============================================================================
    def SendCommand(self, command):
        print "In " + self.get_name() + ".SendCommand()"
        
        if ( self.ControllerType.lower() == "eurotherm" ):
            reply = str(self.modbus.ReadHoldingRegisters([int(command[0]), int(command[1])])[0])
            print "\tRecv MODBUS: %s" % reply
        elif ( self.ControllerType.lower() == "elotech" ):
            if ( len(command) < 4 ):
                raise "NotEnoughArguments"
            elif ( len(command) > 5 ):
                raise "TooManyArguments"
            else:
                package = []
                for i in range(len(command)):
                    if ( i < 2 ):
                        command[i] = ["%02x" % int(command[i])]
                    elif ( i < 4 ):
                        command[i] = [command[i]]
                    elif ( i == 4 ):
                        command[i] = self.elotech_value(command[i])
                    package.extend(command[i])            
                package.append(self.elotech_checksum(package))
                scmd = "\n" + "".join(package) + "\r"
                print "\tSend block: %s" % scmd.strip()
                
                replies = 2
                while ( replies > 0 ):
                    self._serial.write(scmd)
                    ans = self.listen()
                    if ( not ans ):
                        replies -= 1
                    elif ( ans[7:9] in ELOTECH_ERROR.keys() ): 
                        print "\tRecv block: %s" % ans.strip()                        
                        print "\t" + ELOTECH_ERROR.get(ans[7:9])
                        ans = ""
                        break
                    else:
                        print "\tRecv block: %s" % ans.strip()
                        print "\tAck: Command executed"
                        break
                    Event().wait(.1)
                reply = str(ans)
        else:
            raise "UnknownController: %s" % self.ControllerType 
        
        return reply

#===============================================================================
# Start command:
#===============================================================================
    def Start(self, zone):
        print "In " + self.get_name() + ".Start()"

        if ( self._programs.get(zone) == NO_PROGRAM ):
            print "\tErr: No program to run"        
        elif ( not self._c.isAlive(zone) ):
            self._pTimes[zone] = time.time()
            self._pTemps[zone] = self.getTemperatureAttr(zone)
            self._q.put((zone, COMMAND.get("START")))
        else:
            print "\tErr: Program running (stop first)"

#===============================================================================
# Stop command:
#===============================================================================
    def Stop(self, zone):
        print "In " + self.get_name() + ".Stop()"
        
        if ( self._c.isAlive(zone) ):
            for zn in (zone and [zone] or range(1, self._noZones + 1)):        
                self._pTemps[zn] = self._pTimes[zn] = 0.
            self._q.put((zone, COMMAND.get("STOP")))
        else:
            if ( zone ):
                print "\tErr: Program stopped (start first)"
            else:
                print "\tErr: All programs stopped (start first)"            

#===============================================================================
# Getters and setters
#===============================================================================
    def zoneCount(self):
        return self._noZones or 1
 
    def getProgram(self, zone):
        return self._programs.get(zone)
            
#===============================================================================
# BakeoutControlDS other methods
#===============================================================================
    def init_serial(self):
        if ( hasattr(self, "serial") and self._serial ): 
            self.close()
        self._serial = serial.Serial()
        self._serial.baudrate = 9600
        self._serial.bytesize = 7
        self._serial.parity = "E"
        self._serial.stopbits = 1
        self._serial.timeout = 0
        self._serial.port = self.CommsDevice
        self._serial.xonxoff = 0
        self._serial.rtscts = 0
         
    def listen(self):
        s = self._serial.readline()
        if ( not s ):
            ts = 5 
            while ( not s and ts ):
                Event().wait(.1)
                s = self._serial.readline()
                ts -= 1
        s += self._serial.readline()
        
        return s

    def checksum(self, x, y):
        res = 256 - x - y - 32
        while ( res <= 0 ): res += 256
        
        return str(hex(res)).upper()[2:]
        
    def elotech_checksum(self, args):
        res = 256 - sum([int(i, 16) for i in args])
        while ( res <= 0 ): res += 256
        
        return "%02x".upper() % res
     
    def elotech_value(self, value):
        v = Decimal(str(value))
        v = v.as_tuple()
        mantissa = "%04x".upper() % int(("-" if v[0] else "") + "".join(map(str, v[1])))
        exponent = "%02x".upper() % int(self.int2bin(v[2]), 2)        
        
        return mantissa[:2], mantissa[-2:], exponent    
  
    def int2bin(self, n, count=8):
        return "".join([str((n >> y) & 1) for y in range(count -1, -1, -1)])
       
    def update_properties(self, property_list = []):
        property_list = property_list or self.get_device_class().device_property_list.keys()
        if ( not hasattr(self, "db") or not self.db ): self.db = PyTango.Database()
        props = dict([(key, getattr(self, key)) for key in property_list if hasattr(self, key)])
        
        for key, value in props.items():
            print "\tUpdating property %s = %s" % (key, value)
            self.db.put_device_property(self.get_name(), {key:isinstance(value, list) and value or [value]})
        
#===============================================================================
# 
# BakeoutControlDSClass class definition
#
#===============================================================================
class BakeoutControlDSClass(PyTango.PyDeviceClass):
# Class Properties
    class_property_list = {
        }

# Device Properties
    device_property_list = {
        "ControllerType":
            [PyTango.DevString, 
            "Eurotherm or Elotech. \nDepending of the chosen type the communication will use a Modbus protocol or a serial protocol.\nBehaviour of commands for each type are different!", 
            [""] ], 
        "CommsDevice":
            [PyTango.DevString, 
            "Device Server used for communications (modbus or serial line or serial device).", 
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

# Command definitions
    cmd_list = {
        "Reset":
            [[PyTango.DevVoid, "Returns to initial state, forgets last alarm"], 
            [PyTango.DevVoid, ""]], 
        "GetPressure":
            [[PyTango.DevVoid, ""], 
            [PyTango.DevDouble, ""]], 
        "SendCommand":
            [[PyTango.DevVarStringArray, "Issue an instruction to the controller"], 
            [PyTango.DevString, ""]],
        "Start":
            [[PyTango.DevShort, ""],
             [PyTango.DevVoid, ""]],
        "Stop":
            [[PyTango.DevShort, ""],
             [PyTango.DevVoid, ""]]             
        }

# Attribute definitions
    attr_list = {                                                                                      
        "Pressure":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Pressure_SetPoint":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Program_Zone1":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]], 
        "Program_Zone2":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]], 
        "Program_Zone3":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]], 
        "Program_Zone4":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]], 
        "Program_Zone5":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]], 
        "Program_Zone6":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]], 
        "Program_Zone7":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]], 
        "Program_Zone8":
            [[PyTango.DevDouble, 
            PyTango.IMAGE, 
            PyTango.READ_WRITE, 3 , 64]],
       "Program_Temp_Zone1":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Program_Temp_Zone2":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Temp_Zone3":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Temp_Zone4":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Temp_Zone5":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],             
        "Program_Temp_Zone6":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Temp_Zone7":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Temp_Zone8":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],                 
        "Program_Time_Zone1":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Program_Time_Zone2":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Time_Zone3":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Time_Zone4":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Time_Zone5":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],             
        "Program_Time_Zone6":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Time_Zone7":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Program_Time_Zone8":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],            
        "Temperature_All":
            [[PyTango.DevDouble, 
            PyTango.SPECTRUM, 
            PyTango.READ, 256]],         
        "Temperature_Max":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Temperature_SetPoint":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Temperature_Zone1":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],
        "Temperature_Zone2":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_Zone3":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_Zone4":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_Zone5":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]],             
        "Temperature_Zone6":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_Zone7":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]], 
        "Temperature_Zone8":
            [[PyTango.DevDouble, 
            PyTango.SCALAR, 
            PyTango.READ]]           
        }

#===============================================================================
# BakeoutControlDSClass Constructor
#===============================================================================
    def __init__(self, name):
        PyTango.PyDeviceClass.__init__(self, name)
        self.set_type(name);
        print "In BakeoutControlDSClass constructor"

#===============================================================================
# 
# BakeoutControlDS class main method
#
#===============================================================================
if __name__ == "__main__":
    try:
        py = PyTango.PyUtil(sys.argv)
        py.add_TgClass(BakeoutControlDSClass, BakeoutControlDS, "BakeoutControlDS")

        U = PyTango.Util.instance()
        U.server_init()
        U.server_run()

    except PyTango.DevFailed, e:
        print "Received a DevFailed exception:", e
    except Exception, e:
        print "An unforeseen exception occured....", e
