TEMP_ERROR = 1200.
NO_PROGRAM = [TEMP_ERROR, 0., 0., 0.]
ELOTECH_ISTR = {"SEND": "10",
                "SEND_GROUP": "15", 
                "ACPT": "20", 
                "ACPT+SAVE": "21"}
ELOTECH_PARAM = {"TEMP": "10",
                 "SETPOINT": "21",
                 "RISE": "2F",
                 "FALL": "2F",
                 "STATUS": "70",
                 "ZONE_ON_OFF": "8F"}
ELOTECH_ERROR = {"01": "Err: Parity error",
                 "02": "Err: Checksum error",
                 "03": "Err: Procedure error",
                 "04": "Err: Non-compliance with specified range error",
                 "05": "Err: Zone number not allowed/available error",
                 "06": "Err: Parameter read-only error",
                 "FE": "Err: Writing into powerfail storage error",
                 "FF": "Err: General Error"}
