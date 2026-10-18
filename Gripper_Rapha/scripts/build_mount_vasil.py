"""Acople fijo del gripper x1,5 a la punta del antebrazo de Vasil (Arm_Vasil/Brazo Parte 2_1.par).
No modifica nada del brazo: abraza el extremo de la placa (agujero Ø15 + avellanado Ø24).

Coordenadas = las del propio .par de Vasil (mm):
  x a lo largo del antebrazo (codo en x=0, punta en x=150), y en el plano de movimiento,
  z = eje de las articulaciones; placa entre z=-27 (cara plana) y z=-19.5 (cara con el rebaje).

Uso: python build_mount_vasil.py <forearm.stl> <carpeta build del gripper> <salida>
"""
import trimesh, numpy as np, os, sys, json
from trimesh.creation import cylinder, box
import shapely.geometry as sg

FORE, GRIP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
def U(*ms):  return trimesh.boolean.union(list(ms), engine='manifold')
def D(a, *b): return trimesh.boolean.difference([a] + list(b), engine='manifold')

# ---------- interfaz medida en el .par de Vasil ----------
CX, CY = 150.0, 0.0          # centro del agujero de la punta
R_PLATE = 15.0               # placa de 30 mm de ancho con extremo redondo R15
ZB, ZT = -27.0, -19.5        # caras de la placa
CB_R, CB_FLOOR = 12.0, -24.0 # avellanado Ø24 hasta z=-24 (cara superior)
ZMID = (ZB + ZT) / 2

# ---------- parámetros del acople ----------
CLR = 0.3                    # holgura lateral con la placa
WALL = 4.2                   # labios laterales
R_OUT = R_PLATE + CLR + WALL # 19.5
X0 = 118.0                   # inicio del acople (hacia el codo)
CAP = 6.0                    # grosor de la tapa sobre la cara superior
BOSS_R = CB_R - 0.25         # resalte que entra en el avellanado
BOSS_Z0 = CB_FLOOR + 0.2
BACK = 4.0                   # contraplaca bajo la cara plana
M5, M5_NUT_AF, M5_NUT_H = 5.4, 8.4, 4.2
M3, M3_NUT_AF, M3_NUT_D = 3.4, 5.8, 3.0
FL = 6.0                     # brida para la pared del gripper
XF1 = CX + R_OUT + 4.0       # cara de apoyo de la pared del gripper (173.5)
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
R_g = np.diag([-1.0, 1.0, -1.0])                     # rotación propia (det = +1)
def grip_to_arm(m):
    M = np.eye(4); M[:3, :3] = R_g
    M[:3, 3] = [XF1 + WALL_X, CY - GY, ZMID + GZ]
    m = m.copy(); m.apply_transform(M); return m
def gp(yg, zg): return CY + (yg - GY), ZMID - (zg - GZ)          # (y, z) en el brazo

# ---------- ACOPLE ----------
LIP_GAP = 0.4                # los labios no llegan a la cara plana: la contraplaca aprieta la placa, no los labios
cup = stadium(R_OUT, X0, ZB + LIP_GAP, ZT + CAP)
cav = stadium(R_PLATE + CLR, X0 - 1, ZB - 1, ZT)
cav = U(cav, bx(X0 - 5, CX, -(R_PLATE + CLR), R_PLATE + CLR, ZB - 1, ZT))
holes_yz = [gp(y, z) for (y, z) in gm['wall_holes_yz']]
fl_y0 = CY - R_OUT
fl_y1 = max(y for y, _ in holes_yz) + 6.0
fl_z0 = min(z for _, z in holes_yz) - 7.0; fl_z1 = max(z for _, z in holes_yz) + 7.0
flange = bx(XF0, XF1, fl_y0, fl_y1, fl_z0, fl_z1)
strip = bx(XF0, XF0 + 0.05, CY - R_OUT, CY + R_OUT, ZMID - 12, ZMID + 12)   # nervio solo frente al vaso
end = stadium(R_OUT, CX, ZB + LIP_GAP, ZT + CAP)                    # mitad redonda del vaso
web = trimesh.convex.convex_hull(trimesh.util.concatenate([end, strip]))
web = trimesh.boolean.intersection([web, bx(CX - 30, XF1, -100, 100, ZB + LIP_GAP, 100)], engine='manifold')   # deja libre la cara plana para la contraplaca
# aligerar la brida: esquinas inferiores y ventana central superior (sin tornillos)
hz = sorted(set(round(z, 3) for _, z in holes_yz))
flange = D(flange,
           bx(XF0 - 1, XF1 + 1, fl_y0 - 1, min(y for y, _ in holes_yz) - 6.0, fl_z0 - 1, ZMID - R_OUT - 1.5),
           bx(XF0 - 1, XF1 + 1, fl_y0 - 1, min(y for y, _ in holes_yz) - 6.0, ZMID + R_OUT + 1.5, fl_z1 + 1),
           bx(XF0 - 1, XF1 + 1, CY + R_OUT + 1.0, fl_y1 - 4.0, hz[0] + 6.0, hz[-1] - 6.0))
mount = U(cup, web, flange)
mount = D(mount, cav)
mount = U(mount, zcyl(CX, CY, BOSS_R, BOSS_Z0, ZT + 0.01))
mount = D(mount, zcyl(CX, CY, M5 / 2, ZB - 5, ZT + 60),
                 hexz(CX, CY, M5_NUT_AF, ZT + CAP - M5_NUT_H, ZT + 60))     # tuerca M5 arriba
for (y, z) in holes_yz:
    mount = D(mount, xcyl(y, z, M3 / 2, XF0 - 1, XF1 + 1), hexx(y, z, M3_NUT_AF, XF0 - 20, XF0 + M3_NUT_D))

# ---------- CONTRAPLACA ----------
back = stadium(R_OUT, CX - 18.0, ZB - BACK, ZB)
back = trimesh.boolean.intersection([back, bx(CX - 30, XF0 - 0.5, -50, 50, ZB - BACK - 1, ZB + 1)], engine='manifold')   # no invade la brida
back = D(back, zcyl(CX, CY, M5 / 2, ZB - 10, ZB + 1))

def clean(m):
    m = max(m.split(only_watertight=False), key=lambda p: abs(p.volume))
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices(); return m

res = {}
for name, m in [('acople_punta_vasil_x1.5', mount), ('contraplaca_acople_x1.5', back)]:
    m = clean(m); m.export(os.path.join(OUT, name + '.stl')); m = trimesh.load(os.path.join(OUT, name + '.stl'))
    res[name] = dict(watertight=bool(m.is_watertight), volume=round(float(m.volume), 1), extents=np.round(m.extents, 1).tolist())
for k in ['base_plate', 'gear_left', 'gear_right', 'arm_left', 'arm_right', 'jaw_left', 'jaw_right', 'servo_MG90S_aprox']:
    f = os.path.join(GRIP, f'{k}_x1.5.stl') if k != 'servo_MG90S_aprox' else os.path.join(GRIP, 'servo_MG90S_aprox_x1.stl')
    if os.path.exists(f): grip_to_arm(trimesh.load(f)).export(os.path.join(OUT, f'ASM_{k}.stl'))
json.dump(dict(res=res, flange_x=[XF0, XF1], holes_yz=holes_yz, R_g=R_g.tolist(),
               grip_offset=[XF1 + WALL_X, CY - GY, ZMID + GZ]), open(os.path.join(OUT, 'mount_meta.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
