layout2fc.py is a python script to generate a 3D structure from a 2D layout plus stack informations.

Usage:
   layout2fc.py [-step] file1.stack  file.dxf

Output: 
-a FreeCAD document: file.FCStd
-if option "-step" is given also: file.step

Requirewments:
 klayout and FreeCAD must be installed.
 klayout and FreeCAD python modules must be accessible trough a proper setting of python search path.
 
# layout2fc
