import sys
import PyTango
import tau.core
import os
import time
from PyQt4 import QtCore, QtGui, Qwt5 as Qwt
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from guibuilder import Ui_MainWindow
from PyTango_utils.excepts import *
from Refresh import *

class gui(QtGui.QMainWindow):	
	
	def __init__(self, parent=None):
		try:
			# Build the GUI
			QtGui.QMainWindow.__init__(self, parent)
			self.ui  = Ui_MainWindow()
			self.ui.setupUi(self)
			self.file = "log.txt"
			self.filewrite = 0
			# Connect to the Device and manage data
			self.connect(self.ui.avrate_y1, QtCore.SIGNAL("stateChanged(int)"), self.avrateplot)
			self.connect(self.ui.avrate_y2, QtCore.SIGNAL("stateChanged(int)"), self.avrateplot)
			self.connect(self.ui.avthickness_y1, QtCore.SIGNAL("stateChanged(int)"), self.avthicknessplot)
			self.connect(self.ui.avthickness_y2, QtCore.SIGNAL("stateChanged(int)"), self.avthicknessplot)
			self.connect(self.ui.rate1_y1, QtCore.SIGNAL("stateChanged(int)"), self.rate1plot)
			self.connect(self.ui.rate1_y2, QtCore.SIGNAL("stateChanged(int)"), self.rate1plot)
			self.connect(self.ui.rate2_y1, QtCore.SIGNAL("stateChanged(int)"), self.rate2plot)
			self.connect(self.ui.rate2_y2, QtCore.SIGNAL("stateChanged(int)"), self.rate2plot)
			self.connect(self.ui.thickness1_y1, QtCore.SIGNAL("stateChanged(int)"), self.thickness1plot)
			self.connect(self.ui.thickness1_y2, QtCore.SIGNAL("stateChanged(int)"), self.thickness1plot)
			self.connect(self.ui.thickness2_y1, QtCore.SIGNAL("stateChanged(int)"), self.thickness2plot)
			self.connect(self.ui.thickness2_y2, QtCore.SIGNAL("stateChanged(int)"), self.thickness2plot)
			self.connect(self.ui.frequency1_y1, QtCore.SIGNAL("stateChanged(int)"), self.frequency1plot)
			self.connect(self.ui.frequency1_y2, QtCore.SIGNAL("stateChanged(int)"), self.frequency1plot)
			self.connect(self.ui.frequency2_y1, QtCore.SIGNAL("stateChanged(int)"), self.frequency2plot)
			self.connect(self.ui.frequency2_y2, QtCore.SIGNAL("stateChanged(int)"), self.frequency2plot)
			
			self.connect(self.ui.pirani1_y1, QtCore.SIGNAL("stateChanged(int)"), self.pirani1plot)
			self.connect(self.ui.pirani1_y2, QtCore.SIGNAL("stateChanged(int)"), self.pirani1plot)
			self.connect(self.ui.pirani2_y1, QtCore.SIGNAL("stateChanged(int)"), self.pirani2plot)
			self.connect(self.ui.pirani2_y2, QtCore.SIGNAL("stateChanged(int)"), self.pirani2plot)			
			self.connect(self.ui.penning1_y1, QtCore.SIGNAL("stateChanged(int)"), self.penning1plot)
			self.connect(self.ui.penning1_y2, QtCore.SIGNAL("stateChanged(int)"), self.penning1plot)
			self.connect(self.ui.penning2_y1, QtCore.SIGNAL("stateChanged(int)"), self.penning2plot)
			self.connect(self.ui.penning2_y2, QtCore.SIGNAL("stateChanged(int)"), self.penning2plot)			
			
			
			#Common part
			self.connect(self.ui.avrate_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.avrateplot_2)
			self.connect(self.ui.avrate_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.avrateplot_2)
			self.connect(self.ui.avthickness_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.avthicknessplot_2)
			self.connect(self.ui.avthickness_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.avthicknessplot_2)
			self.connect(self.ui.rate1_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.rate1plot_2)
			self.connect(self.ui.rate1_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.rate1plot_2)
			self.connect(self.ui.rate2_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.rate2plot_2)
			self.connect(self.ui.rate2_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.rate2plot_2)
			self.connect(self.ui.thickness1_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.thickness1plot_2)
			self.connect(self.ui.thickness1_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.thickness1plot_2)
			self.connect(self.ui.thickness2_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.thickness2plot_2)
			self.connect(self.ui.thickness2_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.thickness2plot_2)
			self.connect(self.ui.frequency1_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.frequency1plot_2)
			self.connect(self.ui.frequency1_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.frequency1plot_2)
			self.connect(self.ui.frequency2_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.frequency2plot_2)
			self.connect(self.ui.frequency2_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.frequency2plot_2)
			
			self.connect(self.ui.pirani1_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.pirani1plot_2)
			self.connect(self.ui.pirani1_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.pirani1plot_2)
			self.connect(self.ui.pirani2_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.pirani2plot_2)
			self.connect(self.ui.pirani2_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.pirani2plot_2)			
			self.connect(self.ui.penning1_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.penning1plot_2)
			self.connect(self.ui.penning1_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.penning1plot_2)
			self.connect(self.ui.penning2_y1_2, QtCore.SIGNAL("stateChanged(int)"), self.penning2plot_2)
			self.connect(self.ui.penning2_y2_2, QtCore.SIGNAL("stateChanged(int)"), self.penning2plot_2)			
			
			self.connect(self.ui.startbutton1, QtCore.SIGNAL("clicked()"), self.startlogging)
			self.connect(self.ui.startbutton2, QtCore.SIGNAL("clicked()"), self.startlogging)
			self.connect(self.ui.startbutton3, QtCore.SIGNAL("clicked()"), self.startlogging)
			self.connect(self.ui.startbutton4, QtCore.SIGNAL("clicked()"), self.startlogging)
			self.connect(self.ui.startbutton5, QtCore.SIGNAL("clicked()"), self.startlogging)

			self.connect(self.ui.stopbutton1, QtCore.SIGNAL("clicked()"), self.stoplogging)
			self.connect(self.ui.stopbutton2, QtCore.SIGNAL("clicked()"), self.stoplogging)
			self.connect(self.ui.stopbutton3, QtCore.SIGNAL("clicked()"), self.stoplogging)
			self.connect(self.ui.stopbutton4, QtCore.SIGNAL("clicked()"), self.stoplogging)
			self.connect(self.ui.stopbutton5, QtCore.SIGNAL("clicked()"), self.stoplogging)

			self.connect(self.ui.saveasbutton1, QtCore.SIGNAL("clicked()"), self.saveas)
			self.connect(self.ui.saveasbutton2, QtCore.SIGNAL("clicked()"), self.saveas)
			self.connect(self.ui.saveasbutton3, QtCore.SIGNAL("clicked()"), self.saveas)
			self.connect(self.ui.saveasbutton4, QtCore.SIGNAL("clicked()"), self.saveas)
			self.connect(self.ui.saveasbutton5, QtCore.SIGNAL("clicked()"), self.saveas)
			
			#This is used for refreshing of the values inside the main window of the GUI
			self.ui.Counter.setVisible(False)  
			ref = Refresh(self.ui.Counter)
			ref.setDaemon(True)
			ref.start()
			QtCore.QObject.connect(self.ui.Counter, QtCore.SIGNAL("Refresh()"), self.refresh)	
			
		except Exception,e:
			print e

			
			
	def refresh(self):
		if self.filewrite == 1:
			f = open(self.file,"a")
			str = "\n\n" + time.ctime() + " - Logging Started \n"
			f.write(str)
			str = "Av. thickness \t Av.rate \t Thickness1 \t Thickness2 \t Rate1 \t Rate2 \t Frequency1 \t Frequency2 \t Penning1 \t Penning2 \t Pirani1 \t Pirani2 \t \n "# Capacitor1 \t Capacitor2 \t SetPoint \t ForwardPower \t ReflectedPower \t LoadPower \t \n"
			f.write(str)
			f.close()
			self.filewrite =2
		if self.filewrite == 2:	
			f = open(self.file,"a")
			str = self.ui.avthicknessbox.text() + '\t\t\t '
			str += self.ui.avratebox.text() + '\t\t '
			str += self.ui.thickness1box.text() + '\t\t\t '
			str += self.ui.thickness2box.text() + '\t\t\t '
			str += self.ui.rate1box.text() + '\t '
			str += self.ui.rate2box.text() + '\t '
			str += self.ui.frequency1box.text() + '\t\t\t '
			str += self.ui.frequency2box.text() + '\t\t\t '
			str += self.ui.pirani1box.text() + '\t '
			str += self.ui.pirani2box.text() + '\t\t '
			str += self.ui.penning1box.text() + '\t '
			str += self.ui.penning2box.text() + '\t \n'
			f.write(str)
			f.close()


			
	def startlogging(self):
		self.filewrite = 1
		self.ui.startbutton1.setEnabled(False)
		self.ui.startbutton2.setEnabled(False)
		self.ui.startbutton3.setEnabled(False)
		self.ui.startbutton4.setEnabled(False)
		self.ui.startbutton5.setEnabled(False)
		self.ui.stopbutton1.setEnabled(True)
		self.ui.stopbutton2.setEnabled(True)
		self.ui.stopbutton3.setEnabled(True)
		self.ui.stopbutton4.setEnabled(True)
		self.ui.stopbutton5.setEnabled(True)	

			
	def stoplogging(self):
		self.filewrite = 0
		f = open(self.file,"a")
		str = time.ctime() + " - Logging Stopped \n"
		f.write(str)		
		self.ui.startbutton1.setEnabled(True)
		self.ui.startbutton2.setEnabled(True)
		self.ui.startbutton3.setEnabled(True)
		self.ui.startbutton4.setEnabled(True)
		self.ui.startbutton5.setEnabled(True)
		self.ui.stopbutton1.setEnabled(False)
		self.ui.stopbutton2.setEnabled(False)
		self.ui.stopbutton3.setEnabled(False)
		self.ui.stopbutton4.setEnabled(False)
		self.ui.stopbutton5.setEnabled(False)


	def saveas(self):
		fg = QtGui.QFileDialog()
		self.file=fg.getSaveFileName()
		self.ui.file1.setText(QtGui.QApplication.translate("MainWindow", self.file, None, QtGui.QApplication.UnicodeUTF8))
		self.ui.file2.setText(QtGui.QApplication.translate("MainWindow", self.file, None, QtGui.QApplication.UnicodeUTF8))
		self.ui.file3.setText(QtGui.QApplication.translate("MainWindow", self.file, None, QtGui.QApplication.UnicodeUTF8))
		self.ui.file4.setText(QtGui.QApplication.translate("MainWindow", self.file, None, QtGui.QApplication.UnicodeUTF8))
		self.ui.file5.setText(QtGui.QApplication.translate("MainWindow", self.file, None, QtGui.QApplication.UnicodeUTF8))

	def avrateplot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/AverageRate"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend.removeModels([model])			
			
	def avthicknessplot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/AverageThickness"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend.removeModels([model])			
			
	def rate1plot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Rate1"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend.removeModels([model])
			
	def rate2plot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Rate2"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)

		else :
			self.ui.RateTrend.removeModels([model])

	def thickness1plot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Thickness1"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)

		else :
			self.ui.RateTrend.removeModels([model])			

	def thickness2plot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Thickness2"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)

		else :
			self.ui.RateTrend.removeModels([model])			

	def frequency1plot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Frequency1"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)

		else :
			self.ui.RateTrend.removeModels([model])			

	def frequency2plot(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Frequency2"
		if  i:
			self.ui.RateTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.RateTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				#self.ui.RateTrend.setCurvesYAxis([model],Qwt.QwtPlot.yRight)
				self.ui.RateTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)

		else :
			self.ui.RateTrend.removeModels([model])			

	def pirani1plot(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P1"
		if  i:
			self.ui.GaugeTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.GaugeTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				self.ui.GaugeTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.GaugeTrend.removeModels([model])
			
	def pirani2plot(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P2"
		if  i:
			self.ui.GaugeTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.GaugeTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				self.ui.GaugeTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.GaugeTrend.removeModels([model])

	def penning1plot(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P4"
		if  i:
			self.ui.GaugeTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.GaugeTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				self.ui.GaugeTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.GaugeTrend.removeModels([model])
			
	def penning2plot(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P5"
		if  i:
			self.ui.GaugeTrend.addModels([model])
			#print ">>>>>>>>>", self.ui.RateTrend.getCurveNames()
			ts=self.ui.GaugeTrend.getTrendSet(model)
			ts.fireEvent(None,None,None)
			#print "<<<<<<<<<", self.ui.RateTrend.getCurveNames()
			if str(s.objectName())[-1] == "2":
				self.ui.GaugeTrend.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.GaugeTrend.removeModels([model])
	
	def avrateplot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/AverageRate"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])			
			
	def avthicknessplot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/AverageThickness"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])			
			
	def rate1plot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Rate1"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])
			
	def rate2plot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Rate2"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])

	def thickness1plot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Thickness1"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])			

	def thickness2plot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Thickness2"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])			

	def frequency1plot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Frequency1"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])			

	def frequency2plot_2(self,i):
		s = self.sender()
		model = "lab15/vc/ratethickness/Frequency2"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])			

	def pirani1plot_2(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P1"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])
			
	def pirani2plot_2(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P2"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])

	def penning1plot_2(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P4"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])
			
	def penning2plot_2(self,i):
		s = self.sender()
		model = "lab/15/vgct-01/P5"
		if  i:
			self.ui.RateTrend_4.addModels([model])
			ts=self.ui.RateTrend_4.getTrendSet(model)
			ts.fireEvent(None,None,None)
			if str(s.objectName())[-3] == "2":
				self.ui.RateTrend_4.setCurvesYAxis(ts.getCurveNames(),Qwt.QwtPlot.yRight)
		else :
			self.ui.RateTrend_4.removeModels([model])

if __name__ == "__main__":
	import os
	print os.getenv('TANGO_HOST')
	app = QtGui.QApplication(sys.argv)
	Work = gui()
	Work.show()
	sys.exit(app.exec_())