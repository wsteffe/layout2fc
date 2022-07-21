#!/usr/bin/python3

import sys,os
import klayout.db as db

import FreeCAD
import Import, importDXF, Draft, Part, PartDesign, Sketcher

from operator import itemgetter

import pdb
#pdb.set_trace()

def main(tech_fname, fname):
    fname1,fext=os.path.splitext(fname)
    stack={}
    with open(tech_fname, 'r') as f:
        for line in f:
            line=line.split('#')[0]
            [ldata,zdata]=line.split(':')
            stack[ldata]=zdata.split()

    stack_scale=1
    if 'scale' in stack.keys():
        stack_scale=float(stack['scale'][0])

    layout = db.Layout()
    layout.read(fname)
    for ci in layout.each_top_cell():
        c=layout.cell(ci)
        c.flatten(-1,True)

    #pdb.set_trace()

    work_layer = layout.layer()
    for li in layout.layer_indexes():
        linfoi = layout.get_info(li)
        ldatai=str(linfoi.layer)+"/"+str(linfoi.datatype)
        if ldatai not in stack.keys():
            continue
        [z0i,z1i,opi,orderi]=stack[ldatai]
        if opi=='vsurf':
            continue
        for c in layout.each_cell():
            mergeReg = db.Region(c.begin_shapes_rec(li))
            mergeReg.merge()
            c.shapes(work_layer).insert(mergeReg)
        layout.clear_layer(li)
        layout.swap_layers(li, work_layer)


    doc = FreeCAD.newDocument()
    if fname1.startswith('CMP_'):
        partName=fname1
    else:
        partName='CMP_'+fname1

    part=doc.addObject("App::Part", partName)
    doc.recompute()
    doc.saveAs(fname1+'.FCStd')


    def addPad(sketch,h):
        pad=doc.addObject('PartDesign::Pad','Pad')
        pad.Profile=sketch
        pad.NewSolid=False
        pad.Length = h
        pad.Direction = (0, 0, 1)
        pad.ReferenceAxis = None
        pad.AlongSketchNormal = 0
        pad.Type = 0
        pad.UpToFace = None
        pad.Reversed = False
        pad.Offset = 0
        pad.Visibility =True
        return pad

    def addPocket(sketch,h):
        pocket=doc.addObject('PartDesign::Pocket','Pocket')
        pocket.Profile=sketch
        pocket.Length = h
        pocket.Reversed = True
        pocket.Visibility =True
        return pocket

    def addVSurf(sketch,h):
        compound=Part.makeCompound([])
        pdb.set_trace()
        for w in sketch.Shape.Wires:
            f=w.extrude(Base.Vector(0,0,h))
            compound.add(f)
        obj=doc.addObject('PartDesign::Feature','Compound')
        obj.Shape=compound
        obj.Visibility =True
        return obj

    def addHSurf(sketch):
        face=Part.makeFace(sketch.Shape.Wires)
        obj=doc.addObject('PartDesign::Feature','Face')
        obj.Shape=face
        obj.Visibility =True
        return obj


    layer_order_and_indexes= []
    for li in layout.layer_indexes():
        linfoi = layout.get_info(li)
        if linfoi.layer==0 or linfoi.name=="_0" or linfoi.name=="L0D0_0":
            continue
        ldatai=str(linfoi.layer)+"/"+str(linfoi.datatype)
        if ldatai not in stack.keys():
            continue
        layer_order_and_indexes.append((stack[ldatai][3],li))

    layer_order_and_indexes=sorted(layer_order_and_indexes, key=itemgetter(0))

    bodyName={}
    for i in range(len(layer_order_and_indexes)):
        li=layer_order_and_indexes[i][1]
        linfoi = layout.get_info(li)
        if linfoi.layer==0 or linfoi.name=="_0" or linfoi.name=="L0D0_0":
            continue
        ldatai=str(linfoi.layer)+"/"+str(linfoi.datatype)
        if ldatai not in stack.keys():
            continue
        [z0i,z1i,opi,orderi]=stack[ldatai]
        z0i=float(z0i)
        z1i=float(z1i)
        fname_li=fname1+"_"+linfoi.name
        opt = db.SaveLayoutOptions()
        opt.format="DXF"
        # specifies to write only layer index "li" with target layer/datatype taken 
        # from the original "linfo":
        opt.add_layer(li, linfoi)
        layout.write(fname_li+".dxf", opt)
        print(fname_li+".dxf" + " written.")
        body=doc.addObject("PartDesign::Body", linfoi.name)
        bodyName[ldatai]=body.Name
        part.addObject(body)
        pl=FreeCAD.Placement()
        pl.move(FreeCAD.Vector(0,0,z0i*stack_scale))
        body.Placement = pl
        body.Visibility = True
        #  body.ExportMode = 'Child Query'
        existings = doc.Objects
        importDXF.insert(fname_li+".dxf",doc.Name)
        os.remove(fname_li+".dxf")
        if opi=='vsurf':
            pdb.set_trace()
        newObjs = [o for o in doc.Objects if o not in existings]
        skObjs  = [o for o in newObjs if o.TypeId=='Part::Feature' or o.TypeId=='Part::PartFeature']
        sketchi=None
        if len(skObjs) >0:
            sketchi = Draft.make_sketch(skObjs, autoconstraints=True)
        for obj in newObjs:
            doc.removeObject(obj.Name)
        if sketchi==None:
            continue
        #  sketchi.Support=(doc.XY_Plane, [''])
        #  body[ldatai].addObject(sketchi)
        #  doc.recompute()
        sketchi.Label="Sketch_"+linfoi.name
        if opi=='add' or opi=='ins':
          obj=addPad(sketchi,(z1i-z0i)*stack_scale)
          obj.Label="Pad_"+sketchi.Label
        elif opi=='vsurf':
          obj=addVSurf(sketchi,(z1i-z0i)*stack_scale)
          obj.Label="Shell_"+sketchi.Label
          obj.addProperty('App::PropertyBool', 'Group_EnableExport', 'Group')
          obj.Group_EnableExport = True
        elif opi=='hsurf':
          obj=addHSurf(sketchi)
          obj.Label="Sheet_"+sketchi.Label
          obj.addProperty('App::PropertyBool', 'Group_EnableExport', 'Group')
          obj.Group_EnableExport = True
        body.addObject(obj)
        doc.recompute()
        if opi=='ins' or opi=='cut':
           for j in range(i):
              if layer_order_and_indexes[j][0]==layer_order_and_indexes[i][0]:
                 break
              lj=layer_order_and_indexes[j][1]
              linfoj = layout.get_info(lj)
              ldataj=str(linfoj.layer)+"/"+str(linfoj.datatype)
              if ldataj not in stack.keys():
                 continue
              [z0j,z1j,opj,orderj]=stack[ldataj]
              if opj=='add' or opi=='ins':
                 z0j=float(z0j)
                 z1j=float(z1j)
                 if z0i>=z1j or z0j>=z1i:
                   continue
                 pocket=addPocket(sketchi,(z1j-z0j)*stack_scale)
                 pocket.Label="Pocket_"+linfoi.name+"_"+linfoj.name
                 bodyj=doc.getObject(bodyName[ldataj])
                 bodyj.addObject(pocket)
                 doc.recompute()
    Import.export([part], fname1+".step")
    doc.save()
    return doc

if __name__ == '__main__':
    sys.argv
    argv=sys.argv[1:]
    tech_fname=None
    for i,arg in enumerate(argv):
        if arg=="-stack":
            argv.pop(i)
            tech_fname=argv.pop(i)
            tech_fname1,tech_fext=os.path.splitext(tech_fname)
            if tech_fext  != '.stack':
                print(tech_fname+' is not a stack file')
                exit()
            break

    argl=len(argv)
    if argl!=1:
        print("Syntax:  layout2fc  -stack stack_file  dxf_file")
        exit()
    fname=argv[argl-1]
    fname1,fext=os.path.splitext(fname)
    if fext.lower()  != '.dxf':
        print(argv[argl-1]+' is not a dxf file')
        exit()

    if tech_fname==None:
        print("Syntax:  layout2fc  -stack stack_file  dxf_file")

    if not os.path.exists(tech_fname):
        print(tech_fname+"  not found")
        exit()

    if not os.path.exists(fname):
        print(fname+"  not found")
        exit()

    try:
        main(tech_fname, fname)
    except:
        import traceback
        traceback.print_exc()
    exit()

