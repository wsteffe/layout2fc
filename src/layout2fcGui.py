import layout2fc,FreeCADGui
from PyQt5.QtWidgets import QWidget, QFileDialog
import os

 
# CHANGE THE LINE BELOW
path_to_ui = "/home/walter/MwCAD/EmCAD/layout2fc/src/layout2fc.ui"
 
class ImportLayoutDialog:
   def __init__(self):
       # this will create a Qt widget from our ui file
       self.form = FreeCADGui.PySideUic.loadUi(path_to_ui)

   def dxfFileBrowseClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","DXF Files (*.dxf)", options=options)
        if fileName:
            self.form.dxfFileName.set(fileName)
   def stackFileBrowseClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","Stack Files (*.stack)", options=options)
        if fileName:
            self.form.stackFileName.set(fileName)
   def accept(self):
       dxfFileName = self.form.dxfFileName.value()
       stackFileName = self.form.stackFileName.value()
       if (dxfFileName == None) or (stackFileName == None) :
           print("Error! None of the values can be 0!")
           # we bail out without doing anything
           return
       layout2fc.main(stackFileName,dxfFileName)
       FreeCADGui.Control.closeDialog()
        
panel = ImportLayoutDialog()
FreeCADGui.Control.showDialog(panel)



