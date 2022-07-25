layout2fc.py is a python script to generate a 3D structure from a 2D layout plus stack informations.

Usage:
   layout2fc.py [-step] file1.stack  file.dxf

Output: 
1) a FreeCAD document: file.FCStd
2) if option "-step" is given also: file.step

Requirewments:
 klayout and FreeCAD must be installed.
 klayout and FreeCAD python modules must be accessible trough a proper setting of python search path.


Stack File Format:
Composed of two kinds of lines
1) Scale assignment
>scale: val

In example the line
>scale: 0.001
can be used to convert micron length unit used in the stackup definition to mm length unit used in FreeCAD.

2) Assignement of layer stackup data
layerNum/datatype: hmin hmax  operation insertOrder   #Comment 
operation is based on sketch stored in related layer.
operation can be: 
2.1) add: makes a solid extrusion from hmin to hmax
2.2) ins: same extrusion as add plus a cut in all previous extrusions intersecting with it. Previuos is defined by insertionOrder (integer)  
2.3) cut: same cut as for ins but without adding any solid extriusion
2.4) vsurf: makes a surface extrusion from hmin to hmax. Sketch profile may be not closed.
2.5) hsurf: generates an horizontal surface on plane z=hmin by filling the (closed) sketch profile.

In example the lines:
>scale: 0.001
>1/0:  0.0 70.0  add  0   # DIELECTRIC
>2/0:  0.0 70.0  ins  1   # FILLED THROUGH HOLE

will defined a dielectric layer based on sketch stored on layer 1 with a thickness of 70 micron
and will then insert extrusions going from h=0 to h=70 micron based on sketch stored on layer 2
For being insertion order of layer 2 greater than insertion order of layer 1 the related ins operation 
will cut the solid created by layer 1.
 

# layout2fc
