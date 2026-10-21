"""Acople fijo del gripper x1,5 a la punta del antebrazo de Vasil, que son DOS placas paralelas:
  A = Arm_Vasil/Brazo_modificado/Brazo Parte 2_1      (z de -27 a -19,5; avellanado Ø24 hacia +z)
  B = Arm_Vasil/Brazo_modificado/Brazo Parte 2.2_4    (z de -7,5 a 0;    avellanado Ø24 hacia -z;
                                                       orejetas Ø6 en (138, ±26,2), z de -3 a 0)
Ambas en las coordenadas propias de sus .par (mm): codo en x=0, punta en x=150, entre ellas un hueco de 12 mm.
No modifica nada del brazo.

Piezas que genera:
  acople_punta_vasil_x1.5   bloque que entra en el hueco entre placas + labios que abrazan los cantos
                            + alas bajo las orejetas de B + brida para la pared del gripper
  casquillo_punta_x1.5      casquillo con valona que rellena los agujeros Ø15 de A, bloque y B
  contraplaca_acople_x1.5   arandela grande bajo la cara plana de A (con alojamiento de tuerca M5)

Uso: python build_mount_vasil.py <placaA.stl> <placaB.stl> <carpeta build del gripper> <salida>
"""
import trimesh, numpy as np, os, sys, json
from trimesh.creation import cylinder, box
import shapely.geometry as sg

FORE_A, FORE_B, GRIP, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
def U(*ms):  return trimesh.boolean.union(list(ms), engine='manifold')
def D(a, *b): return trimesh.boolean.difference([a] + list(b), engine='manifold')
def I(a, b):  return trimesh.boolean.intersection([a, b], engine='manifold')

# ---------- interfaz medida en las piezas de Vasil ----------
CX, CY = 150.0, 0.0                 # eje de la punta (común a las dos placas)
R_PLATE = 15.0                      # placas de 30 mm con extremo R15
ZA0, ZA1 = -27.0, -19.5             # placa A
ZB0, ZB1 = -7.5, 0.0                # placa B
EAR_X, EAR_Y, EAR_Z0 = 138.0, 26.2, -3.0           # orejetas de B (Ø6), de z=-3 a 0
EAR_PAD = (121.9, 154.6, 14.1, 32.6)               # huella de las orejetas (x0, x1, |y|0, |y|1) + holgura
ZMID = (ZA1 + ZB0) / 2              # centro del hueco entre placas: -13,5

# ---------- parámetros ----------
CLR, GAP_CLR = 0.3, 0.15            # holgura lateral / en el hueco entre placas
WALL = 4.2
R_OUT = R_PLATE + CLR + WALL        # 19,5
X0 = 124.0                          # inicio del acople hacia el codo
LIP_Z0, LIP_Z1 = ZA0 + 0.4, EAR_Z0 - 0.2           # labios: no tocan la contraplaca ni las orejetas
WING_X = (EAR_X - 8.0, EAR_X + 8.0); WING_Y1 = 32.0
M5, M5_NUT_AF, M5_NUT_H = 5.4, 8.4, 4.2
M3, M3_NUT_AF, M3_NUT_D = 3.4, 5.8, 3.0
SLEEVE_R = 7.5 - 0.2                # casquillo Ø14,6 en los agujeros Ø15
FLANGE_R, FLANGE_H = 11.0, 2.5      # valona del casquillo sobre la cara exterior de B
BACK = 5.0                          # contraplaca
FL = 6.0
XF1 = CX + R_OUT + 4.0              # cara de apoyo de la pared del gripper (173,5)
XF0 = XF1 - FL

def zcyl(x, y, r, z0, z1, sec=96):
    c = cylinder(radius=r, height=z1 - z0, sections=sec); c.apply_translation([x, y, (z0 + z1) / 2]); return c
def xcyl(y, z, r, x0, x1, sec=48):
    c = cylinder(radius=r, height=x1 - x0, sections=sec)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])); c.apply_translation([(x0 + x1) / 2, y, z]); return c
def bx(x0, x1, y0, y1, z0, z1):
    b = box(extents=[x1 - x0, y1 - y0, z1 - z0]); b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]); return b
def stadium(r, x0, z0, z1):
    poly = sg.box(x0, -r, CX, r).union(sg.Point(CX, CY).buffer(r, 128))
    m = trimesh.creation.extrude_polygon(poly, z1 - z0); m.apply_translation([0, 0, z0]); return m
def hexz(x, y, af, z0, z1):
    r = af / np.sqrt(3); a = np.radians(np.arange(0, 360, 60))
    m = trimesh.creation.extrude_polygon(sg.Polygon(np.c_[x + r*np.cos(a), y + r*np.sin(a)]), z1 - z0)
    m.apply_translation([0, 0, z0]); return m
def hexx(y, z, af, x0, x1):
    m = hexz(0, 0, af, 0, x1 - x0)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    b = m.bounds; m.apply_translation([x0 - b[0][0], y, z]); return m

# ---------- gripper -> coordenadas del antebrazo ----------
gm = json.load(open(os.path.join(GRIP, 'gripper_meta.json')))
WALL_X = gm['wall_x_outer']; GY, GZ = gm['grip_center_yz']
R_g = np.diag([-1.0, 1.0, -1.0])
def grip_to_arm(m):
    M = np.eye(4); M[:3, :3] = R_g; M[:3, 3] = [XF1 + WALL_X, CY - GY, ZMID + GZ]
    m = m.copy(); m.apply_transform(M); return m
def gp(yg, zg): return CY + (yg - GY), ZMID - (zg - GZ)

# ---------- ACOPLE ----------
block = stadium(R_OUT, X0, ZA1 + GAP_CLR, ZB0 - GAP_CLR)                 # entre las placas
lips = stadium(R_OUT, X0, LIP_Z0, LIP_Z1)                                 # vaso que abraza los cantos
wings = [bx(*WING_X, s * (R_PLATE + CLR), s * WING_Y1, LIP_Z0, LIP_Z1) if s > 0 else
         bx(*WING_X, -WING_Y1, -(R_PLATE + CLR), LIP_Z0, LIP_Z1) for s in (1, -1)]
holes_yz = [gp(y, z) for (y, z) in gm['wall_holes_yz']]
fl_y0 = CY - R_OUT; fl_y1 = max(y for y, _ in holes_yz) + 6.0
fl_z0 = min(z for _, z in holes_yz) - 7.0; fl_z1 = max(z for _, z in holes_yz) + 7.0
flange = bx(XF0, XF1, fl_y0, fl_y1, fl_z0, fl_z1)
hz = sorted(set(round(z, 3) for _, z in holes_yz)); ymin_h = min(y for y, _ in holes_yz)
flange = D(flange,
           bx(XF0 - 1, XF1 + 1, fl_y0 - 1, ymin_h - 6.0, fl_z0 - 1, LIP_Z0 - 1.5),
           bx(XF0 - 1, XF1 + 1, fl_y0 - 1, ymin_h - 6.0, ZB1 + 1.5, fl_z1 + 1),
           bx(XF0 - 1, XF1 + 1, CY + R_OUT + 1.0, fl_y1 - 4.0, hz[0] + 6.0, hz[-1] - 6.0))
end = stadium(R_OUT, CX, LIP_Z0, LIP_Z1)
strip = bx(XF0, XF0 + 0.05, CY - R_OUT, CY + R_OUT, LIP_Z0, LIP_Z1)
web = trimesh.convex.convex_hull(trimesh.util.concatenate([end, strip]))
mount = U(block, lips, *wings, web, flange)

# huecos de las placas (con holgura) y de sus orejetas
cav_plate = lambda z0, z1: U(stadium(R_PLATE + CLR, X0 - 5, z0, z1), bx(X0 - 10, CX, -(R_PLATE + CLR), R_PLATE + CLR, z0, z1))
ear_cav = [bx(EAR_PAD[0], EAR_PAD[1], s * EAR_PAD[2], s * EAR_PAD[3], EAR_Z0 - 0.15, ZB1 + 5) if s > 0 else
           bx(EAR_PAD[0], EAR_PAD[1], -EAR_PAD[3], -EAR_PAD[2], EAR_Z0 - 0.15, ZB1 + 5) for s in (1, -1)]
mount = D(mount, cav_plate(ZA0 - 5, ZA1 + GAP_CLR), cav_plate(ZB0 - GAP_CLR, ZB1 + 10), *ear_cav)
# casquillo central, tornillos de las orejetas y de la pared del gripper
mount = D(mount, zcyl(CX, CY, 7.5, ZA0 - 10, ZB1 + 10))
for s in (1, -1):
    mount = D(mount, zcyl(EAR_X, s * EAR_Y, M5 / 2, LIP_Z0 - 1, ZB1 + 1),
                     hexz(EAR_X, s * EAR_Y, M5_NUT_AF, LIP_Z0 - 1, LIP_Z0 + M5_NUT_H))
for (y, z) in holes_yz:
    mount = D(mount, xcyl(y, z, M3 / 2, XF0 - 1, XF1 + 1), hexx(y, z, M3_NUT_AF, XF0 - 20, XF0 + M3_NUT_D))

# ---------- CASQUILLO (con valona) ----------
sleeve = U(zcyl(CX, CY, SLEEVE_R, ZA0 + 0.5, ZB1 + 0.01), zcyl(CX, CY, FLANGE_R, ZB1, ZB1 + FLANGE_H))
sleeve = D(sleeve, zcyl(CX, CY, M5 / 2, ZA0 - 1, ZB1 + FLANGE_H + 1))

# ---------- CONTRAPLACA ----------
back = stadium(R_OUT, CX - 18.0, ZA0 - BACK, ZA0)
back = I(back, bx(CX - 30, XF0 - 0.5, -50, 50, ZA0 - BACK - 1, ZA0 + 1))
back = D(back, zcyl(CX, CY, M5 / 2, ZA0 - 10, ZA0 + 1), hexz(CX, CY, M5_NUT_AF, ZA0 - BACK - 1, ZA0 - BACK + M5_NUT_H))

def clean(m):
    m = max(m.split(only_watertight=False), key=lambda p: abs(p.volume))
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices(); return m

res = {}
for name, m in [('acople_punta_vasil_x1.5', mount), ('casquillo_punta_x1.5', sleeve), ('contraplaca_acople_x1.5', back)]:
    m = clean(m); m.export(os.path.join(OUT, name + '.stl')); m = trimesh.load(os.path.join(OUT, name + '.stl'))
    res[name] = dict(watertight=bool(m.is_watertight), volume=round(float(m.volume), 1), extents=np.round(m.extents, 1).tolist())
for k in ['base_plate', 'gear_left', 'gear_right', 'arm_left', 'arm_right', 'jaw_left', 'jaw_right', 'servo_MG90S_aprox']:
    f = os.path.join(GRIP, f'{k}_x1.5.stl') if k != 'servo_MG90S_aprox' else os.path.join(GRIP, 'servo_MG90S_aprox_x1.stl')
    if os.path.exists(f): grip_to_arm(trimesh.load(f)).export(os.path.join(OUT, f'ASM_{k}.stl'))
json.dump(dict(res=res, zmid=ZMID, flange_x=[XF0, XF1], holes_yz=holes_yz,
               grip_offset=[XF1 + WALL_X, CY - GY, ZMID + GZ]), open(os.path.join(OUT, 'mount_meta.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
