"""Gripper SuperbTech escalado x1.5 y adaptado a MG90S + tornillería M3.
Marco del gripper (original): plano de la placa XZ, Y = normal (arriba), mordazas hacia -X,
pared de montaje en +X.  Todo se escala x1.5 respecto al origen y después:
  - la capa móvil (engranajes, bielas, mordazas) baja 4 mm para que el eje real del servo llegue al engranaje
  - los separadores de la placa se recortan a 0.5 mm
  - se rehacen a tamaño real: hueco y taladros del servo, acople del eje, pivotes M3, taladros de la pared
"""
import trimesh, numpy as np, sys, os, json
from trimesh.creation import cylinder, box

SRC = sys.argv[1]; OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
S = 1.5
DY = -4.0                      # bajada de la capa móvil
HOLE_M3 = 3.4                  # pivotes M3 (giro libre)
SERVO_PILOT = 1.8              # tornillos autorroscantes del MG90S
SPLINE = 4.9                   # agujero para el estriado del MG90S (el original funcionaba con 4.9)
CBORE = 7.0                    # cajeado para tornillo + arandela del eje

def U(*ms):  return trimesh.boolean.union(list(ms), engine='manifold')
def D(a,*b): return trimesh.boolean.difference([a]+list(b), engine='manifold')

def ycyl(x, z, r, y0, y1, sections=64):
    c = cylinder(radius=r, height=y1-y0, sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]))  # eje Z -> eje Y
    c.apply_translation([x, (y0+y1)/2, z]); return c
def xcyl(y, z, r, x0, x1, sections=48):
    c = cylinder(radius=r, height=x1-x0, sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]))   # eje Z -> eje X
    c.apply_translation([(x0+x1)/2, y, z]); return c
def bx(x0,x1,y0,y1,z0,z1):
    b = box(extents=[x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b

def load(name, dy=0.0):
    m = trimesh.load(os.path.join(SRC, name+'.stl'))
    m.apply_scale(S); m.apply_translation([0, dy, 0]); return m

def material_y_range(m, x, z, r):
    """Tramo en Y donde hay material alrededor de un agujero de radio r (rayos en el anillo r+0.6)."""
    lo, hi = -1e9, 1e9
    for a in np.linspace(0, 2*np.pi, 12, endpoint=False):
        o = [x+(r+0.6)*np.cos(a), -200, z+(r+0.6)*np.sin(a)]
        loc,_,_ = m.ray.intersects_location([o], [[0,1,0]])
        if len(loc)==0: continue
        ys = np.sort(np.atleast_2d(loc)[:,1])
        lo = max(lo, ys[0]); hi = min(hi, ys[-1])
    return lo, hi

def refit_hole(m, x, z, r_old, d_new):
    y0, y1 = material_y_range(m, x, z, r_old)
    plug = ycyl(x, z, r_old+0.3, y0+0.02, y1-0.02)
    m = U(m, plug)
    return D(m, ycyl(x, z, d_new/2, y0-1, y1+1)), (y0, y1)

P = lambda x,z: (x*S, z*S)
H = {   # agujeros originales (marco del gripper, mm sin escalar)
 'crank_l': P(-0.38,-29.76), 'gear_l': P(29.62,-29.76),
 'crank_r': P(-0.38,-7.76),  'servo':  P(29.62,-7.76),
 'arml_end':P(-20.38,-23.26),'arml_base':P(9.62,-23.26),
 'armr_end':P(-20.38,-14.26),'armr_base':P(9.62,-14.26),
}
r_m3_old = 3.3*S/2
log = {}

# ---------- piezas móviles ----------
parts = {}
for name, holes in [('gear_left',['crank_l','gear_l']), ('gear_right',['crank_r']),
                    ('arm_left',['arml_end','arml_base']), ('arm_right',['armr_end','armr_base']),
                    ('jaw_left',['crank_l','arml_end']), ('jaw_right',['crank_r','armr_end'])]:
    m = load(name, DY)
    for h in holes:
        m, yr = refit_hole(m, *H[h], r_m3_old, HOLE_M3)
        log[f'{name}:{h}'] = [round(v,2) for v in yr]
    parts[name] = m

# acople del servo en gear_right: estriado Ø4.9 abajo + cajeado Ø7 arriba (2 mm)
g = parts['gear_right']; sx, sz = H['servo']
y0, y1 = material_y_range(g, sx, sz, 4.9*S/2)
g = U(g, ycyl(sx, sz, 4.9*S/2+0.3, y0+0.02, y1-0.02))
g = D(g, ycyl(sx, sz, SPLINE/2, y0-1, y1+1), ycyl(sx, sz, CBORE/2, y1-2.0, y1+1))
parts['gear_right'] = g; log['gear_right:servo_layer'] = [round(y0,2), round(y1,2)]

# ---------- placa base ----------
b = load('base_plate')
PLATE_TOP = 5.0*S                     # 7.5
# 1) recortar separadores a 0.5 mm (capa móvil empieza en 8.0)
for h in ['gear_l','arml_base','armr_base']:
    x,z = H[h]; b = D(b, ycyl(x, z, 6.0*S/2+0.6, PLATE_TOP+0.5, 30))
# 2) pivotes a Ø3.4
for h in ['gear_l','arml_base','armr_base']:
    x,z = H[h]
    b = U(b, ycyl(x, z, 3.4*S/2+0.3, 0.02, PLATE_TOP+0.48))
    b = D(b, ycyl(x, z, HOLE_M3/2, -1, 20))
# 3) hueco del servo: rellenar el escalado y hacer el real (MG90S 22.8 x 12.2 + holgura)
cx_o, cz_o = 29.62*S, -12.76*S
b = U(b, bx(cx_o-13*S/2-0.3, cx_o+13*S/2+0.3, 0.02, PLATE_TOP-0.02, cz_o-23*S/2-0.3, cz_o+23*S/2+0.3))
for zz in [0.99, -26.51]:
    b = U(b, ycyl(29.62*S, zz*S, 2.0*S/2+0.3, 0.02, PLATE_TOP-0.02))
SERVO_OFF = 5.0                        # eje desplazado 5 mm del centro del cuerpo (igual que el original)
scx, scz = sx, sz - SERVO_OFF
b = D(b, bx(scx-12.6/2, scx+12.6/2, -1, 20, scz-23.2/2, scz+23.2/2))
for zz in [scz+13.75, scz-13.75]:
    b = D(b, ycyl(scx, zz, SERVO_PILOT/2, -1, PLATE_TOP+1))
# 4) pared de montaje: tapar Ø6.6 y hacer 4 x M3
WALL_X0, WALL_X1 = 44.62*S, 49.62*S
WALL_YC, WALL_ZC = 12.5*S, -18.76*S
b = U(b, xcyl(WALL_YC, WALL_ZC, 4.4*S/2+0.3, WALL_X0+0.02, WALL_X1-0.02))
GRIP_ZC = -18.76*S
WALL_HOLES = [(yy, GRIP_ZC+dz) for yy in (19.0, 29.0) for dz in (22.0, -22.0)]
for yy, zz in WALL_HOLES:
    b = D(b, xcyl(yy, zz, HOLE_M3/2, WALL_X0-1, WALL_X1+1))
parts['base_plate'] = b

meta = dict(scale=S, dy_moving=DY, wall_x_outer=WALL_X1, wall_holes_yz=WALL_HOLES,
            grip_center_yz=[2.0, GRIP_ZC], servo_shaft_xz=[sx,sz], servo_slot_center_xz=[scx,scz], log=log)
for k,m in parts.items():
    m.export(os.path.join(OUT, f'{k}_x1.5.stl'))
    meta[k] = dict(watertight=bool(m.is_watertight), volume=round(float(m.volume),1),
                   bounds=np.round(m.bounds,2).tolist())
json.dump(meta, open(os.path.join(OUT,'gripper_meta.json'),'w'), indent=1)
print(json.dumps({k:v for k,v in meta.items() if k!='log'}, indent=1)); print(log)
