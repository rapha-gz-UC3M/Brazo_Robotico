"""Convierte los STL del montaje en un STEP AP214 con estructura de ensamblaje (un componente por pieza)."""
import sys, os, time, trimesh, numpy as np
from OCP.gp import gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.ShapeFix import ShapeFix_Solid
from OCP.TopoDS import TopoDS
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorSurf
from OCP.TDataStd import TDataStd_Name
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopLoc import TopLoc_Location
from OCP.BRepCheck import BRepCheck_Analyzer

def mesh_to_solid(path):
    m = trimesh.load(path); m.merge_vertices()
    sew = BRepBuilderAPI_Sewing(1e-3)
    V = m.vertices
    for f in m.faces:
        a, b, c = (gp_Pnt(*map(float, V[i])) for i in f)
        poly = BRepBuilderAPI_MakePolygon(a, b, c, True)
        if not poly.IsDone(): continue
        face = BRepBuilderAPI_MakeFace(poly.Wire(), True)
        if face.IsDone(): sew.Add(face.Face())
    sew.Perform()
    sewed = sew.SewedShape()
    exp = TopExp_Explorer(sewed, TopAbs_SHELL)
    ms = BRepBuilderAPI_MakeSolid()
    while exp.More():
        ms.Add(TopoDS.Shell(exp.Current()) if hasattr(TopoDS,"Shell") else TopoDS.Shell_s(exp.Current())); exp.Next()
    fix = ShapeFix_Solid(ms.Solid()); fix.Perform(); solid = fix.Solid()
    u = ShapeUpgrade_UnifySameDomain(solid, True, True, True); u.SetLinearTolerance(2e-3); u.SetAngularTolerance(np.radians(0.05)); u.Build()   # fusiona triángulos coplanarios
    from OCP.ShapeFix import ShapeFix_Shape
    fx = ShapeFix_Shape(u.Shape()); fx.Perform(); res = fx.Shape()
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.TopAbs import TopAbs_SOLID
    def good(sh):
        if not BRepCheck_Analyzer(sh).IsValid(): return False
        e = TopExp_Explorer(sh, TopAbs_SOLID); n = 0
        while e.More(): n += 1; e.Next()
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(sh, g)
        return n == 1 and abs(g.Mass() - m.volume) < 0.01*m.volume
    if not good(res):                                   # si la fusión de caras rompe algo, se usa el sólido sin fusionar
        res = solid
        assert good(res), path
    return res, len(m.faces)

def hex2rgb(h): h = h.lstrip('#'); return [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]

def main(items, out, asm_name):
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()); ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    root = st.NewShape(); TDataStd_Name.Set_s(root, TCollection_ExtendedString(asm_name))
    for path, name, color in items:
        t0 = time.time(); shp, ntri = mesh_to_solid(path)
        ok = BRepCheck_Analyzer(shp).IsValid()
        lab = st.AddShape(shp, False); TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
        r, g, b = hex2rgb(color); ct.SetColor(lab, Quantity_Color(r, g, b, Quantity_TOC_RGB), XCAFDoc_ColorSurf)
        comp = st.AddComponent(root, lab, TopLoc_Location())
        TDataStd_Name.Set_s(comp, TCollection_ExtendedString(name))
        print(f'{name:28s} {ntri:6d} triángulos  válido={ok}  {time.time()-t0:5.1f}s', flush=True)
    st.UpdateAssemblies()
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    w = STEPCAFControl_Writer(); w.SetColorMode(True); w.SetNameMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    assert w.Write(out) == IFSelect_RetDone
    print('escrito', out, os.path.getsize(out)//1024, 'KB')

if __name__ == '__main__':
    C = sys.argv[1]; out = sys.argv[2]
    items = [
        (f'{C}/REF_Brazo_Parte_2_1_Vasil.stl',  'Brazo_Parte_2_1_Vasil', '#8e96a6'),
        (f'{C}/REF_Brazo_Parte_2.2_4_Vasil.stl', 'Brazo_Parte_2.2_4_Vasil', '#72b7b2'),
        (f'{C}/ASM_acople_punta_vasil.stl',     'Acople_punta_vasil_x1.5',   '#b279a2'),
        (f'{C}/ASM_contraplaca_acople.stl',     'Contraplaca_acople_x1.5',   '#eeca3b'),
        (f'{C}/ASM_casquillo_punta.stl',        'Casquillo_punta_x1.5',      '#e45756'),
        (f'{C}/ASM_base_plate.stl',         'Gripper_base_plate_x1.5', '#c9ced6'),
        (f'{C}/ASM_gear_left.stl',          'Gripper_gear_left_x1.5',  '#4c78a8'),
        (f'{C}/ASM_gear_right.stl',         'Gripper_gear_right_x1.5', '#2f5d8a'),
        (f'{C}/ASM_arm_left.stl',           'Gripper_arm_left_x1.5',   '#f58518'),
        (f'{C}/ASM_arm_right.stl',          'Gripper_arm_right_x1.5',  '#e45756'),
        (f'{C}/ASM_jaw_left.stl',           'Gripper_jaw_left_x1.5',   '#54a24b'),
        (f'{C}/ASM_jaw_right.stl',          'Gripper_jaw_right_x1.5',  '#3b7d35'),
        (f'{C}/ASM_servo_MG90S_aprox.stl',  'Servo_MG90S_referencia',  '#2b2b2b'),
    ]
    main(items, out, 'Ensamblaje_Gripper_Brazo_Vasil_x1.5')
