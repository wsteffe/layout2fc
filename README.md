
# layout2fc

layout2fc.py is a python script to generate a 3D structure from a 2D layout plus stack informations.

Usage:
   layout2fc.py [-step] file1.stack  file.dxf

Output:

  - A FreeCAD document file.FCStd
  - If option "-step" is set it produces also file.step

Requirements:

  - klayout and FreeCAD must be installed.
  - klayout and FreeCAD python modules must be accessible trough a proper setting of python search path.


Stack File Format:
Composed of two kinds of lines
* Scale assignment
><pre> scale: val</pre>

In example the line
><pre> scale: 0.001</pre>

can be used to convert micron length unit used in the stackup definition to mm length unit used in FreeCAD.

- Assignement of stackup data

><pre> layerNum/datatype: hmin hmax  operation insertOrder   #Comment</pre>

  operation is based on sketch stored in related layer. Operation can be:

  - add: makes a solid extrusion from hmin to hmax
  - ins: same extrusion as add plus a cut in all previous extrusions intersecting with it. Previuos is defined by insertOrder (integer)  
  - cut: same cut as for ins but without adding any solid extrusion
  - vsurf: makes a surface extrusion from hmin to hmax. Sketch profile may be not closed.
  - hsurf: generates an horizontal surface on plane z=hmin by filling the (closed) sketch profile.

In example the lines:

><pre> scale: 0.001</pre>

><pre> 1/0:  0.0 70.0  add  0   # DIELECTRIC</pre>

><pre> 2/0:  0.0 70.0  ins  1   # FILLED THROUGH HOLE</pre>

Define a dielectric layer based on sketch stored on layer 1 with a thickness of 70 micron
and then insert an extrusion from h=0 to h=70 micron based on sketch stored on layer 2.
For being insertion order of layer 2 greater than insertion order of layer 1 the related extrusion 
will cut the solid created by layer 1.
 
