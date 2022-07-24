import layout2fc,FreeCADGui
import PySide
from PySide.QtGui import QWidget, QFileDialog
from os import path
 
# CHANGE THE LINE BELOW
path_to_ui = path.join(path.dirname(path.realpath(__file__)), 'layout2fc.ui')
 
class ImportLayoutDialog:
   def __init__(self):
       # this will create a Qt widget from our ui file
       self.form = FreeCADGui.PySideUic.loadUi(path_to_ui)
       self.form.dxfFileBrowse.clicked.connect(self.dxfFileBrowseClicked)
       self.form.stackFileBrowse.clicked.connect(self.stackFileBrowseClicked)

   def dxfFileBrowseClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(FreeCADGui.getMainWindow(),"QFileDialog.getOpenFileName()", "","DXF Files (*.dxf)", options=options)
        if fileName:
            self.form.dxfFileName.setText(fileName)
   def stackFileBrowseClicked(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(FreeCADGui.getMainWindow(),"QFileDialog.getOpenFileName()", "","Stack Files (*.stack)", options=options)
        if fileName:
            self.form.stackFileName.setText(fileName)
   def accept(self):
       dxfFileName = self.form.dxfFileName.text()
       stackFileName = self.form.stackFileName.text()
       if (dxfFileName == None) or (stackFileName == None) :
           print("Error! None of the values can be 0!")
           # we bail out without doing anything
           return
       layout2fc.main(stackFileName,dxfFileName)
       FreeCADGui.Control.closeDialog()
        
panel = ImportLayoutDialog()
FreeCADGui.Control.showDialog(panel)



