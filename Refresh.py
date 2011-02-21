import sys
import time
import threading
from PyQt4 import QtCore




class Refresh(threading.Thread, QtCore.QObject):

        
    
    def __init__(self, ch):
	global change
        threading.Thread.__init__(self)
	change = ch

    def run(self):
	global change
        while 1:
	    time.sleep(5)
	    change.emit(QtCore.SIGNAL("Refresh()"))
	    
    def set_delay(self, temp):
        self.delay = temp
 
