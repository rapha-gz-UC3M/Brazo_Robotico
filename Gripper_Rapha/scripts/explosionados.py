"""Vistas explosionadas de cada subconjunto del brazo (PyVista + matplotlib).  uso: python explode.py OUT [1 2 ...]"""
import os, sys, json, textwrap
import numpy as np, trimesh, pyvista as pv, vtk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch

GR = '/mnt/user-data/outputs/Gripper_Rapha'; COL = GR + '/ENSAMBLAJE/piezas_colocadas/'
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
QUE = sys.argv[2:] or ['all']
P = {f[:-4]: trimesh.load(COL + f) for f in os.listdir(COL) if f.endswith('.stl')}

# ---------------- motores JGB37 (mismo modelo que montar_ensamblaje.py) ----------------
TF = json.load(open(GR + '/ENSAMBLAJE/transformaciones.json'))['piezas']; M2 = np.array(TF['Vasil_Shield_2']['matrix'])
def cyl(r, p0, p1, sec=64):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); a = p1 - p0; h = np.linalg.norm(a)
    c = trimesh.creation.cylinder(radius=r, height=h, sections=sec)
    c.apply_transform(trimesh.geometry.align_vectors([0, 0, 1.0], a / h)); c.apply_translation((p0 + p1) / 2); return c
def jgb(face, axis, toward, L=26.5):
    a = np.asarray(axis, float); a /= np.linalg.norm(a); t = np.asarray(toward, float); t -= a * (t @ a); t /= np.linalg.norm(t)
    f = np.asarray(face, float); c = f + 7 * t; e = L + 22.7
    return trimesh.util.concatenate([cyl(18.5, c, c - a * L), cyl(16.5, c - a * L, c - a * e), cyl(16, c - a * e, c - a * (e + 11.75)),
                                     cyl(6, f, f + a * 6), cyl(2.9, f + a * 6, f + a * 15.5, 32)])
P['motor_hombro'] = jgb([-43.6, 52.5, 55.6], [1, 0, 0], [0, -8.1, 0.3])
P['motor_codo'] = jgb((M2 @ [0, 45, 0, 1])[:3], [1, 0, 0], -M2[:3, 1])
P['motor_base'] = jgb([0, -21.3, 0], [0, 1, 0], [0, 0, 1])
GRIP = [k for k in P if k.startswith('Gripper_')]

X = np.array([1.0, 0, 0]); Y = np.array([0, 1.0, 0]); Z = np.array([0, 0, 1.0])
N = np.array([0, 0.77, 0.638]); N /= np.linalg.norm(N)          # normal de la placa del gripper
F = np.array([0, -96.0, 115.5]); F /= np.linalg.norm(F)
T = np.cross(X, N)                                                # perpendicular a N y a X          # dirección de la punta del antebrazo

PAL = ['#e8833a', '#3d7fd9', '#33a36a', '#d1495b', '#8c62c9', '#e0b01c', '#1f9fb0', '#c2618f', '#7a9c2e', '#5b6bbf']
MOTOR = '#2f3237'; CTX = '#d9dce0'

def pvmesh(m):
    return pv.PolyData(m.vertices.copy(), np.hstack([np.full((len(m.faces), 1), 3), m.faces]).astype(np.int64))

def clipbox(m, lo, hi):
    for i in range(3):
        for s, v in ((1, lo[i]), (-1, hi[i])):
            if m is None or len(m.faces) == 0: return None
            n = np.zeros(3); n[i] = s; o = np.zeros(3); o[i] = v; m = m.slice_plane(o, n, cap=True)
    return m

def a_pantalla(ren, p, H):
    c = vtk.vtkCoordinate(); c.SetCoordinateSystemToWorld(); c.SetValue(*p)
    x, y = c.GetComputedDoubleDisplayValue(ren); return np.array([x, H - y])

def lamina(nombre, titulo, sub, piezas, vista, ctx=(), focus=None, up=Y, zoom=1.0, W=1700, H=1350, globos=None):
    """piezas: [(malla | [mallas], nombre, nota, desplazamiento, color)]. vista: vector desde el objeto hacia la cámara."""
    pl = pv.Plotter(off_screen=True, window_size=(W, H), lighting='none'); pl.set_background('white')
    pl.enable_parallel_projection(); pl.enable_anti_aliasing('ssaa')
    v = np.asarray(vista, float); v /= np.linalg.norm(v)
    for d, it in ((v + 0.6 * np.asarray(up) + 0.4 * np.cross(up, v), 0.75), (v - 0.5 * np.cross(up, v), 0.35), (-v + up, 0.25)):
        l = pv.Light(light_type='scene light', intensity=it); l.position = tuple(d * 2000); l.focal_point = (0, 0, 0); pl.add_light(l)
    lit = dict(smooth_shading=True, split_sharp_edges=True, feature_angle=35, ambient=0.28, diffuse=0.75, specular=0.18, specular_power=20)
    if focus is not None:
        ctx = [clipbox(m, np.asarray(focus[0], float), np.asarray(focus[1], float)) for m in ctx]
    for m in ctx:
        if m is not None and len(m.faces): pl.add_mesh(pvmesh(m), color=CTX, **lit)
    anclas, todas = [], []
    for i, (ms, nom, nota, off, col) in enumerate(piezas):
        ms = ms if isinstance(ms, list) else [ms]; off = np.asarray(off, float); col = col or PAL[i % len(PAL)]
        for m in ms:
            mm = m.copy(); mm.apply_translation(off); pl.add_mesh(pvmesh(mm), color=col, **lit); todas.append(mm.vertices)
        c0 = np.mean([m.bounds.mean(0) for m in ms], 0)
        if np.linalg.norm(off) > 1:                                   # línea de montaje discontinua
            a, b = c0, c0 + off; L = np.linalg.norm(b - a); k = int(L // 9)
            for j in range(0, k, 2):
                pl.add_mesh(pv.Line(a + (b - a) * j / k, a + (b - a) * min(j + 1, k) / k), color='#8a8f96', line_width=2.2)
        vv = np.vstack([m.vertices for m in ms]) + off                # ancla: vértice más cercano al centro
        anclas.append((vv[np.argmin(np.linalg.norm(vv - (c0 + off), axis=1))], nom, nota, col))
    allv = np.vstack(todas + [m.vertices for m in ctx if m is not None and len(m.faces)])
    cen = (allv.min(0) + allv.max(0)) / 2
    pl.camera.position = tuple(cen + v * 3000); pl.camera.focal_point = tuple(cen); pl.camera.up = tuple(up)
    pl.reset_camera(); pl.camera.zoom(zoom)
    pl.render(); ren = pl.renderer
    img = pl.screenshot(return_img=True); pts = [a_pantalla(ren, a[0], H) for a in anclas]; pl.close()
    ys, xs = np.where((img < 245).any(axis=2)); m = 130                 # recortar el blanco sobrante
    x0, x1 = max(xs.min() - m, 0), min(xs.max() + m, W); y0, y1 = max(ys.min() - m, 0), min(ys.max() + m, H)
    img = img[y0:y1, x0:x1]; pts = [p - [x0, y0] for p in pts]; W, H = x1 - x0, y1 - y0
    R = 0.021 * max(W, H); D = 0.075 * max(W, H)

    # ---------------- composición: dibujo + lista de piezas ----------------
    fig = plt.figure(figsize=(17, 9.6), dpi=110); fig.patch.set_facecolor('white')
    ax = fig.add_axes([0.01, 0.01, 0.63, 0.86]); ax.imshow(img); ax.set_axis_off()
    fig.text(0.025, 0.955, titulo, fontsize=24, fontweight='bold', color='#1b1d21', va='center')
    fig.text(0.025, 0.912, sub, fontsize=13, color='#6b7079', va='center')
    cimg = np.array([W / 2, H / 2])
    usadas = []
    for k, (p, (a, nom, nota, col)) in enumerate(zip(pts, anclas), 1):
        d = p - cimg; d = d / (np.linalg.norm(d) + 1e-9) if np.linalg.norm(d) > 30 else np.array([0.7, -0.7])
        q = p + d * D if not globos or k not in globos else p + np.asarray(globos[k], float) * D / 95
        for _ in range(30):                                           # separar globos que se pisan
            cerca = [u for u in usadas if np.linalg.norm(u - q) < 2.4 * R]
            if not cerca: break
            q = q + (q - cerca[0]) / (np.linalg.norm(q - cerca[0]) + 1e-9) * R + np.array([0, 0.3 * R])
        q = np.clip(q, R + 4, [W - R - 4, H - R - 4]); usadas.append(q)
        ax.plot([p[0], q[0]], [p[1], q[1]], color='#4a4f57', lw=1.3, zorder=5)
        ax.plot(*p, 'o', color='#4a4f57', ms=4, zorder=6)
        ax.add_patch(Circle(q, R, fc=col, ec='white', lw=2.5, zorder=7))
        ax.text(*q, str(k), color='white', fontsize=15, fontweight='bold', ha='center', va='center', zorder=8)
    lx = 0.675; y = 0.865
    fig.text(lx, y + 0.04, 'Piezas', fontsize=15, fontweight='bold', color='#1b1d21')
    fig.add_artist(plt.Line2D([lx, 0.98], [y + 0.025, y + 0.025], color='#d0d3d8', lw=1))
    for k, (a, nom, nota, col) in enumerate(anclas, 1):
        fig.text(lx + 0.012, y, str(k), fontsize=12, fontweight='bold', color='white', ha='center', va='center',
                 bbox=dict(boxstyle='circle,pad=0.35', fc=col, ec='none'))
        fig.text(lx + 0.032, y, nom, fontsize=12.5, fontweight='bold', color='#1b1d21', va='center')
        y -= 0.033
        if nota:
            lineas = textwrap.wrap(nota, 54)
            fig.text(lx + 0.032, y + 0.012, '\n'.join(lineas), fontsize=10.5, color='#555a62', va='top', linespacing=1.35)
            y -= 0.0245 * len(lineas) + 0.008
        y -= 0.006
    ruta = os.path.join(OUT, nombre + '.png'); fig.savefig(ruta, facecolor='white'); plt.close(fig); print('ok', ruta, 'lista hasta y =', round(y, 3))

Q = lambda k: k in QUE or 'all' in QUE
BASE = [P['BASE_TAPA_INF'], P['Base_suplemento_15mm'], P['BASE_TAPA_SUP_cuerpo'], P['BASE_TAPA_SUP_pestana'], P['Pieza_Eje_Giro_Base'], P['motor_base']]
GRIPPER = [P[k] for k in GRIP if k not in ('Gripper_acople_punta', 'Gripper_casquillo_punta', 'Gripper_contraplaca_acople')]
FORE = [P['Brazo_Parte_2_1'], P['Brazo_Parte_2.2_4'], P['Eje_Parte_2']] + [P[k] for k in GRIP]
UPPER = [P['Brazo_Parte_1_1'], P['Eje_Parte_1'], P['Brazo_Parte_1.1'], P['Sujetador_codo']]
CODO = [P['Corona_codo'], P['Shield_2_placa'], P['Shield_2_separadores_x3'], P['motor_codo'], P['Pinon_codo']]
HOMBRO = [P['Paleta_1'], P['Paleta_2'], P['Sujetador_hombro'], P['Corona_hombro'], P['Shield_1_placa'],
          P['Shield_1_separadores_x4'], P['motor_hombro'], P['Pinon_hombro']]
SUB = 'Vista explosionada · las líneas discontinuas indican dónde va cada pieza'

if Q('1'):
    lamina('explosionado_1_base', '1 · Base giratoria', SUB, [
        (P['Base_suplemento_15mm'], 'Base_suplemento_15mm', 'Debajo de BASE_TAPA_INF: deja sitio al encoder del motor. Pegado o con 4 tirafondos al tablero', -150 * Y, None),
        (P['motor_base'], 'Motor de la base (JGB37-520B)', 'Por debajo del techo de la torre, eje hacia arriba y cables hacia abajo. 6 × M3×8 con arandela desde arriba', -105 * Y, MOTOR),
        (P['BASE_TAPA_INF'], 'BASE_TAPA_INF', 'Lleva los 2 finales de carrera en sus repisas interiores (4 × M2×16 + tuerca)', 0 * Y, None),
        (P['Pieza_Eje_Giro_Base'], 'Pieza_Eje_Giro_Base', 'En el eje del motor: prisionero M3×6 contra el plano de la D', 70 * Y, None),
        (P['BASE_TAPA_SUP_cuerpo'], 'BASE_TAPA_SUP', 'Apoya sobre INF y gira. 1 × M3×12 desde arriba por el agujero central', 140 * Y, None),
        (P['BASE_TAPA_SUP_pestana'], 'Pestaña de los finales de carrera', 'Se pega bajo BASE_TAPA_SUP; acciona los finales de carrera', 140 * Y + 55 * X, None)],
        vista=[0.75, 0.42, 1.0], zoom=1.0)

if Q('2'):
    lamina('explosionado_2_gripper', '2 · Pinza (gripper)', SUB, [
        (P['Gripper_servo_MG90S_aprox'], 'Servo MG90S', 'Centrado a 90° antes de montar. Con sus 2 tornillos a la placa base', -55 * N, MOTOR),
        (P['Gripper_base_plate'], 'base_plate', '', 0 * N, None),
        (P['Gripper_gear_right'], 'gear_right', 'Al estriado del servo (tornillo del servo)', 45 * N + 25 * X, None),
        (P['Gripper_gear_left'], 'gear_left', 'Pivote: M3×20 + autoblocante, sin frenar el giro', 45 * N - 25 * X, None),
        (P['Gripper_arm_right'], 'arm_right (biela)', 'M3×20 + autoblocante', 85 * N + 25 * X, None),
        (P['Gripper_arm_left'], 'arm_left (biela)', 'M3×20 + autoblocante', 85 * N - 25 * X, None),
        (P['Gripper_jaw_right'], 'jaw_right (mordaza)', '2 × M3×20 + autoblocante, al engranaje y a la biela', 130 * N + 25 * X, None),
        (P['Gripper_jaw_left'], 'jaw_left (mordaza)', '2 × M3×20 + autoblocante', 130 * N - 25 * X, None)],
        vista=T + 0.55 * X + 0.45 * N, up=N, zoom=1.0)

if Q('3'):
    lamina('explosionado_3_antebrazo', '3 · Antebrazo y punta', SUB, [
        (P['Eje_Parte_2'], 'Eje_Parte_2 (codo)', 'Entre las dos placas; el extremo largo sale por 2.2_4', 0 * X, None),
        (P['Brazo_Parte_2_1'], 'Brazo_Parte_2_1', '', 65 * X, None),
        (P['Brazo_Parte_2.2_4'], 'Brazo_Parte_2.2_4', '', -65 * X, None),
        ([P['Gripper_acople_punta']] + GRIPPER, 'Acople + pinza montada (lámina 2)', 'Se desliza desde la punta hasta el tope. Pinza al acople: 4 × M3×16 + tuerca. Orejetas de 2.2_4 a las alas: 2 × M5×30 + tuerca', 120 * F, '#1f9fb0'),
        (P['Gripper_casquillo_punta'], 'casquillo_punta', 'Por fuera de 2.2_4. Eje de la punta: 1 × M5×40 + arandela', -120 * X, None),
        (P['Gripper_contraplaca_acople'], 'contraplaca_acople', 'Por fuera de 2_1, con la tuerca M5 en su alojamiento', 120 * X, None)],
        vista=[1.0, 0.55, 0.55], zoom=1.0)

if Q('4'):
    lamina('explosionado_4_brazo', '4 · Brazo (tramo del hombro al codo)', SUB, [
        (P['Brazo_Parte_1_1'], 'Brazo_Parte_1_1', '', 110 * X, None),
        (P['Brazo_Parte_1.1'], 'Brazo_Parte_1.1', 'Lado del motor del codo (Shield 2 se atornilla aquí, lámina 5)', -110 * X, None),
        (P['Eje_Parte_1'], 'Eje_Parte_1 (hombro)', 'Atraviesa 1_1; luego entra en las paletas (lámina 6)', 210 * X, None),
        (P['Sujetador_codo'], 'Sujetador de eje (clip del codo)', 'A presión en Eje_Parte_2, por fuera de 1_1', 165 * X, None),
        (FORE, 'Antebrazo montado (lámina 3)', 'Su Eje_Parte_2 entra entre las placas 1_1 y 1.1', 0 * X, '#b9bec6')],
        vista=[0.75, 0.5, 1.0], zoom=1.0)

if Q('5'):
    ELBOW = [[-300, 120, -10], [80, 320, 140]]
    lamina('explosionado_5_codo', '5 · Codo: transmisión y motor', SUB, [
        (P['Corona_codo'], 'Corona de 30 dientes', 'En los planos de Eje_Parte_2', -45 * X, None),
        (P['Pinon_codo'], 'Piñón de 10 dientes', 'En el eje del motor, con el rebaje hacia el motor', -85 * X, None),
        (P['Shield_2_separadores_x3'], 'Shield_2_separadores ×3', 'Entre Shield 2 y Brazo_Parte_1.1', -120 * X, None),
        (P['Shield_2_placa'], 'Shield_2_placa', 'A 1.1: 2 × M5×30 cabeza baja (cabeza por dentro) + 1 × M6×30. Potenciómetro con brida en su semicasquillo', -165 * X, None),
        (P['motor_codo'], 'Motor del codo (JGB37-520B)', '6 × M3×6 avellanados, cabeza en la cara interior de Shield 2', -240 * X, MOTOR)],
        vista=[-1.0, 0.45, -0.6], ctx=FORE + UPPER, focus=ELBOW, zoom=1.0)

if Q('6'):
    SH = [[-360, -40, -80], [90, 170, 120]]
    lamina('explosionado_6_hombro', '6 · Hombro: paletas, transmisión y motor', SUB, [
        (P['Paleta_1'], 'Paleta_1', 'A la pared derecha de BASE_TAPA_SUP: 2 × M5×16 + arandela + tuerca', 55 * X, None),
        (P['Sujetador_hombro'], 'Sujetador de eje (clip del hombro)', 'A presión en Eje_Parte_1, por fuera de Paleta_1', 100 * X, None),
        (P['Paleta_2'], 'Paleta_2', 'Mete antes el M4×30 de arriba al revés (cabeza por dentro)', -45 * X, None),
        (P['Corona_hombro'], 'Corona de 30 dientes', 'En los planos de Eje_Parte_1', -85 * X, None),
        (P['Pinon_hombro'], 'Piñón de 10 dientes', 'En el eje del motor, con el rebaje hacia el motor', -120 * X, None),
        (P['Shield_1_separadores_x4'], 'Shield_1_separadores ×4', 'Entre Shield 1 y Paleta 2', -150 * X, None),
        (P['Shield_1_placa'], 'Shield_1_placa', '2 × M4×35 + 2 × M4×30 avellanados hasta Paleta 2 y SUP. Potenciómetro con brida en su semicasquillo', -195 * X, None),
        (P['motor_hombro'], 'Motor del hombro (JGB37-520B)', '6 × M3×6 avellanados, cabeza en la cara interior de Shield 1', -275 * X, MOTOR)],
        vista=[-1.0, 0.5, 0.75], ctx=BASE + UPPER + FORE + CODO, focus=SH, zoom=1.0)

if Q('0'):
    g = lambda *pre: [P[k] for k in P if k.startswith(pre)]
    lamina('explosionado_0_brazo_completo', 'Brazo completo por subconjuntos', 'Vista explosionada · cada color es una lámina', [
        (BASE, 'Base giratoria', 'Lámina 1', -110 * Y, '#9aa3ad'),
        ([P['Paleta_1'], P['Paleta_2'], P['Sujetador_hombro'], P['Corona_hombro']], 'Paletas y corona del hombro', 'Lámina 6', 0 * X, '#e8833a'),
        ([P['Shield_1_placa'], P['Shield_1_separadores_x4'], P['motor_hombro'], P['Pinon_hombro']], 'Motor del hombro con Shield 1', 'Lámina 6', -140 * X, '#3d7fd9'),
        (UPPER, 'Brazo', 'Lámina 4', 0 * X, '#c9b18a'),
        (CODO, 'Codo: corona, Shield 2 y motor', 'Lámina 5', -140 * X, '#8c62c9'),
        ([P['Brazo_Parte_2_1'], P['Brazo_Parte_2.2_4'], P['Eje_Parte_2'], P['Gripper_casquillo_punta'], P['Gripper_contraplaca_acople']], 'Antebrazo', 'Lámina 3', 0 * X, '#d1495b'),
        ([P['Gripper_acople_punta']] + GRIPPER, 'Pinza con su acople', 'Láminas 2 y 3', 110 * F, '#33a36a')],
        vista=[-1.0, 0.5, 0.9], zoom=1.0)
