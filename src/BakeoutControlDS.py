import PyTango
import sys, traceback
import time
from threading import Event
import serial
import decimal
from BakeoutControl import COMMAND, BakeoutController
from BakeoutEnumeration import *

#==================================================================
#   BakeoutControlDS Class Description:
#
#         This device can be used to do a simple control of a Bake Out process.<br/>
#         <p>
#         The ControllerType property tells the kind of temperature controller to use, 
#         CommsDevice specifies the device to be used for communications.
#         From this controller we will read the Temperature and TemperatureSetPoint 
#         attributes, but it will not be modified by the device server.
#         </p><p>
#         Using the PressureAttribute property a pressure value will be read from other
#         Tango Device and showed as Pressure attribute. If the value readed exceeds the
#         PressureSetPoint value (either attribute or property); then a command (Reset or Standby) 
#         will be executed to stop the Temperature Controller device. <br>
#         This interlock action will be performed in the GetPressure command.
#         </p>
#
#==================================================================
#     Device States Description:
#
#   DevState.OFF :
#   DevState.DISABLE :
#   DevState.FAULT :
#   DevState.ALARM :
#   DevState.ON :
#==================================================================

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

        if ( self.ControllerType.lower() == "elotech" and self.serial ):
            print "delete_device(): Closing elotech serial line...",
            self.serial.close()
            print "done"

#===============================================================================
# Device initialization
#===============================================================================
    def init_device(self):
        print "In " + self.get_name() + ".init_device()"
        self.set_state(PyTango.DevState.ON)
        self.get_device_properties(self.get_device_class())
        self.update_properties()
        self._pressure_value = self._temp_max = None
        self._pressure_time = self._temp_time = 0
        self._temperatures = dict.fromkeys((i for i in range(1, 9)), 0)
        
        try: 
            self.pressure_attr = PyTango.AttributeProxy(self.PressureAttribute)
        except Exception, e: 
            self.pressure_attr = None
            print "Unable to create AttributeProxy for %s: %s" % (self.PressureAttribute, str(e))
            print traceback.format_exc()
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                print "\tUsing an eurotherm controller..."
                self.modbus = PyTango.DeviceProxy(self.CommsDevice)
                self.modbus.ping()
            elif ( self.ControllerType.lower() == "elotech" ):
                print "\tUsing an elotech controller..."
                self.init_serial()
                self.serial.open()
                self._numberOfZones = 8
                self._programs = dict.fromkeys((i for i in range(1, self._numberOfZones + 1)), NO_PROGRAM)
                self._programs_time = dict.fromkeys((i for i in range(1, self._numberOfZones + 1)), 0.)
                self._c = BakeoutController(self)
                self._c.setDaemon(True)
                self._q = self._c.getQueue()
                self._c.start()
            else:
                raise "UnknownController: %s" % self.ControllerType
        except Exception, e:
            PyTango.Except.throw_exception("BakeoutControlDS_initDeviceException", str(e), str(e))
            self.modbus = self.serial = None
        
        print "\tDevice server " + self.get_name() + " awaiting requests..."

#===============================================================================
# Always excuted hook method
#===============================================================================
    def always_executed_hook(self):
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                self.modbus.ping()  
        except:
            print traceback.format_exc()
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
        pass
    
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
        
        data = self._programs_time.get(zone)        
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
        else: data = None
        
        if ( attr is not None ):
            attr.set_value(data)
        
        return data

#===============================================================================
# Read Pressure attribute
#===============================================================================
    def read_Pressure(self, attr):
        print "In " + self.get_name() + ".read_Pressure()"

        if ( not self.pressure_attr ):
            raise "WrongPressureAttribute(%s)" % (hasattr(self, "PressureAttribute") and str(self.PressureAttribute) or "")
        
        self._pressure_value = self.GetPressure()
        self._pressure_time = time.time()
        attr.set_value(self._pressure_value)

#===============================================================================
# Read Pressure_SetPoint attribute
#===============================================================================
    def read_Pressure_SetPoint(self, attr):
        print "In " + self.get_name() + ".read_Pressure_SetPoint()"

        attr_Pressure_SetPoint_read = self.PressureSetPoint
        attr.set_value(attr_Pressure_SetPoint_read)

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
        
        if ( self.ControllerType.lower() == "eurotherm" ):
            attr_Temperature_All_read = float(self.modbus.ReadHoldingRegisters([1, 1])[0])
            print "Recv MODBUS: %s" % attr_Temperature_All_read
        elif ( self.ControllerType.lower() == "elotech" ):
            attr_Temperature_All_read = []                        
            for zone in range(1, self._numberOfZones + 1):
                result = self.getTemperatureAttr(zone)
                attr_Temperature_All_read.append(result)
        else:
            raise "UnknownController: %s" % self.ControllerType

        self._temp_time = time.time()
        for i, value in enumerate(attr_Temperature_All_read):
            self._temperatures[i] = value
        
        if ( attr is not None ):
            attr.set_value(attr_Temperature_All_read, len(attr_Temperature_All_read))
        
        return attr_Temperature_All_read

#===============================================================================
# Read Temperature_Max attribute
#===============================================================================
    def read_Temperature_Max(self, attr):
        print "In " + self.get_name() + ".read_Temperature_Max()"
                
        if ( self.ControllerType.lower() == "eurotherm" ):
            self._temp_max = self.read_Temperature_All()
        elif ( self.ControllerType.lower() == "elotech" ):
            if ( self._temp_time < time.time() - 60 ):
                ans = self.read_Temperature_All()
            else:
                ans = self._temperatures.values()
            self._temp_max = max([value for value in ans if value != 1200.0])
        else:
            raise "UnknownController: %s" % self.ControllerType            
        attr.set_value(self._temp_max)

#===============================================================================
# Read Temperature_SetPoint attribute
#===============================================================================
    def read_Temperature_SetPoint(self, attr):
        print "In " + self.get_name() + ".read_Temperature_SetPoint()"
        
        attr_Temperature_SetPoint_read = self.TemperatureSetPoint
        attr.set_value(attr_Temperature_SetPoint_read)

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
        
        value = self.pressure_attr.read().value
        if ( value > self.PressureSetPoint ):
            self.Stop()
            self.set_state(PyTango.DevState.DISABLE)
        
        return value

#===============================================================================
# SendCommand command:
# 
# Description: Communicates to the controller to update State and Status attributes.
#===============================================================================
    def SendCommand(self, argin):
        print "In " + self.get_name() + ".SendCommand()"
        
        if ( self.ControllerType.lower() == "eurotherm" ):
            argout = str(self.modbus.ReadHoldingRegisters([int(argin[0]), int(argin[1])])[0])
            print "\tRecv MODBUS: %s" % argout
        elif ( self.ControllerType.lower() == "elotech" ):
            if ( len(argin) < 4 ):
                raise "NotEnoughArguments"
            elif ( len(argin) > 5 ):
                raise "TooManyArguments"
            else:
                package = []
                for i in range(len(argin)):
                    if ( i < 2 ):
                        argin[i] = ["%02x" % int(argin[i])]
                    elif ( i < 4 ):
                        argin[i] = [argin[i]]
                    elif ( i == 4 ):
                        argin[i] = self.elotech_value(argin[i])
                    package.extend(argin[i])            
                package.append(self.elotech_checksum(package))
                command = "\n" + "".join(package) + "\r"
                print "\tSend block: %s" % command.strip()
                
                replies = 2
                while ( replies > 0 ):
                    self.serial.write(command)
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
                    Event().wait(0.1)
                argout = str(ans)
        else:
            raise "UnknownController: %s" % self.ControllerType 
        
        return argout

#===============================================================================
# StartStop command:
#===============================================================================
    def StartStop(self, zone):
        print "In " + self.get_name() + ".StartStop()"
        
        self._q.put((zone, COMMAND.get("START_STOP")))
        if ( self._programs_time.get(zone)):
            self._programs_time[zone] = 0.
        else:
            self._programs_time[zone] = time.time()

#===============================================================================
# BakeoutControlDS other methods
#===============================================================================
    def init_serial(self):
        if ( hasattr(self, "serial") and self.serial ): 
            self.close()
        self.serial = serial.Serial()
        self.serial.baudrate = 9600
        self.serial.bytesize = 7
        self.serial.parity = "E"
        self.serial.stopbits = 1
        self.serial.timeout = 0
        self.serial.port = self.CommsDevice
        self.serial.xonxoff = 0
        self.serial.rtscts = 0
         
    def listen(self):
        s = self.serial.readline()
        if ( not s ):
            ts = 5 
            while ( not s and ts ):
                Event().wait(0.1)
                s = self.serial.readline()
                ts -= 1
        s += self.serial.readline()
        
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
        v = decimal.Decimal(str(value))
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
            
    def getProgram(self, zone):
        return self._programs.get(zone)
    
    def getNumberOfZones(self):
        return self._numberOfZones or 1
         
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
        "StartStop":
            [[PyTango.DevUShort, ""],
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
