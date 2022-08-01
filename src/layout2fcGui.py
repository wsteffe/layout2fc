import FreeCAD, FreeCADGui
import importlib
import layout2fc as layout
import PySide
from PySide.QtGui import QWidget, QFileDialog
from os import path
 
# CHANGE THE LINE BELOW
path_to_ui = path.join(path.dirname(path.realpath(__file__)), 'layout2fc.ui')
 
class ImportLayoutDialog:
   def __init__(self):
       # this will create a Qt widget from our ui file
       self.param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/layout2fc")
       self.form = FreeCADGui.PySideUic.loadUi(path_to_ui)
       self.form.dxfFileName.setText(self.param.GetString('DxfFileName'))
       self.form.stackFileName.setText(self.param.GetString('StackFileName'))
       self.form.checkBoxRecompute.setChecked(self.param.GetBool('Recompute', True))
       self.form.checkBoxExportStep.setChecked(self.param.GetBool('ExportStep', False))
       self.form.spinBoxParallel.setValue(self.param.GetInt('Parallel', 4))
       self.form.dxfFileBrowse.clicked.connect(self.dxfFileBrowseClicked)
       self.form.stackFileBrowse.clicked.connect(self.stackFileBrowseClicked)

   def dxfFileBrowseClicked(self):
        fileName, _ = QFileDialog.getOpenFileName(FreeCADGui.getMainWindow(),"QFileDialog.getOpenFileName()", "","DXF Files (*.dxf)")
        if fileName:
            self.form.dxfFileName.setText(fileName)
   def stackFileBrowseClicked(self):
        fileName, _ = QFileDialog.getOpenFileName(FreeCADGui.getMainWindow(),"QFileDialog.getOpenFileName()", "","Stack Files (*.stack)")
        if fileName:
            self.form.stackFileName.setText(fileName)
   def accept(self):
       dxfFileName = self.form.dxfFileName.text()
       stackFileName = self.form.stackFileName.text()
       recompute = self.form.checkBoxRecompute.isChecked()
       parallel = self.form.spinBoxParallel.value()
       export = self.form.checkBoxExportStep.isChecked()
       self.param.SetString('DxfFileName', dxfFileName)
       self.param.SetString('StackFileName', stackFileName)
       self.param.SetBool('Recompute', recompute)
       self.param.SetBool('ExportStep', export)
       self.param.SetInt('Parallel', parallel)
       if (dxfFileName == None) or (stackFileName == None) :
           print("Error! None of the values can be 0!")
           # we bail out without doing anything
           return
       importlib.reload(layout)
       layout.main(stackFileName,dxfFileName,export_step=export,
                   recompute=recompute, parallel=parallel)
       #  FreeCADGui.Control.closeDialog()

def run():
    panel = ImportLayoutDialog()
    FreeCADGui.Control.showDialog(panel)

run()

