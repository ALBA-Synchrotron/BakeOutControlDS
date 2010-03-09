import PyTango
import serial
import sys
import time
from BakeoutControl import COMMAND, BakeoutController
from BakeoutEnumeration import *
from decimal import Decimal
from threading import Event, Lock

class BakeoutControlDS(PyTango.Device_3Impl):
    def __init__(self, cl, name):
        PyTango.Device_3Impl.__init__(self, cl, name)
        BakeoutControlDS.init_device(self)
        
    #---------------------------------------------------------------- __init__()

    def delete_device(self):
#        print "[Device delete_device method] for device", self.get_name()
        if ( self.ControllerType.lower() == "elotech" and self._serial ):
            print "delete_device(): Closing elotech serial line...",
            self._serial.close()
            print "done"
            
    #----------------------------------------------------------- delete_device()

    def init_device(self):
#        print "In " + self.get_name() + ".init_device()"
        self.set_state(PyTango.DevState.ON)
        self.get_device_properties(self.get_device_class())
        self.update_properties()
        self._sndCmdLock = Lock()
        self._noZones = 1
        self._outputs = self._oLimits = self._programs = self._pParams = self._pZones = self._temps = None
        self._pressure = self._tempMax = 0.
        self._pressureTime = self._tempTime = long(0)
        
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
                self._outputs = dict.fromkeys((i for i in range(1, self._noZones + 1)), 0)
                self._oLimits = dict.fromkeys((i for i in range(1, self._noZones + 1)), 100)
                self._programs = dict.fromkeys((i for i in range(1, self._noZones + 1)), PROGRAM_DEFAULT)
                self._pParams = dict((i, list(PARAMS_DEFAULT)) for i in range(1, self._noZones + 1))
                self._pZones = dict.fromkeys((i for i in range(1, self._noZones + 1)), list())
                self._temps = dict.fromkeys((i for i in range(1, self._noZones + 1)), TEMP_DEFAULT)
                self._c = BakeoutController(self)
                self._q = self._c.getQueue()
                self._c.setDaemon(True)
                self._c.start()
                self._q.put((0, COMMAND.get("STOP")))                
            else:
                raise RuntimeError("UnknownController: %s" % self.ControllerType)
        except Exception, e:
            PyTango.Except.throw_exception("BakeoutControlDS_initDeviceException", str(e), str(e))
            self.modbus = self._serial = None
        
        print "\tDevice server " + self.get_name() + " awaiting requests..."
        
    #------------------------------------------------------------- init_device()

    def always_executed_hook(self):
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                self.modbus.ping()  
        except:
            self.set_state(PyTango.DevState.FAULT)
            
    #---------------------------------------------------- always_executed_hook()

    def read_attr_hardware(self, data):
#        print "In " + self.get_name() + ".read_attr_hardware()"
        pass
        
    #------------------------------------------------------ read_attr_hardware()

    def read_Output_1(self, attr):
        self.getOutputAttr(1, attr)
        
    #----------------------------------------------------------- read_Output_1()

    def read_Output_2(self, attr):
        self.getOutputAttr(2, attr)
        
    #----------------------------------------------------------- read_Output_2()

    def read_Output_3(self, attr):
        self.getOutputAttr(3, attr)
        
    #----------------------------------------------------------- read_Output_3()

    def read_Output_4(self, attr):
        self.getOutputAttr(4, attr)
        
    #----------------------------------------------------------- read_Output_4()

    def read_Output_5(self, attr):
        self.getOutputAttr(5, attr)
        
    #----------------------------------------------------------- read_Output_5()

    def read_Output_6(self, attr):
        self.getOutputAttr(6, attr)
        
    #----------------------------------------------------------- read_Output_6()

    def read_Output_7(self, attr):
        self.getOutputAttr(7, attr)
        
    #----------------------------------------------------------- read_Output_7()

    def read_Output_8(self, attr):
        self.getOutputAttr(8, attr)
        
    #----------------------------------------------------------- read_Output_8()

    def read_Output_1_Limit(self, attr):
        self.getLimitAttr(1, attr)
        
    #----------------------------------------------------- read_Output_1_Limit()

    def write_Output_1_Limit(self, attr):
        self.setLimitAttr(1, attr)
        
    #---------------------------------------------------- write_Output_1_Limit()

    def read_Output_2_Limit(self, attr):
        self.getLimitAttr(2, attr)
        
    #----------------------------------------------------- read_Output_2_Limit()

    def write_Output_2_Limit(self, attr):
        self.setLimitAttr(2, attr)
        
    #---------------------------------------------------- write_Output_2_Limit()

    def read_Output_3_Limit(self, attr):
        self.getLimitAttr(3, attr)
        
    #----------------------------------------------------- read_Output_3_Limit()

    def write_Output_3_Limit(self, attr):
        self.setLimitAttr(3, attr)
        
    #---------------------------------------------------- write_Output_3_Limit()

    def read_Output_4_Limit(self, attr):
        self.getLimitAttr(4, attr)
        
    #----------------------------------------------------- read_Output_4_Limit()

    def write_Output_4_Limit(self, attr):
        self.setLimitAttr(4, attr)
        
    #---------------------------------------------------- write_Output_4_Limit()

    def read_Output_5_Limit(self, attr):
        self.getLimitAttr(5, attr)
        
    #----------------------------------------------------- read_Output_5_Limit()

    def write_Output_5_Limit(self, attr):
        self.setLimitAttr(5, attr)
        
    #---------------------------------------------------- write_Output_5_Limit()

    def read_Output_6_Limit(self, attr):
        self.getLimitAttr(6, attr)
        
    #----------------------------------------------------- read_Output_6_Limit()

    def write_Output_6_Limit(self, attr):
        self.setLimitAttr(6, attr)
        
    #---------------------------------------------------- write_Output_6_Limit()

    def read_Output_7_Limit(self, attr):
        self.getLimitAttr(7, attr)
        
    #----------------------------------------------------- read_Output_7_Limit()

    def write_Output_7_Limit(self, attr):
        self.setLimitAttr(7, attr)
        
    #---------------------------------------------------- write_Output_7_Limit()

    def read_Output_8_Limit(self, attr):
        self.getLimitAttr(8, attr)
        
    #----------------------------------------------------- read_Output_8_Limit()

    def write_Output_8_Limit(self, attr):
        self.setLimitAttr(8, attr)
        
    #---------------------------------------------------- write_Output_8_Limit()

    def read_Pressure(self, attr):
#        print "In " + self.get_name() + ".read_Pressure()"
        if ( not self.pressureAttr ):
            raise RuntimeError("WrongPressureAttribute: %s" % (hasattr(self, "PressureAttribute") and str(self.PressureAttribute) or ""))
        
        self._pressureTime = long(time.time())
        self._pressure = self.GetPressure()
        attr.set_value(self._pressure)
        
    #----------------------------------------------------------- read_Pressure()

    def read_Pressure_SetPoint(self, attr):
#        print "In " + self.get_name() + ".read_Pressure_SetPoint()"
        data = self.PressureSetPoint
        attr.set_value(data)

    #-------------------------------------------------- read_Pressure_SetPoint()

    def write_Pressure_SetPoint(self, attr):
#        print "In " + self.get_name() + ".write_Pressure_SetPoint()"
        data = []
        attr.get_write_value(data)
        self.PressureSetPoint = float(data[0])
        self.update_properties()
        
    #------------------------------------------------- write_Pressure_SetPoint()
        
    def read_Program_1(self, attr):
#        print "In " + self.get_name() + ".read_Program_1()"
        self.getProgramAttr(1, attr)
        
    #------------------------------------------------------------ read_Program_1
  
    def write_Program_1(self, attr):
#        print "In " + self.get_name() + ".write_Program_1()"
        self.setProgramAttr(1, attr)
        
    #--------------------------------------------------------- write_Program_1()
        
    def read_Program_2(self, attr):
#        print "In " + self.get_name() + ".read_Program_2()"
        self.getProgramAttr(2, attr)
        
    #---------------------------------------------------------- read_Program_2()
         
    def write_Program_2(self, attr):
#        print "In " + self.get_name() + ".write_Program_2()"
        self.setProgramAttr(2, attr)
        
    #--------------------------------------------------------- write_Program_2()
 
    def read_Program_3(self, attr):
#        print "In " + self.get_name() + ".read_Program_3()"
        self.getProgramAttr(3, attr)
        
    #---------------------------------------------------------- read_Program_3()
        
    def write_Program_3(self, attr):
#        print "In " + self.get_name() + ".write_Program_3()"
        self.setProgramAttr(3, attr)
        
    #--------------------------------------------------------- write_Program_3()
 
    def read_Program_4(self, attr):
#        print "In " + self.get_name() + ".read_Program_4()"
        self.getProgramAttr(4, attr)
        
    #---------------------------------------------------------- read_Program_4()
       
    def write_Program_4(self, attr):
#        print "In " + self.get_name() + ".write_Program_4()"
        self.setProgramAttr(4, attr)
        
    #--------------------------------------------------------- write_Program_4()
 
    def read_Program_5(self, attr):
#        print "In " + self.get_name() + ".read_Program_5()"
        self.getProgramAttr(5, attr)
        
    #---------------------------------------------------------- read_Program_5()
        
    def write_Program_5(self, attr):
#        print "In " + self.get_name() + ".write_Program_5()"
        self.setProgramAttr(5, attr)
        
    #--------------------------------------------------------- write_Program_5()
  
    def read_Program_6(self, attr):
#        print "In " + self.get_name() + ".read_Program_6()"
        self.getProgramAttr(6, attr)
        
    #---------------------------------------------------------- read_Program_6()
        
    def write_Program_6(self, attr):
#        print "In " + self.get_name() + ".write_Program_6()"
        self.setProgramAttr(6, attr)
        
    #--------------------------------------------------------- write_Program_6()
 
    def read_Program_7(self, attr):
#        print "In " + self.get_name() + ".read_Program_7()"
        self.getProgramAttr(7, attr)
        
    #---------------------------------------------------------- read_Program_7()
        
    def write_Program_7(self, attr):
#        print "In " + self.get_name() + ".write_Program_7()"
        self.setProgramAttr(7, attr)
        
    #--------------------------------------------------------- write_Program_7()
 
    def read_Program_8(self, attr):
#        print "In " + self.get_name() + ".read_Program_8()"
        self.getProgramAttr(8, attr)
        
    #---------------------------------------------------------- read_Program_8()

    def write_Program_8(self, attr):
#        print "In " + self.get_name() + ".write_Program_8()"
        self.setProgramAttr(8, attr)
        
    #--------------------------------------------------------- write_Program_8()
      
    def read_Program_1_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_1_Params()"
        self.getParamsAttr(1, attr)
        
    #--------------------------------------------------- read_Program_1_Params()
       
    def read_Program_2_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_2_Params()"
        self.getParamsAttr(2, attr)

    #--------------------------------------------------- read_Program_2_Params()

    def read_Program_3_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_3_Params()"
        self.getParamsAttr(3, attr)

    #--------------------------------------------------- read_Program_3_Params()

    def read_Program_4_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_4_Params()"
        self.getParamsAttr(4, attr)

    #--------------------------------------------------- read_Program_4_Params()
       
    def read_Program_5_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_5_Params()"
        self.getParamsAttr(5, attr)

    #--------------------------------------------------- read_Program_5_Params()
 
    def read_Program_6_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_6_Params()"
        self.getParamsAttr(6, attr)

    #--------------------------------------------------- read_Program_6_Params()

    def read_Program_7_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_7_Params()"
        self.getParamsAttr(7, attr)
        
    #--------------------------------------------------- read_Program_7_Params()
        
    def read_Program_8_Params(self, attr):
#        print "In " + self.get_name() + ".read_Program_8_Params()"
        self.getParamsAttr(8, attr)
        
    #--------------------------------------------------- read_Program_8_Params()
       
    def read_Program_1_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_1_Zones()"
        self.getZonesAttr(1, attr)
        
    #---------------------------------------------------- read_Program_1_Zones()
        
    def write_Program_1_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_1_Zones()"
        self.setZonesAttr(1, attr)
        
    #--------------------------------------------------- write_Program_1_Zones()
        
    def read_Program_2_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_2_Zones()"
        self.getZonesAttr(2, attr)
        
    #---------------------------------------------------- read_Program_2_Zones()
        
    def write_Program_2_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_2_Zones()"
        self.setZonesAttr(2, attr)
        
    #--------------------------------------------------- write_Program_2_Zones()
 
    def read_Program_3_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_3_Zones()"
        self.getZonesAttr(3, attr)
        
    #---------------------------------------------------- read_Program_3_Zones()
        
    def write_Program_3_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_3_Zones()"
        self.setZonesAttr(3, attr)
        
    #--------------------------------------------------- write_Program_3_Zones()
 
    def read_Program_4_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_4_Zones()"
        self.getZonesAttr(4, attr)
         
    #---------------------------------------------------- read_Program_4_Zones()
        
    def write_Program_4_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_4_Zones()"
        self.setZonesAttr(4, attr)
        
    #--------------------------------------------------- write_Program_4_Zones()
       
    def read_Program_5_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_5_Zones()"
        self.getZonesAttr(5, attr)
         
    #---------------------------------------------------- read_Program_5_Zones()
    
    def write_Program_5_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_5_Zones()"
        self.setZonesAttr(5, attr)
        
    #--------------------------------------------------- write_Program_5_Zones()
 
    def read_Program_6_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_6_Zones()"
        self.getZonesAttr(6, attr)
        
    #---------------------------------------------------- read_Program_6_Zones()
        
    def write_Program_6_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_6_Zones()"
        self.setZonesAttr(6, attr)
        
    #--------------------------------------------------- write_Program_6_Zones()
 
    def read_Program_7_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_7_Zones()"
        self.getZonesAttr(7, attr)
        
    #---------------------------------------------------- read_Program_7_Zones()
          
    def write_Program_7_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_7_Zones()"
        self.setZonesAttr(7, attr)
       
    #--------------------------------------------------- write_Program_7_Zones()
       
    def read_Program_8_Zones(self, attr):
#        print "In " + self.get_name() + ".read_Program_8_Zones()"
        self.getZonesAttr(8, attr)
        
    #---------------------------------------------------- read_Program_8_Zones()
          
    def write_Program_8_Zones(self, attr):
#        print "In " + self.get_name() + ".write_Program_8_Zones()"
        self.setZonesAttr(8, attr)
        
    #--------------------------------------------------- write_Program_8_Zones()
 
    def read_Temperature_1(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_1()"
        self.getTemperatureAttr(1, attr)
        
    #------------------------------------------------------ read_Temperature_1()
 
    def read_Temperature_2(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_2()"
        self.getTemperatureAttr(2, attr)
        
    #------------------------------------------------------ read_Temperature_2()
   
    def read_Temperature_3(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_3()"
        self.getTemperatureAttr(3, attr)
        
    #------------------------------------------------------ read_Temperature_3()
   
    def read_Temperature_4(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_4()"
        self.getTemperatureAttr(4, attr)
        
    #------------------------------------------------------ read_Temperature_4()
   
    def read_Temperature_5(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_5()"
        self.getTemperatureAttr(5, attr)
        
    #------------------------------------------------------ read_Temperature_5()
   
    def read_Temperature_6(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_6()"
        self.getTemperatureAttr(6, attr)
        
    #------------------------------------------------------ read_Temperature_6()
   
    def read_Temperature_7(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_7()"
        self.getTemperatureAttr(7, attr)
        
    #------------------------------------------------------ read_Temperature_7()
   
    def read_Temperature_8(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_8()"
        self.getTemperatureAttr(8, attr)
        
    #------------------------------------------------------ read_Temperature_8()
  
    def read_Temperature_All(self, attr=None):
#        print "In " + self.get_name() + ".read_Temperature_All()"
        self._tempTime = long(time.time())
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

        for key, value in enumerate(data):
            self.setTemperature(key, value)
        
        if ( attr is not None ):
            attr.set_value(data, len(data))
        
        return data
    
    #---------------------------------------------------- read_Temperature_All()

    def read_Temperature_Max(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_Max()"
        if ( self.ControllerType.lower() == "eurotherm" ):
            self._tempMax = self.read_Temperature_All()
        elif ( self.ControllerType.lower() == "elotech" ):
            if ( self._tempTime < long(time.time()) - 60 ):
                ans = self.read_Temperature_All()
            else:
                ans = self._temps.values()
            self._tempMax = max([value for value in ans if value != TEMP_DEFAULt])
        else:
            raise "UnknownController: %s" % self.ControllerType            
        attr.set_value(self._tempMax)
        
    #---------------------------------------------------- read_Temperature_Max()

    def read_Temperature_SetPoint(self, attr):
#        print "In " + self.get_name() + ".read_Temperature_SetPoint()"
        data = self.TemperatureSetPoint
        attr.set_value(data)
        
    #----------------------------------------------- read_Temperature_SetPoint()

    def write_Temperature_SetPoint(self, attr):
#        print "In " + self.get_name() + ".write_Temperature_SetPoint()"
        data = []
        attr.get_write_value(data)
        self.TemperatureSetPoint = float(data[0])
        self.update_properties()
        
    #---------------------------------------------- write_Temperature_SetPoint()

    def getLimitAttr(self, zone, attr):
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = ELOTECH_ISTR.get("SEND")
            code = ELOTECH_PARAM.get("OUTPUT_LIMIT")
        else:
            raise RuntimeError("UnknownController: %s" % self.ControllerType)
        
        ans = self.SendCommand([device, zone, instruction, code])
        if ( ans ):
            data = int(ans[9:13], 16)
        else:
            data = 100
        
        self.setLimit(zone, data)
        attr.set_value(data)
        
    #------------------------------------------------------------ getLimitAttr()

    def setLimitAttr(self, zone, attr):
        data = []
        attr.get_write_value(data)
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = ELOTECH_ISTR.get("ACPT")
            code = ELOTECH_PARAM.get("OUTPUT_LIMIT")
            value = data[0]
        else:
            raise RuntimeError("UnknownController: %s" % self.ControllerType)
        self.SendCommand([device, zone, instruction, code, value])
        
        self.setLimit(zone, value)
        
    #------------------------------------------------------------ setLimitAttr()
        
    def getLimit(self, key):
        return self._oLimits.get(key)
    
    #---------------------------------------------------------------- getLimit()
      
    def setLimit(self, key, value):
        self._oLimits[key] = value
    
    #---------------------------------------------------------------- setLimit()
  
    def getOutputAttr(self, zone, attr):
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = ELOTECH_ISTR.get("SEND")
            code = ELOTECH_PARAM.get("OUTPUT")
        else:
            raise RuntimeError("UnknownController: %s" % self.ControllerType)
        
        ans = self.SendCommand([device, zone, instruction, code])
        if ( ans ):
            data = int(ans[9:13], 16)
        else:
            data = 0
        
        self.setOutput(zone, data)
        
        if ( attr ):
            attr.set_value(data)
        
        return data
        
    #----------------------------------------------------------- getOutputAttr()
      
    def getOutput(self, key):
        return self._outputs.get(key)
    
    #--------------------------------------------------------------- getOutput()
      
    def setOutput(self, key, value):
        self._outputs[key] = value
    
    #--------------------------------------------------------------- setOutput()
        
    def getParamsAttr(self, programNo, attr):
#        print "In " + self.get_name() + ".getParamsAttr()"
        data = self.getParams(programNo)
        attr.set_value(data)
        
    #----------------------------------------------------------- getParamsAttr()
 
    def getParams(self, key):
        return self._pParams.get(key)
                
    #--------------------------------------------------------------- getParams()
    
    def setParams(self, key, value):
        self._pParams[key] = value
        
    #--------------------------------------------------------------- setParams()
 
    def getProgramAttr(self, programNo, attr):
#        print "In " + self.get_name() + ".getProgramAttr()"
        data = self.getProgram(programNo)        
        dim_x = 3
        dim_y = len(data) / 3    
        attr.set_value(data, dim_x, dim_y)
        
    #---------------------------------------------------------- getProgramAttr()

    def setProgramAttr(self, programNo, attr):
#        print "In " + self.get_name() + ".setProgramAttr()"
        data = []
        attr.get_write_value(data)
        if ( len(data) == 0 or len(data) % 3 != 0 ):
            raise ValueError
        self.setProgram(programNo, data)
        self.setParams(programNo, list(PARAMS_DEFAULT))
        
    #---------------------------------------------------------- setProgramAttr()
 
    def getProgram(self, key):
        return self._programs.get(key)
    
    #-------------------------------------------------------------- getProgram()
   
    def setProgram(self, key, value):
        self._programs[key] = value
    
    #-------------------------------------------------------------- setProgram()    
      
    def getTemperatureAttr(self, zone, attr=None):
#        print "In " + self.get_name() + ".getTemperatureAttr()"
        if ( self.ControllerType.lower() == "eurotherm" ):
            raise NotImplementedError        
        elif ( self.ControllerType.lower() == "elotech" ):
            device = 1
            instruction = ELOTECH_ISTR.get("SEND")
            code = ELOTECH_PARAM.get("TEMP")
        else:
            raise RuntimeError("UnknownController: %s" % self.ControllerType)
        
        ans = self.SendCommand([device, zone, instruction, code])
        if ( ans ):
            data = float(int(ans[9:13], 16)*10**int(ans[13:15], 16))
        else:
            data = TEMP_DEFAULT
        
        self.setTemperature(zone, data)
        
        if ( attr ):
            attr.set_value(data)
        
        return data
    
    #------------------------------------------------------ getTemperatureAttr()

    def getTemperature(self, key):
        return self._temps.get(key)
    
    #---------------------------------------------------------- getTemperature()

    def setTemperature(self, key, value):
        self._temps[key] = value
        
    #---------------------------------------------------------- setTemperature()
       
    def getZonesAttr(self, programNo, attr):
#        print "In " + self.get_name() + ".getZonesAttr()"
        data = self.getZones(programNo)        
        attr.set_value(data)
    
    #------------------------------------------------------------ getZonesAttr()

    def setZonesAttr(self, programNo, attr):
#        print "In " + self.get_name() + ".setZonesAttr()"
        data = []
        attr.get_write_value(data)
        dataSet = set(data)
        dataSet.intersection_update(i for i in range(1, self._noZones))
        for otherSet in [self.getZones(pNo) for pNo in range(1, self._noZones) if pNo != programNo]:
            if ( dataSet.intersection(otherSet) ):
                dataSet.difference_update(otherSet)
        self.setZones(programNo, sorted(dataSet))
        
    #------------------------------------------------------------ setZonesAttr()
       
    def getZones(self, key):
        return self._pZones.get(key)
    
    #---------------------------------------------------------------- getZones()

    def setZones(self, key, value):
        self._pZones[key] = value
    
    #---------------------------------------------------------------- setZones()
      
    def zoneCount(self):
        return self._noZones
    
    #--------------------------------------------------------------- zoneCount()
       
    def Reset(self):
        print "In " + self.get_name() + ".Reset()"

        self.set_state(PyTango.DevState.ON)
        
    #------------------------------------------------------------------- Reset()

    def GetPressure(self):
        print "In " + self.get_name() + ".GetPressure()"
        
        value = self.pressureAttr.read().value
        if ( value > self.PressureSetPoint ):
            self._q.put((0, COMMAND.get("STOP")))
            self.set_state(PyTango.DevState.DISABLE)
        
        return value
    
    #------------------------------------------------------------- GetPressure()

    def SendCommand(self, command):
        print "In " + self.get_name() + ".SendCommand()"
        
        self._sndCmdLock.acquire()
        try:
            if ( self.ControllerType.lower() == "eurotherm" ):
                reply = str(self.modbus.ReadHoldingRegisters([int(command[0]), int(command[1])])[0])
                print "\tRecv MODBUS: %s" % reply
            elif ( self.ControllerType.lower() == "elotech" ):
                if ( len(command) < 4 ):
                    raise ValueError
                elif ( len(command) > 5 ):
                    raise ValueError
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
                raise RuntimeError("UnknownController: %s" % self.ControllerType) 
            
            return reply
        finally:
            self._sndCmdLock.release()
            
    #------------------------------------------------------------- SendCommand()

    def Start(self, programNo):
        print "In " + self.get_name() + ".Start()"

        if ( not self._c.isAlive(programNo) ):
            self._q.put((programNo, COMMAND.get("START")))
        else:
            print "\tErr: Program running (stop it first)"
            
    #------------------------------------------------------------------- Start()

    def Stop(self, zone):
        print "In " + self.get_name() + ".Stop()"
        
        if ( self._c.isAlive(zone) ):
            self._q.put((zone, COMMAND.get("STOP")))
        else:
            if ( zone ):
                print "\tErr: Program stopped (start it first)"
            else:
                print "\tErr: All programs stopped (start one first)"
                
    #-------------------------------------------------------------------- Stop()
     
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
        
    #------------------------------------------------------------- init_serial()
         
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
    
    #------------------------------------------------------------------ listen()

    def checksum(self, x, y):
        res = 256 - x - y - 32
        while ( res <= 0 ): res += 256
        
        return str(hex(res)).upper()[2:]
    
    #---------------------------------------------------------------- checksum()
        
    def elotech_checksum(self, args):
        res = 256 - sum([int(i, 16) for i in args])
        while ( res <= 0 ): res += 256
        
        return "%02x".upper() % res
    
    #-------------------------------------------------------- elotech_checksum()
     
    def elotech_value(self, value):
        v = Decimal(str(value))
        v = v.as_tuple()
        mantissa = "%04x".upper() % int(("-" if v[0] else "") + "".join(map(str, v[1])))
        exponent = "%02x".upper() % int(self.int2bin(v[2]), 2)        
        
        return mantissa[:2], mantissa[-2:], exponent 
    
    #----------------------------------------------------------- elotech_value()
   
    def update_properties(self, property_list = []):
        property_list = property_list or self.get_device_class().device_property_list.keys()
        if ( not hasattr(self, "db") or not self.db ): self.db = PyTango.Database()
        props = dict([(key, getattr(self, key)) for key in property_list if hasattr(self, key)])
        
        for key, value in props.items():
            print "\tUpdating property %s = %s" % (key, value)
            self.db.put_device_property(self.get_name(), {key:isinstance(value, list) and value or [value]})
            
    #------------------------------------------------------- update_properties()
  
    def int2bin(self, n, count=8):
        return "".join([str((n >> y) & 1) for y in range(count - 1, -1, -1)])
    
    #----------------------------------------------------------------- int2bin()

#------------------------------------------------------------ BakeoutControlDS()
              
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
            PyTango.READ_WRITE]],
        "Output_2_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Output_3_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Output_4_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Output_5_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Output_6_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Output_7_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],
        "Output_8_Limit":
            [[PyTango.DevShort, 
            PyTango.SCALAR, 
            PyTango.READ_WRITE]],                                                                                                                                                                                         
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
