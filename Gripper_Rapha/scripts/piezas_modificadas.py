"""Piezas de Vasil e Ignacio MODIFICADAS (copias; los originales no se tocan) y piezas nuevas.

Resuelven los problemas de la revisión y adaptan el brazo a los motores comprados, JGB37-520B de 12 V, 45 RPM,
con encoder (ver ENSAMBLAJE/README.md):
  - Codo movido igual que el hombro: segunda corona de 30 + piñón de 10 (módulo 3, 60 mm entre ejes) y motor
    atornillado a la parte plana de Shield 2.
  - Shield 1: cuna Ø37,6 a 7 mm del eje del piñón y 6 x M3 avellanados para atornillar el motor de cara.
  - Piñones: agujero en D 6,15 x 5,65 y rebaje Ø12,8 x 3 para el resalte Ø12 x 6 del motor.
  - Corona: agujero de planos 8,6 x 13,9 (entraba muy justa).
  - Gorrones Ø15 -> Ø14,2 (Paletas y Brazo Parte 1); rebaje en Paleta 1; avellanado M4 en Paleta 2.
  - Base: BASE_TAPA_SUP imprimible (pestaña aparte) y atornillada a Pieza_Eje_Giro_Base (no vuelca);
    Pieza_Eje_Giro_Base más alta, con prisionero y libre del resalte del motor; suplemento de 15 mm bajo
    BASE_TAPA_INF para el encoder.
  - Manguitos para centrar los potenciómetros.

Escribe: IMPRIMIR/1_base y IMPRIMIR/2_brazo (orientadas para imprimir) y ENSAMBLAJE/piezas_colocadas (montadas).
Uso (desde Gripper_Rapha):  python scripts/piezas_modificadas.py
"""
import os, sys, json, subprocess, tempfile, numpy as np, trimesh
import shapely.geometry as sg, shapely.affinity as sa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rutas import SCRIPTS, VAS, IGN, IMP_BASE, IMP_BRAZO, COL, TF_JSON, load_mm, orient, row, export

TF = json.load(open(TF_JSON))['piezas']
Mof = lambda k: np.array(TF[k]['matrix'])
D = lambda a, *b: trimesh.boolean.difference([a, *b], engine='manifold')
U = lambda *a: trimesh.boolean.union(list(a), engine='manifold')
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold')
V = lambda n: load_mm(os.path.join(VAS, n + '.stl'))
G = lambda n: load_mm(os.path.join(IGN, n + '.stl'))
def box(lo, hi): return trimesh.creation.box(bounds=[lo, hi])
def cyl(r, p0, p1, sec=96):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); a = p1 - p0; h = np.linalg.norm(a)
    c = trimesh.creation.cylinder(radius=r, height=h, sections=sec)
    c.apply_transform(trimesh.geometry.align_vectors([0, 0, 1.0], a / h)); c.apply_translation((p0 + p1) / 2); return c
def csink(p_face, axis_in, d_head=6.4, d_hole=3.4, depth=30.0, cbore=0.0):
    """Avellanado de 90° con la cabeza en p_face, entrando según axis_in (un solo sólido de revolución).
    cbore > 0: además un cajeado Ø6,6 de esa altura por encima de la cabeza (asiento más hondo)."""
    axis_in = np.asarray(axis_in, float) / np.linalg.norm(axis_in); R, rh = d_head / 2, d_hole / 2
    if cbore: prof = [(0, -1.0 - cbore), (3.3, -1.0 - cbore), (3.3, R - 3.3), (rh, R - rh), (rh, depth), (0, depth)]
    else: prof = [(0, -1.0), (R + 1.0, -1.0), (rh, R - rh), (rh, depth), (0, depth)]
    c = trimesh.creation.revolve(prof, sections=64)
    c.apply_transform(trimesh.geometry.align_vectors([0, 0, 1.0], axis_in)); c.apply_translation(np.asarray(p_face, float)); return c
def biggest(m): return max(m.split(only_watertight=False), key=lambda p: p.volume)

def save(folder, name, pr, own=None, M=None, placed=None):
    """pr: pieza para imprimir. own + M (o placed): pieza montada en ENSAMBLAJE/piezas_colocadas/<placed name>."""
    export(pr, os.path.join(folder, name + '.stl'))
    print(f'  {os.path.basename(folder)}/{name}: {np.round(pr.extents, 1).tolist()} mm')
    if own is not None and M is not None:
        for nm, mat in (M.items() if isinstance(M, dict) else [(name, M)]):
            w = own.copy(); w.apply_transform(mat)
            if w.volume < 0: w.invert()
            export(w, os.path.join(COL, nm + '.stl'))

JGB = dict(offset=7.0, pcd=31.0)                       # JGB37-520: eje a 7 mm del centro, 6 x M3 en Ø31
REB_D, REB_H = 12.8, 3.0                               # rebaje del piñón para el resalte Ø12 x 6 del motor

# =============== 1. Coronas de 30 dientes (hombro y codo), agujero de planos 8,6 x 13,9 ===============
def flats_bore(d=13.9, w=8.6): return sg.Point(0, 0).buffer(d / 2, 128).intersection(sg.box(-d, -w / 2, d, w / 2))
c30 = V('Corona - 30 dientes - modulo 2_1')                            # eje x (0..13,5), planos con normal y
c30 = U(c30, cyl(7.3, [0, 0, 0], [13.5, 0, 0]))
bore = trimesh.creation.extrude_polygon(flats_bore(), 15.5); bore.apply_translation([0, 0, -1])
bore.apply_transform(np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1.0]]))
c30 = D(c30, bore)
save(IMP_BRAZO, 'Corona_30_dientes_x2', row([orient(c30, [1, 0, 0])] * 2), c30,
     {'Corona_hombro': Mof('Vasil_Corona_hombro'), 'Corona_codo': Mof('Corona_codo')})

# =============== 2. Piñones: D 6,15 x 5,65 y rebaje para el resalte del motor (cara x=0 = lado del motor) ===============
pn = V('Piñon - 10 dientes - modulo 2_1')
def d_prism(axis, center, flat_dir, t0, t1, dia=6.15, across=5.65):
    r = dia / 2; c = trimesh.creation.cylinder(radius=r, height=t1 - t0, sections=96)
    c = D(c, box([-2 * r, across - r, -(t1 - t0)], [2 * r, 3 * r, (t1 - t0)]))
    a = np.asarray(axis, float); f = np.asarray(flat_dir, float); f -= a * (f @ a); f /= np.linalg.norm(f)
    R = np.eye(4); R[:3, :3] = np.c_[np.cross(f, a), f, a]; c.apply_transform(R); c.apply_translation(np.asarray(center, float) + a * (t0 + t1) / 2); return c
sec = pn.section(plane_origin=[6.75, 0, 0], plane_normal=[1, 0, 0]); hole = min((np.array(e) for e in sec.discrete), key=lambda p: np.ptp(p[:, 1]))
hp = hole[:, 1:]; fdir = hp[np.linalg.norm(hp, axis=1).argmin()]          # del eje (0,0) al plano de la D
pn = D(pn, d_prism([1, 0, 0], [0, 0, 0], [0, *fdir], -1, 14.5))
pn = D(pn, cyl(REB_D / 2, [-1, 0, 0], [REB_H, 0, 0]))
save(IMP_BRAZO, 'Pinon_10_dientes_x2', row([orient(pn, [-1, 0, 0])] * 2), pn,           # rebaje arriba: sin puentes
     {'Pinon_hombro': Mof('Vasil_Pinon_hombro'), 'Pinon_codo': Mof('Pinon_codo')})

# =============== 3. Shield 1: motor del hombro atornillado de cara y cuna Ø37,6 ===============
def shield_split(m, ax, face):
    lo, hi = m.bounds[0] - 1, m.bounds[1] + 1; lo2 = lo.copy(); lo2[ax] = face
    plate = biggest(D(m, box(lo2, hi))); lo3 = lo2.copy(); lo3[ax] = face + 1e-3
    seps = [p for p in I(m, box(lo3, hi)).split(only_watertight=False) if p.volume > 1]
    return plate, seps
s1 = V('Shield 1 - 2.0_1'); s1p, s1s = shield_split(s1, 0, 3.0)        # placa x 0..3, separadores x 3..18, cuna x -50..0
old_c, pin_c = np.array([21.9, 55.9]), np.array([30.0, 55.6])           # (y,z): centro de la cuna original, eje del piñón
u = (old_c - pin_c) / np.linalg.norm(old_c - pin_c); new_c = pin_c + JGB['offset'] * u
s1p = D(s1p, cyl(21.6, [-51, *old_c], [-0.02, *old_c]))
ring = sg.Point(*new_c).buffer(21.3, 128).difference(sg.Point(*new_c).buffer(18.8, 128))
wedge = sg.Polygon([tuple(new_c)] + [tuple(new_c + 40 * np.array([np.cos(a), np.sin(a)])) for a in np.radians(np.linspace(100, 230, 27))])
cr = trimesh.creation.extrude_polygon(ring.intersection(wedge), 50.0)
cr.apply_transform(np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])); cr.apply_translation([-50.0, 0, 0])
s1p = U(s1p, cr)
a0 = np.arctan2(*(pin_c - new_c)[::-1])
for k in range(6):                                                      # placa de 3 mm: con M3 x 6 entran 3 mm en el motor
    a = a0 + np.pi / 2 + k * np.pi / 3; p = new_c + JGB['pcd'] / 2 * np.array([np.cos(a), np.sin(a)])
    s1p = D(s1p, csink([3.0, *p], [-1, 0, 0]))
save(IMP_BRAZO, 'Shield_1_placa', orient(s1p, [-1, 0, 0]), s1p, Mof('Vasil_Shield_1'))
s1s_all = trimesh.util.concatenate(s1s)
save(IMP_BRAZO, 'Shield_1_separadores_x4', row([orient(s, [1, 0, 0]) for s in s1s]), s1s_all, Mof('Vasil_Shield_1'))

# =============== 4. Shield 2: motor del codo en la parte plana, eje del piñón a 60 mm del codo ===============
s2 = V('Shield 2 - 2.0_1'); s2p, s2s = shield_split(s2, 2, 4.5)        # placa z 0..4,5 (exterior z=0)
P2 = np.array([0.0, 105.0 - 60.0]); m2c = P2 + np.array([0.0, -JGB['offset']])
s2p = U(s2p, trimesh.creation.extrude_polygon(sg.Point(*m2c).buffer(21.0, 128), 4.5))
s2p = D(s2p, cyl(7.5, [P2[0], P2[1], -1], [P2[0], P2[1], 6]))          # paso del eje y del resalte (Ø15)
a0 = np.arctan2(P2[1] - m2c[1], P2[0] - m2c[0])
for k in range(6):                                                      # asiento 1,5 mm hondo: M3 x 6 entra 3 mm
    a = a0 + np.pi / 2 + k * np.pi / 3; p = m2c + JGB['pcd'] / 2 * np.array([np.cos(a), np.sin(a)])
    s2p = D(s2p, csink([p[0], p[1], 3.0], [0, 0, -1], cbore=1.5))
save(IMP_BRAZO, 'Shield_2_placa', orient(s2p, [0, 0, -1]), s2p, Mof('Vasil_Shield_2'))
save(IMP_BRAZO, 'Shield_2_separadores_x3', row([orient(s, [0, 0, 1]) for s in s2s]), trimesh.util.concatenate(s2s), Mof('Vasil_Shield_2'))

# =============== 5. Gorrones Ø15 -> Ø14,2; Paletas; Brazo Parte 1 ===============
def rebore(m, c, axis, t0, t1, d_old=15.0, d_new=14.2):
    p0 = np.asarray(c, float) + np.asarray(axis, float) * t0; p1 = np.asarray(c, float) + np.asarray(axis, float) * t1
    plug = I(cyl(d_old / 2 + 0.15, p0, p1), trimesh.convex.convex_hull(m))
    return D(U(m, plug), cyl(d_new / 2, p0 - np.asarray(axis) * 1, p1 + np.asarray(axis) * 1))
p1 = V('Base Tapa Superior - Paleta 1 - 2.0_1')
p1 = rebore(p1, [0, 52.5, 0], [1, 0, 0], 0.0, 4.5)
p1 = D(p1, cyl(12.0, [4.1, 52.5, 0], [5.0, 52.5, 0]))                   # rebaje de 0,4 mm donde apoya el clip
save(IMP_BRAZO, 'Paleta_1', orient(p1, [1, 0, 0]), p1, Mof('Vasil_Paleta_1'))
p2 = V('Base Tapa Superior - Paleta 2 - 2.0_1')
p2 = rebore(p2, [0, 52.5, 0], [1, 0, 0], 0.0, 4.5)
p2 = D(p2, csink([4.5, 58.8, 57.9], [-1, 0, 0], d_head=8.4, d_hole=6.0))   # M4 avellanado al revés (cara interior)
save(IMP_BRAZO, 'Paleta_2', orient(p2, [1, 0, 0]), p2, Mof('Vasil_Paleta_2'))
b11 = V('Brazo Parte 1_1'); b11 = rebore(b11, [180, 0, 0], [0, 0, 1], -19.5, -12.0)
save(IMP_BRAZO, 'Brazo_Parte_1_1', orient(b11, [0, 0, 1]), b11, Mof('Vasil_Brazo_Parte_1_1'))
b1 = V('Brazo Parte 1.1 2.0_1'); b1 = rebore(b1, [180, 0, 0], [0, 0, 1], 0.0, 7.5)
MB = Mof('Vasil_Brazo_Parte_1.1'); ax_c = (Mof('Vasil_Shield_2') @ [*P2, 0, 1])[:3]                # eje del motor del codo
ax_own = (np.linalg.inv(MB) @ [*ax_c, 1])[:3]
b1 = D(b1, cyl(4.0, [ax_own[0], ax_own[1], -5], [ax_own[0], ax_own[1], 12]))  # alivio Ø8 frente al eje del motor del codo
save(IMP_BRAZO, 'Brazo_Parte_1.1', orient(b1, [0, 0, 1]), b1, MB)

# =============== 6. Base ===============
MS = Mof('Ignacio_BASE_TAPA_SUP')
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.executable, os.path.join(SCRIPTS, 'build_base_sup_imprimible.py'), os.path.join(IGN, 'BASE_TAPA_SUP.stl'), tmp],
                   check=True, stdout=subprocess.DEVNULL)
    sup = trimesh.load(os.path.join(tmp, 'comprobacion', 'BASE_TAPA_SUP_imprimible_posicion_montaje.stl'))
    tab_pr = trimesh.load(os.path.join(tmp, 'BASE_TAPA_SUP_pestana.stl'))
    tab_own = trimesh.load(os.path.join(tmp, 'comprobacion', 'BASE_TAPA_SUP_pestana_posicion_montaje.stl'))
sup = D(sup, cyl(1.7, [0, -2, 0], [0, 4, 0]), cyl(3.3, [0, 1.0, 0], [0, 4, 0]))      # M3 desde arriba, cabeza rebajada
save(IMP_BASE, 'BASE_TAPA_SUP_cuerpo', orient(sup, [0, 1, 0]), sup, MS)
save(IMP_BASE, 'BASE_TAPA_SUP_pestana', tab_pr, tab_own, MS)

# Pieza_Eje_Giro_Base (propia: y de -26 a 0, agujero en D pasante, plano de la D en z=-2,575):
#  - sube hasta 0,15 mm del techo del alojamiento de SUP (y=9,6) y lleva un taladro guía para el M3 desde SUP
#  - se recorta 4 mm por abajo (y=-22) para librar el resalte del motor y las cabezas de sus tornillos
#  - prisionero M3 contra el plano de la D, a 3,5 mm del nuevo borde
pz = G('Pieza_Eje_Giro_Base'); top_y = 9.6
pz = U(pz, box([pz.bounds[0][0], -0.01, pz.bounds[0][2]], [pz.bounds[1][0], top_y, pz.bounds[1][2]]))
pz = D(pz, cyl(1.25, [0, top_y - 8, 0], [0, top_y + 1, 0]))
pz = D(pz, box([-50, -40, -50], [50, -22.0, 50]))
pz = D(pz, cyl(1.25, [0, -18.5, -2.0], [0, -18.5, -9]))
save(IMP_BASE, 'Pieza_Eje_Giro_Base', orient(pz, [0, -1, 0]), pz, Mof('Ignacio_Pieza_Eje_Giro_Base'))

# Suplemento de 15 mm bajo BASE_TAPA_INF: marco con el contorno de su base, las 4 orejetas y salida de cables
inf = G('BASE_TAPA_INF'); inf.apply_transform(Mof('Ignacio_BASE_TAPA_INF')); y_bot = inf.bounds[0][1]
T2 = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])            # (x,y,z) -> (x,z) en planta
P, _ = inf.section(plane_origin=[0, y_bot + 0.1, 0], plane_normal=[0, 1, 0]).to_2D(to_2D=T2)
polys = list(P.polygons_full); big = max(polys, key=lambda p: p.area)
H = 15.0
frame = sg.Polygon(big.exterior).difference(sg.Polygon(big.exterior).buffer(-7.0, join_style=2))
for t in polys:
    if t is not big: frame = frame.union(t)
frame = frame.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
geoms = list(frame.geoms) if hasattr(frame, 'geoms') else [frame]
foot = U(*[trimesh.creation.extrude_polygon(g, H) for g in geoms]) if len(geoms) > 1 else trimesh.creation.extrude_polygon(geoms[0], H)
foot = D(foot, box([-80, 20, -1], [-55, 38, 10]))                       # salida de cables 18 x 10 en el lado -x
Mfoot = np.array([[1, 0, 0, 0], [0, 0, 1, y_bot - H], [0, 1, 0, 0], [0, 0, 0, 1.0]])
save(IMP_BASE, 'Base_suplemento_15mm', orient(foot, [0, 0, 1]), foot, Mfoot)

# =============== 7. Manguitos para centrar los potenciómetros (tipo WH148, cuerpo Ø16-17) ===============
sl = trimesh.creation.extrude_polygon(sg.Point(0, 0).buffer(11.4, 96).difference(sg.Point(0, 0).buffer(8.35, 96)).difference(sg.box(-0.8, 8, 0.8, 12)), 12.0)
save(IMP_BRAZO, 'Manguito_potenciometro_x2', row([sl, sl]))
print('piezas_modificadas: hecho')
