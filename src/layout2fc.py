#!/usr/bin/python3

import sys, os, time, platform
import klayout.db as db

import FreeCAD, FreeCADGui
import Import, Part

from operator import itemgetter
from collections import defaultdict
import subprocess as sp
from threading import Event
from concurrent.futures import ThreadPoolExecutor

import pdb
#pdb.set_trace()

logger = FreeCAD.Logger('layout2fc')

def new_document(path):
    doc = FreeCAD.newDocument()
    doc.saveAs(path+'.FCStd')
    if hasattr(Part, 'disableElementMapping'):
        Part.disableElementMapping(doc)
    doc.UndoMode = 0
    return doc

def create_doc(layout_fname, tech_fname):
    layout_fname1,fext=os.path.splitext(layout_fname)
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
    layout.read(layout_fname)
    for ci in layout.each_top_cell():
        c=layout.cell(ci)
        c.flatten(-1,True)

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


    mainDoc = doc = new_document(layout_fname1)

    partName = os.path.basename(layout_fname1)
    if not partName.startswith('CMP_'):
        partName='CMP_'+partName

    paramPath = "User parameter:BaseApp/Preferences/Mod/layout2fc"
    params = FreeCAD.ParamGet(paramPath)
    params.SetBool('groupLayers', True)
    params.SetBool('connectEdges', False)

    Import.readDXF(layout_fname, option_source=paramPath)
    layers = doc.Objects
    for layer in layers:
        layer.Visibility = False

    part=doc.addObject("App::Part", partName)

    def useObject(container, obj, export=True, prefix=None):
        if not export:
            obj.Visibility = False
        if obj.Document == container.Document:
            parent = obj.getParentGeoFeatureGroup()
            if not parent or parent == container:
                if hasattr(obj, 'Group_EnableExport'):
                    obj.Group_EnableExport = export
                return obj
        link = container.Document.addObject('App::Link', 'Link')
        link.LinkedObject = obj
        container.addObject(link)
        if prefix is not None:
            link.Label = f'{prefix}_{obj.Label}'
        if hasattr(link, 'Group_EnableExport'):
            link.Group_EnableExport = export
        return link

    def addPad(body, wires, h, solid = True, prefix='Pad', export=True):
        parent = wires.getParentGeoFeatureGroup()
        if not parent:
            parent = body
            body.addObject(wires)
            wires.Group_EnableExport = False

        label = f'{prefix}_{h}_{parent.Label}'
        objs = body.Document.getObjectsByLabel(label)
        if objs and objs[0].LengthFwd == h \
                and objs[0].Solid == solid \
                and objs[0].getParentGeoFeatureGroup() == parent:
            return useObject(body, objs[0], export)

        link = None
        if wires.isDerivedFrom('App::Link') and wires.ElementCount > 1:
            link = wires
            wires = wires.LinkedObject

        pad=parent.Document.addObject('Part::Extrusion', 'Extrude')
        pad.Base=wires
        pad.Solid=solid
        pad.LengthFwd = h
        pad.Dir = (0, 0, 1)
        parent.addObject(pad)
        pad.Visibility =True
        if parent != body:
            pad.Group_EnableExport = False

        if not link:
            pad.Label = label
        else:
            pad.Label = f'Single_{label}'
            pad.Visibility = False
            padlink = parent.Document.addObject('App::Link', 'Link')
            padlink.LinkedObject = pad
            padlink.ShowElement = False
            padlink.ElementCount = link.ElementCount
            padlink.PlacementList = link.PlacementList
            parent.addObject(padlink)
            padlink.Group_EnableExport = pad.Group_EnableExport
            padlink.Visibility = False
            padlink.Label = label
            pad = padlink

        return useObject(body, pad, export)

    def addPocket(body, wires, h, prefix='Pocket'):
        objs = body.Document.getObjectsByLabel('Wires_' + body.Label)
        if not objs:
            raise RuntimeError('Wires not found for body ' + body.Label)
        base = objs[0]
        tool = useObject(body, wires, False)
        faces = body.Document.addObject('Path::FeatureArea','Area')
        faces.WorkPlane = workplane
        faces.Label = f'Faces_{body.Label}'
        faces.Operation = 'Difference'
        faces.Fill = 'Face'
        faces.Sources = [base, tool]
        body.addObject(faces)
        base.Visibility = False
        tool.Visibility = False
        faces.Visibility =False
        base.Group_EnableExport = False
        tool.Group_EnableExport = False
        faces.Group_EnableExport = False
        pocket = addPad(body, faces, h, prefix='Pocket')
        pocket.Visibility = True
        for obj in body.Group:
            if obj.Label.startswith('Pad_'):
                body.Document.removeObject(obj.Name)

    def addVSurf(body, wires, h):
        return addPad(body, wires, h, solid=False, prefix='Shell')

    def addHSurf(body, wires):
        return useObject(body, wires, export=True, prefix='Sheet')

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

    body_names={}
    workplane = Part.makeCircle(10)

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

        layer = [ o for o in layers if o.Name.endswith(linfoi.name) ]
        if not layer:
            logger.warn('layout {} not found', linfoi.name)
            continue
        # assuming only one layer match the name
        layer = layer[0]

        label = linfoi.name

        doc = new_document(layout_fname1 + '_' + label)
        layer = doc.moveObject(layer)

        body=doc.addObject("App::Part", label)
        body_names[ldatai]=body
        pl=FreeCAD.Placement()
        pl.move(FreeCAD.Vector(0,0,z0i*stack_scale))
        body.Placement = pl
        body.Visibility = True
        body.ExportMode = 'Child Query'
        body.addObject(layer)
        layer.Group_EnableExport = False
        layer.Visibility = False

        useObject(part, body, prefix='').Visibility = True

        hole_map = defaultdict(list)
        edges = []
        for edge in layer.Shape.Edges:
            if edge.isClosed() and isinstance(edge.Curve, Part.Circle):
                radius = round(edge.Curve.Radius, 3)
                hole_map[radius].append(edge)
            else:
                edge.Tag = -1
                edges.append(edge)

        if not hole_map:
            if len(layer.Shape.Wires) > 1 or layer.Shape.Wire1.findPlane():
                wires = doc.addObject('Path::FeatureArea','Area')
                wires.Outline = True
                wires.WorkPlane = workplane
                wires.Sources = layer
                wires.Label="Wires_"+label
                wires.Visibility = False
            else:
                wires = layer
            body.addObject(wires)
            wires.Group_EnableExport = False
        else:
            objs = []
            for r, holes in hole_map.items():
                hole = doc.addObject('Part::Feature', 'Hole')
                hole.Label = f'Hole_{r}_{label}'
                hole.Shape = Part.Face(Part.makeCircle(r))
                hole.Visibility = False
                if len(holes) == 1:
                    hole.Placement = FreeCAD.Placement(holes[0].Curve.Center, FreeCAD.Rotation())
                else:
                    link = doc.addObject('App::Link', 'Holes')
                    link.Label = f'Holes_{r}_{label}'
                    link.Visibility = False
                    link.LinkedObject = hole
                    link.ShowElement = False
                    link.ElementCount = len(holes)
                    if hasattr(link, 'LinkClaimChildren'):
                        link.LinkClaimChildren = True
                    plalist = []
                    for h in holes:
                        plalist.append(FreeCAD.Placement(h.Curve.Center, FreeCAD.Rotation()))
                    link.PlacementList = plalist;
                    hole = link
                objs.append(hole)

            if edges:
                wires = doc.addObject('App::Feature', 'Wires')
                wires.Label = 'Wires_' + label
                wires.Shape = Part.Compound(edges)
                wires.Visibility = False
                body.addObject(wires)
                wires.Group_EnableExport = False
                area = doc.addObject('Path::FeatureArea','Area')
                area.Outline = True
                area.WorkPlane = workplane
                area.Label = 'Area_' + label
                area.Sources = wires
                area.Visibility = False
                objs.append(area)

            if len(objs) == 1:
                wires = objs[0]
            else:
                body.addObject(objs)
                for o in objs:
                    o.Group_EnableExport = False
                wires = doc.addObject('Part::Compound2', 'Compound')
                wires.Links = objs
                wires.Label="Wires_"+label
            body.addObject(wires)
            wires.Group_EnableExport = False

        if opi=='add':
          obj=addPad(body, wires,(z1i-z0i)*stack_scale)
        elif opi=='vsurf':
          obj=addVSurf(body, wires,(z1i-z0i)*stack_scale)
        elif opi=='hsurf':
          obj=addHSurf(body, wires)
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
                 bodyj=body_names[ldataj]
                 pocket=addPocket(bodyj,wires,(z1j-z0j)*stack_scale)

    for doc in mainDoc.getDependentDocuments():
        doc.save();
    return mainDoc

def run_process(event, cmd):
    proc = sp.Popen([sys.executable, '-c'],
                    stdin=sp.PIPE,
                    stderr=sp.PIPE,
                    stdout=sp.PIPE,
                    text=True)

    try:
        while True:
            try:
                if cmd:
                    stdout, stderr = proc.communicate(input=cmd, timeout=1)
                else:
                    stdout, stderr = proc.communicate(timeout=1)
                break
            except sp.TimeoutExpired as e:
                cmd = None
                if not event.is_set():
                    continue
                logger.error('abort process')
                proc.kill()
                stdout = e.stdout.decode('utf8')
                stderr = e.stderr.decode('utf8')
                break;
        if stdout:
            FreeCAD.Console.PrintMessage(stdout + '\n')
        if stderr:
            for line in stderr.split('\n'):
                if not line.startswith('>>>'):
                    FreeCAD.Console.PrintError(line + '\n')
    except Exception:
        import traceback
        logger.error(traceback.format_exc())

def recompute_doc(file_path, event):
    logger.msg('recomputing {}', file_path)
    run_process(event, cmd=f'''
import sys, FreeCAD

try:
    FreeCAD.silenceSequencer()
except Exception:
    pass

try:
    doc = FreeCAD.openDocument('{file_path}')
    doc.UndoMode = 0
    doc.recompute()
    doc.save()
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

sys.exit()
''')

def main(tech_fname, layout_fname,
         export_step=False, recompute=True, parallel=4):

    event = Event()
    with ThreadPoolExecutor(max(parallel,1)) as executor:

        def next(p, futures):
            nonlocal progress
            try:
                if p > progress:
                    progress += 1
                    progress_bar.next(True)
                else:
                    FreeCAD.checkAbort()
            except Exception as e:
                import traceback
                logger.error(traceback.format_exc())
                for future in futures:
                    if future:
                        try:
                            future.cancel()
                        except Exception:
                            pass
                event.set()
                for future in futures:
                    while future and future.running():
                        time.sleep(0.2)
                logger.error('User abort')
                return False
            return True

        future = executor.submit(run_process, event, cmd=f'''
import layout2fc
layout2fc.create_doc('{layout_fname}', '{tech_fname}')

''')
        try:
            progress_bar = FreeCAD.Base.ProgressIndicator()
            progress_bar.start("Creating layout", 100)
            progress = 0

            counter = 0
            while not future.done():
                time.sleep(0.1)
                counter += 1
                FreeCADGui.updateGui()
                if not next(min(95, counter/10), [future]):
                    return
        finally:
            progress_bar.stop()

        file_path,fext=os.path.splitext(layout_fname)
        mainDoc = FreeCAD.openDocument(file_path + '.FCStd')
        body_map = {}
        for obj in mainDoc.Objects:
            if obj.isDerivedFrom('App::Link'):
                body_map[obj.LinkedObject] = None

        if recompute and parallel>1:
            try:
                body_deps = {}
                for body in body_map:
                    body_deps[body] = {o for o in body.InList if o != body and o in body_map}

                progress_bar = FreeCAD.Base.ProgressIndicator()
                progress_bar.start("Recomputing", len(body_map))
                progress = 0

                body_done = set()
                while len(body_done) != len(body_map):
                    for body, future in body_map.items():
                        if future:
                            if future.done():
                                body_done.add(body)
                            continue
                        can_run = True
                        for dep in body_deps[body]:
                            future = body_map[dep]
                            if not future or not future.done():
                                can_run = False
                                break
                        if can_run:
                            body_map[body] = executor.submit(recompute_doc,
                                                            body.Document.FileName,
                                                            event)
                            break
                    time.sleep(0.1)
                    FreeCADGui.updateGui()
                    if not next(len(body_done), body_map.values()):
                        return
            finally:
                progress_bar.stop()

    if recompute:
        if parallel:
            filename = mainDoc.FileName
            FreeCAD.closeDocument(mainDoc.Name)
            for body in body_map.keys():
                FreeCAD.closeDocument(body.Document.Name)
            mainDoc = FreeCAD.openDocument(filename)
            #  mainDoc.UndoMode = 0
        #  mainDoc.recompute()
        #  mainDoc.save()

    if export_step:
        Import.export([part], layout_fname1+".step")
    mainDoc.UndoMode = 1
    FreeCAD.setActiveDocument(mainDoc.Name)
    if recompute:
        FreeCADGui.runCommand('Std_ViewFitAll')
    return mainDoc

if __name__ == '__main__':
    sys.argv
    argv=sys.argv[1:]
    tech_fname=None
    layout_fname=None
    export_step=False
    argl=len(argv)
    for i,arg in enumerate(argv):
       if arg.lower()=='-step':
          export_step=True
          argv.pop(i)
          break
    argl=len(argv)
    if argl<2:
        print("Syntax:  layout2fc  -stack stack_file  dxf_file")
        exit()
    for i in range(2):
      fname=argv[argl-1-i]
      fname1,fext=os.path.splitext(fname)
      if fext.lower()  == '.dxf':
         layout_fname=fname
      elif fext == '.stack':
         tech_fname=fname

    if layout_fname==None or tech_fname==None:
        print("Syntax:  layout2fc  -stack stack_file  dxf_file")
        exit()

    if not os.path.exists(tech_fname):
        print(tech_fname+"  not found")
        exit()

    if not os.path.exists(fname):
        print(fname+"  not found")
        exit()

    try:
        main(tech_fname, layout_fname, export_step)
    except:
        import traceback
        logger.error(traceback.format_exc())
    exit()

