"""Prepara TODAS las piezas del brazo para imprimir, en mm y bien orientadas (no modifica nada fuera de Gripper_Rapha).

Lee (solo lectura):
  ../Arm_Vasil/Brazo_modificado_STL/*.stl     (Solid Edge, en pulgadas)
  ../Base_Ignacio/*.stl                       (Solid Edge, en pulgadas)
  imprimir/*.stl                              (gripper, ya en mm)

Escribe:
  piezas_mm/Arm_Vasil/, piezas_mm/Base_Ignacio/
      Copia exacta de cada STL pasada a mm (x25,4), con el mismo nombre y las mismas coordenadas.
  imprimir_brazo/1_base_Ignacio/, 2_brazo_Vasil/, 3_gripper_Rapha/
      Lo que hay que imprimir, en mm, apoyado en la cama (z=0) en la mejor orientación, con los cambios
      para que se pueda imprimir bien:
        - BASE_TAPA_SUP: cuerpo + pestaña pegada        (ver build_base_sup_imprimible.py)
        - Shield 1 y Shield 2: placa + separadores sueltos (ver build_shields_imprimibles.py)
        - Piñón: agujero en D a 6,15 x 5,65 (estaba a 6,0 x 5,5 exactos, sin holgura para el eje del JGB37)
        - Eje Parte 2: el agujero del extremo (motor del codo) pasa de redondo Ø6 a D 6,15 x 5,65, para que
          el eje en D del JGB37 arrastre
      No se incluye Eje Parte 3 (en la punta va el casquillo del gripper).

Uso (desde Gripper_Rapha):  python scripts/preparar_impresion.py
"""
import os, sys, glob, shutil, subprocess, tempfile, numpy as np, trimesh
HERE = os.path.dirname(os.path.abspath(__file__)); GR = os.path.dirname(HERE); REPO = os.path.dirname(GR)
VAS = os.path.join(REPO, 'Arm_Vasil', 'Brazo_modificado_STL'); IGN = os.path.join(REPO, 'Base_Ignacio')
MM = os.path.join(GR, 'piezas_mm'); PR = os.path.join(GR, 'imprimir_brazo')
D = lambda a, *b: trimesh.boolean.difference([a, *b], engine='manifold')
U = lambda *a: trimesh.boolean.union(list(a), engine='manifold')

def load_mm(p):
    m = trimesh.load(p)
    if m.extents.max() < 20: m.apply_scale(25.4)                  # exportado en pulgadas
    return m

# ---------- 1. copias exactas en mm ----------
for src, dst in ((VAS, os.path.join(MM, 'Arm_Vasil')), (IGN, os.path.join(MM, 'Base_Ignacio'))):
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, '*.stl'))):
        load_mm(f).export(os.path.join(dst, os.path.basename(f)))
print('piezas_mm: hecho')

# ---------- utilidades ----------
def orient(m, up):
    """Gira la pieza para que 'up' (eje propio) apunte a +Z y la apoya en z=0, centrada en XY."""
    m = m.copy(); m.apply_transform(trimesh.geometry.align_vectors(np.asarray(up, float), [0, 0, 1.0]))
    m.apply_translation([-m.bounds[:, 0].mean(), -m.bounds[:, 1].mean(), -m.bounds[0][2]]); return m
def copies(m, n, gap=8.0):
    out = []
    for i in range(n):
        c = m.copy(); c.apply_translation([i * (m.extents[0] + gap), 0, 0]); out.append(c)
    r = trimesh.util.concatenate(out); r.apply_translation([-r.bounds[:, 0].mean(), 0, 0]); return r
def d_prism(axis, center, flat_dir, t0, t1, dia=6.15, across=5.65, sec=96):
    """Prisma en D (Ø dia, plano a 'across' del lado opuesto) a lo largo de 'axis' entre t0 y t1."""
    r = dia / 2; c = trimesh.creation.cylinder(radius=r, height=t1 - t0, sections=sec)
    cut = trimesh.creation.box(extents=[4 * r, 4 * r, (t1 - t0) + 2])         # quita lo que pasa del plano
    cut.apply_translation([0, (across - r) + 2 * r, 0]); dprism = D(c, cut)   # plano en +y local, a across-r del centro
    a = np.asarray(axis, float); f = np.asarray(flat_dir, float); f -= a * (f @ a); f /= np.linalg.norm(f)
    R = np.eye(4); R[:3, :3] = np.c_[np.cross(f, a), f, a]                      # local x, y(=plano), z(=eje)
    dprism.apply_transform(R); dprism.apply_translation(np.asarray(center, float) + a * (t0 + t1) / 2); return dprism
def hole_flat_dir(m, origin, normal):
    """Dirección (perpendicular al eje) del punto del agujero más cercano al eje = normal del plano de la D."""
    s = m.section(plane_origin=origin, plane_normal=normal)
    best = None
    for e in s.discrete:
        p = np.array(e) - origin; r = np.linalg.norm(p - np.outer(p @ normal, normal), axis=1)
        if r.max() < 4.5 and (best is None or len(p) > len(best)): best = p
    p = best - np.outer(best @ normal, normal); r = np.linalg.norm(p, axis=1); return p[r.argmin()] / r.min(), r.min(), r.max()

out = {k: os.path.join(PR, k) for k in ('1_base_Ignacio', '2_brazo_Vasil', '3_gripper_Rapha')}
for d in out.values(): os.makedirs(d, exist_ok=True)
def save(folder, name, m): m.export(os.path.join(out[folder], name + '.stl')); print(f'  {folder}/{name}.stl  {np.round(m.extents, 1).tolist()} mm')

# ---------- 2. base (Ignacio) ----------
save('1_base_Ignacio', 'BASE_TAPA_INF', orient(load_mm(os.path.join(IGN, 'BASE_TAPA_INF.stl')), [0, 1, 0]))
save('1_base_Ignacio', 'Pieza_Eje_Giro_Base', orient(load_mm(os.path.join(IGN, 'Pieza_Eje_Giro_Base.stl')), [0, 1, 0]))
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.executable, os.path.join(HERE, 'build_base_sup_imprimible.py'), os.path.join(IGN, 'BASE_TAPA_SUP.stl'), tmp], check=True, stdout=subprocess.DEVNULL)
    for n in ('BASE_TAPA_SUP_imprimible', 'BASE_TAPA_SUP_pestana'): save('1_base_Ignacio', n, trimesh.load(os.path.join(tmp, n + '.stl')))
    # ---------- 3. brazo (Vasil) ----------
    subprocess.run([sys.executable, os.path.join(HERE, 'build_shields_imprimibles.py'), VAS, tmp], check=True, stdout=subprocess.DEVNULL)
    for n in ('Shield_1_imprimible', 'Shield_1_separadores_x4', 'Shield_2_imprimible', 'Shield_2_separadores_x3'):
        save('2_brazo_Vasil', n, trimesh.load(os.path.join(tmp, n + '.stl')))
V = lambda n: load_mm(os.path.join(VAS, n + '.stl'))
for name, up in [('Brazo Parte 1_1', [0, 0, 1]), ('Brazo Parte 1.1 2.0_1', [0, 0, 1]), ('Brazo Parte 2_1', [0, 0, 1]),
                 ('Brazo Parte 2.2_4', [0, 0, -1]), ('Base Tapa Superior - Paleta 1 - 2.0_1', [1, 0, 0]),
                 ('Base Tapa Superior - Paleta 2 - 2.0_1', [1, 0, 0]), ('Corona - 30 dientes - modulo 2_1', [1, 0, 0]),
                 ('Eje Parte 1 - 2.0_1', [0, 0, 1])]:
    save('2_brazo_Vasil', name.replace(' - ', '_').replace(' ', '_'), orient(V(name), up))
save('2_brazo_Vasil', 'Sujetador_de_eje_x2', copies(orient(V('Sujetador de eje_2'), [0, 0, 1]), 2))

# piñón: agujero en D 6,0 x 5,5 -> 6,15 x 5,65 (eje x, centro (0,0))
pn = V('Piñon - 10 dientes - modulo 2_1')
f, rmin, rmax = hole_flat_dir(pn, np.array([6.75, 0, 0]), np.array([1.0, 0, 0]))
print('  piñón: agujero original Ø%.2f, plano a %.2f del centro' % (2 * rmax, rmin + rmax))
pn = D(pn, d_prism([1, 0, 0], [0, 0, 0], f, pn.bounds[0][0] - 1, pn.bounds[1][0] + 1))
save('2_brazo_Vasil', 'Pinon_10_dientes_modulo_3_agujero_D_6.15', orient(pn, [1, 0, 0]))

# eje 2: agujero del extremo (z de ~7 a 22,5) redondo Ø6 -> D 6,15 x 5,65, con el plano hacia la pared más gruesa
e2 = V('Eje Parte 2 - 2.0_1'); top = e2.bounds[1][2]
s = e2.section(plane_origin=[0, 0, top - 3], plane_normal=[0, 0, 1])
outer = max((np.array(e)[:, :2] for e in s.discrete), key=lambda p: np.ptp(p[:, 0]) * np.ptp(p[:, 1]))
w, v = np.linalg.eigh(np.cov((outer - outer.mean(0)).T)); thin = np.r_[v[:, 0], 0]       # dirección del lado estrecho (8,2 mm)
z = top - 0.2                                                    # fondo del agujero original (tiene un nervio central,
while not e2.contains([[1.8, 0, z], [0, 1.8, z]]).all(): z -= 0.1  #  así que se mira a 1,8 mm del eje en dos direcciones)
bottom = z + 0.05
plug = trimesh.creation.cylinder(radius=3.3, height=top - bottom - 0.01, sections=96); plug.apply_translation([0, 0, (top + bottom) / 2])
core = trimesh.boolean.intersection([plug, trimesh.convex.convex_hull(e2)], engine='manifold')
e2 = U(e2, core)                                                  # tapa el agujero redondo
e2 = D(e2, d_prism([0, 0, 1], [0, 0, 0], -thin, bottom, top + 1))  # y lo vuelve a abrir en D
print('  eje 2: agujero del extremo en D 6,15 x 5,65 de %.1f mm de fondo' % (top - bottom))
save('2_brazo_Vasil', 'Eje_Parte_2_2.0_agujero_D_6.15', orient(e2, [0, 0, 1]))

# ---------- 4. gripper (Rapha) ----------
G = lambda n: trimesh.load(os.path.join(GR, 'imprimir', n + '_x1.5.stl'))
for name, up in [('acople_punta_vasil', [-1, 0, 0]), ('casquillo_punta', [0, 0, -1]), ('contraplaca_acople', [0, 0, 1]),
                 ('base_plate', [0, 1, 0]), ('gear_left', [0, 1, 0]), ('gear_right', [0, 1, 0]),
                 ('arm_left', [0, 1, 0]), ('arm_right', [0, 1, 0]), ('jaw_left', [0, -1, 0]), ('jaw_right', [0, -1, 0])]:
    save('3_gripper_Rapha', name + '_x1.5', orient(G(name), up))
print('imprimir_brazo: hecho')
