"""Monta el brazo entero (base + brazo + gripper) con las piezas finales y lo comprueba.

Lee:     ENSAMBLAJE/transformaciones.json (dónde va cada pieza), los STL de Vasil e Ignacio que se usan sin
         cambios, GRIPPER/comprobacion/ASM_* y lo que ya ha dejado piezas_modificadas.py en ENSAMBLAJE/piezas_colocadas.
Escribe: ENSAMBLAJE/piezas_colocadas/   cada pieza colocada (se pueden importar una a una en Solid Edge)
         ENSAMBLAJE/ensamblaje_brazo.stl          todas las piezas en un solo STL (mm)
         ENSAMBLAJE/motores_JGB37_referencia.stl  los 3 motores JGB37-520B con encoder (no se imprimen)
         ENSAMBLAJE/imagenes/                     vistas del brazo
Marco: origen en el eje de giro de la base, sobre el escalón de BASE_TAPA_INF; Y hacia arriba; X = eje del
hombro y del codo.

Uso (desde Gripper_Rapha):
    python scripts/montar_ensamblaje.py               # monta + interferencias
    python scripts/montar_ensamblaje.py --barrido     # además recorre el hombro de -130° a +130°
"""
import os, sys, json, itertools, numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rutas import REPO, GR, ENS, COL, TF_JSON, load_mm, export

TF = json.load(open(TF_JSON))['piezas']; Mof = lambda k: np.array(TF[k]['matrix'])
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold')

# ---------- piezas que se usan sin cambios ----------
SIN_CAMBIOS = {'BASE_TAPA_INF': 'Ignacio_BASE_TAPA_INF', 'Eje_Parte_1': 'Vasil_Eje_Parte_1', 'Eje_Parte_2': 'Vasil_Eje_Parte_2',
               'Brazo_Parte_2_1': 'Vasil_Brazo_Parte_2_1', 'Brazo_Parte_2.2_4': 'Vasil_Brazo_Parte_2.2_4',
               'Sujetador_hombro': 'Vasil_Sujetador_hombro', 'Sujetador_codo': 'Vasil_Sujetador_codo'}
SIN_CAMBIOS.update({'Gripper_' + k[len('Rapha_'):].replace('acople_punta_vasil', 'acople_punta'): k for k in TF if k.startswith('Rapha_')})
for name, key in SIN_CAMBIOS.items():
    src = TF[key]['src']; src = os.path.join(GR, src[len('Gripper_Rapha/'):]) if src.startswith('Gripper_Rapha/') else os.path.join(REPO, src)
    m = load_mm(src); m.apply_transform(Mof(key)); export(m, os.path.join(COL, name + '.stl'), check=False)

# ---------- motores JGB37-520B (12 V, 45 RPM: reductora de 26,5 mm) con encoder ----------
JGB = dict(offset=7.0, L=26.5, gear_d=37.0, mot_d=33.0, mot_l=22.7, enc_l=11.75, conn=7.0, boss_d=12.0, boss_h=6.0, shaft=15.5)
def cyl(r, p0, p1, sec=64):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); a = p1 - p0; h = np.linalg.norm(a)
    c = trimesh.creation.cylinder(radius=r, height=h, sections=sec)
    c.apply_transform(trimesh.geometry.align_vectors([0, 0, 1.0], a / h)); c.apply_translation((p0 + p1) / 2); return c
def jgb37b(face, axis, toward, L=JGB['L']):
    """face: punto del eje del motor en la cara de la reductora; axis: hacia donde sale el eje; toward: del eje al centro."""
    a = np.asarray(axis, float); a /= np.linalg.norm(a); t = np.asarray(toward, float); t -= a * (t @ a); t /= np.linalg.norm(t)
    f = np.asarray(face, float); c = f + JGB['offset'] * t; e = L + JGB['mot_l']
    return {'reductora': cyl(JGB['gear_d'] / 2, c, c - a * L), 'motor': cyl(JGB['mot_d'] / 2, c - a * L, c - a * e),
            'encoder': cyl(16.0, c - a * e, c - a * (e + JGB['enc_l'])),
            'conector': cyl(5.0, c - a * (e + JGB['enc_l']), c - a * (e + JGB['enc_l'] + JGB['conn']), 24),
            'resalte': cyl(JGB['boss_d'] / 2, f, f + a * JGB['boss_h'], 48), 'eje': cyl(2.9, f + a * JGB['boss_h'], f + a * JGB['shaft'], 32)}
M2 = Mof('Vasil_Shield_2'); ax_codo = (M2 @ [0, 45, 0, 1])[:3]
MOT = {'hombro': jgb37b([-43.6, 52.5, 55.6], [1, 0, 0], [0, -8.1, 0.3]),          # en la cuna de Shield 1
       'codo': jgb37b(ax_codo, [1, 0, 0], -M2[:3, 1]),                             # en la parte plana de Shield 2
       'base': jgb37b([0, -21.3, 0], [0, 1, 0], [0, 0, 1])}                        # bajo el techo de la torre de BASE_TAPA_INF
mot_all = trimesh.util.concatenate([p for m in MOT.values() for p in m.values()])
mot_all.export(os.path.join(ENS, 'motores_JGB37_referencia.stl'))

P = {f[:-4]: trimesh.load(os.path.join(COL, f)) for f in sorted(os.listdir(COL)) if f.endswith('.stl')}
trimesh.util.concatenate(list(P.values())).export(os.path.join(ENS, 'ensamblaje_brazo.stl'))
print(f'{len(P)} piezas -> ENSAMBLAJE/ensamblaje_brazo.stl')

# ---------- interferencias ----------
def bodies(m): return [m] if m.is_volume else [p for p in m.split(only_watertight=True) if p.is_volume]
def overlap(A, B):
    if np.any(A.bounds[1] < B.bounds[0]) or np.any(B.bounds[1] < A.bounds[0]): return 0.0
    v = 0.0
    for a in bodies(A):
        for b in bodies(B):
            if np.any(a.bounds[1] < b.bounds[0]) or np.any(b.bounds[1] < a.bounds[0]): continue
            i = I(a, b); v += abs(i.volume) if len(i.faces) else 0.0
    return v
PREVISTO = {('Corona_hombro', 'Eje_Parte_1'), ('Corona_codo', 'Eje_Parte_2'),                # corona en los planos del eje
            ('motor_hombro', 'Pinon_hombro'), ('motor_codo', 'Pinon_codo'), ('motor_base', 'Pieza_Eje_Giro_Base')}
ALL = dict(P); ALL.update({f'motor_{k}': trimesh.util.concatenate(list(v.values())) for k, v in MOT.items()})
ALLB = {k: (list(MOT[k[6:]].values()) if k.startswith('motor_') else [v]) for k, v in ALL.items()}
print('Interferencias (> 1 mm3):')
n = 0
for a, b in itertools.combinations(ALL, 2):
    v = sum(overlap(x, y) for x in ALLB[a] for y in ALLB[b])
    if v > 1.0:
        prev = (a, b) in PREVISTO or (b, a) in PREVISTO; n += not prev
        print(f'  {a} / {b}: {v:.1f} mm3' + ('  (ajuste previsto)' if prev else '  <-- REVISAR'))
print('interferencias no previstas:', n)
base_back = trimesh.util.concatenate(list(MOT['base'].values())).bounds[0][1]
print(f'conector del motor de la base a {base_back - P["Base_suplemento_15mm"].bounds[0][1]:.1f} mm de la mesa')

# ---------- recorrido del hombro (opcional) ----------
if '--barrido' in sys.argv:
    fijo = ['Shield_1_placa', 'Shield_1_separadores_x4', 'Paleta_1', 'Paleta_2', 'BASE_TAPA_SUP_cuerpo', 'BASE_TAPA_INF']
    S = [P[k] for k in fijo] + list(MOT['hombro'].values())
    mov = [P[k] for k in ('Brazo_Parte_1_1', 'Brazo_Parte_1.1', 'Shield_2_placa')]; mc = list(MOT['codo'].values())
    for ang in range(-130, 131, 10):
        T = trimesh.transformations.rotation_matrix(np.radians(ang), [1, 0, 0], [0, 75, 0])
        hit_b = any(overlap(m.copy().apply_transform(T), s) > 0.5 for m in mov for s in S)
        hit_m = any(overlap(m.copy().apply_transform(T), s) > 0.5 for m in mc for s in S)
        print(f'  hombro {ang:+4d}°: brazo {"choca" if hit_b else "libre"}, motor del codo {"choca" if hit_m else "libre"}')

# ---------- vistas ----------
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
IMG = os.path.join(ENS, 'imagenes'); os.makedirs(IMG, exist_ok=True)
GRUPOS = [(('BASE_TAPA', 'Base_', 'Pieza'), '#9aa3ad'), (('Brazo_Parte', 'Paleta', 'Eje_', 'Sujetador'), '#c9b18a'),
          (('Shield', ), '#7f9cc0'), (('Corona', 'Pinon'), '#d68b4b'), (('Gripper', ), '#8fbf7f')]
def color(n):
    for keys, c in GRUPOS:
        if any(n.startswith(k) for k in keys): return c
    return '#bbbbbb'
def render(path, elev, azim):
    """Vista sombreada; todos los triángulos en una sola colección para que se ordenen bien por profundidad."""
    fig = plt.figure(figsize=(9, 10)); ax = fig.add_subplot(111, projection='3d'); light = np.array([0.4, 0.45, 0.8]); light /= np.linalg.norm(light)
    tris, cols = [], []
    for nm, m in list(P.items()) + [('motor', mot_all)]:
        v = m.vertices[:, [0, 2, 1]] * [1, -1, 1]; tri = v[m.faces]; nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12; sh = 0.45 + 0.55 * np.abs(nrm @ light)
        base = np.array(matplotlib.colors.to_rgb('#3a3a3a' if nm == 'motor' else color(nm)))
        tris.append(tri); cols.append(np.clip(base * sh[:, None], 0, 1))
    ax.add_collection3d(Poly3DCollection(np.vstack(tris), facecolors=np.vstack(cols), linewidths=0))
    allv = np.vstack([m.vertices for m in P.values()])[:, [0, 2, 1]] * [1, -1, 1]; c = (allv.min(0) + allv.max(0)) / 2; r = np.ptp(allv, 0).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r); ax.set_box_aspect([1, 1, 1])
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); plt.savefig(path, dpi=110, bbox_inches='tight'); plt.close(fig)
render(os.path.join(IMG, 'brazo_iso.png'), 20, -55)
render(os.path.join(IMG, 'brazo_lateral.png'), 5, 0)
print('vistas en ENSAMBLAJE/imagenes')
