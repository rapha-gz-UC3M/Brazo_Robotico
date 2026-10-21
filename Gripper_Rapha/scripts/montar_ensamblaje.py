"""Monta el brazo completo (base de Ignacio + brazo de Vasil + gripper de Rapha) a partir de los STL del repositorio.

Lee (solo lectura):
  ../Base_Ignacio/*.stl
  ../Arm_Vasil/Brazo_modificado_STL/*.stl
  comprobacion/ASM_*.stl              (gripper y acople, ya colocados respecto a Brazo Parte 2_1)
y las colocaciones de ensamblaje_completo/transformaciones.json.

Escribe en ensamblaje_completo/:
  ensamblaje_completo.stl             todas las piezas en un único STL (mm)
  motores_JGB37_referencia.stl        dos motores JGB37-520 aproximados (no se imprimen; solo para ver el hueco)
  piezas_colocadas/<pieza>.stl        cada pieza por separado, ya colocada (para importarlas una a una)

Marco W: origen en el eje de giro de la base, a la altura del escalón de BASE_TAPA_INF donde apoya
BASE_TAPA_SUP; Y hacia arriba; X = eje del hombro y del codo. Pose: la del brazo BR3E original, base a 0°.

Los STL que exporta Solid Edge por defecto están en pulgadas: se detecta y se pasa a mm.

Uso (desde Gripper_Rapha):  python scripts/montar_ensamblaje.py [--comprobar]
"""
import trimesh, numpy as np, json, os, sys, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); GR = os.path.dirname(HERE); REPO = os.path.dirname(GR)
OUT = os.path.join(GR, 'ensamblaje_completo'); PZ = os.path.join(OUT, 'piezas_colocadas'); os.makedirs(PZ, exist_ok=True)
cfg = json.load(open(os.path.join(OUT, 'transformaciones.json')))['piezas']

def load_mm(path):
    m = trimesh.load(path)
    if m.extents.max() < 20: m.apply_scale(25.4)          # exportado en pulgadas
    return m

parts = {}
for name, c in cfg.items():
    src = os.path.join(GR, c['src'][len('Gripper_Rapha/'):]) if c['src'].startswith('Gripper_Rapha/') else os.path.join(REPO, c['src'])
    if not os.path.exists(src): print('FALTA', c['src']); continue
    m = load_mm(src); m.apply_transform(np.array(c['matrix'])); parts[name] = m
    m.export(os.path.join(PZ, name + '.stl'))

# motores JGB37-520 aproximados: reductora Ø37 x 22, motor Ø35,5 x 30, eje Ø6 x 15 descentrado
def jgb37(axis, ctr_off, face):
    axis = np.asarray(axis, float); face = np.asarray(face, float); ctr = face + np.asarray(ctr_off, float)
    R = trimesh.geometry.align_vectors([0, 0, 1.0], axis)
    def cyl(r, h, p0):
        c = trimesh.creation.cylinder(radius=r, height=h, sections=64); c.apply_transform(R); c.apply_translation(p0 - axis * h / 2); return c
    sh = trimesh.creation.cylinder(radius=3, height=15, sections=32); sh.apply_transform(R); sh.apply_translation(face + axis * 7.5)
    return trimesh.util.concatenate([sh, cyl(18.5, 22, ctr), cyl(17.75, 30, ctr - axis * 22)])
motors = {'REF_motor_JGB37_hombro': jgb37([1, 0, 0], [0, -8.1, 0.3], [-43.6, 52.5, 55.6]),   # en la cuna de Shield 1, mueve el piñón
          'REF_motor_JGB37_base': jgb37([0, 1, 0], [0, 0, 7.0], [0, -21.75, 0])}             # bajo la placa central de BASE_TAPA_INF
for k, m in motors.items(): m.export(os.path.join(PZ, k + '.stl'))

trimesh.util.concatenate(list(parts.values())).export(os.path.join(OUT, 'ensamblaje_completo.stl'))
trimesh.util.concatenate(list(motors.values())).export(os.path.join(OUT, 'motores_JGB37_referencia.stl'))
allm = trimesh.util.concatenate(list(parts.values()))
print(f'{len(parts)} piezas -> ensamblaje_completo.stl  (límites en mm: {np.round(allm.bounds, 1).tolist()})')

if '--comprobar' in sys.argv:
    # contactos que son el ajuste previsto (eje en D dentro de un agujero en D, clip a presión, etc.)
    esperado = {frozenset(p) for p in [('REF_motor_JGB37_hombro', 'Vasil_Pinon_hombro'), ('REF_motor_JGB37_base', 'Ignacio_Pieza_Eje_Giro_Base')]}
    allp = {**parts, **motors}; n = 0
    for a, b in itertools.combinations(allp, 2):
        A, B = allp[a], allp[b]
        if np.any(A.bounds[1] < B.bounds[0]) or np.any(B.bounds[1] < A.bounds[0]): continue
        i = trimesh.boolean.intersection([A, B], engine='manifold'); v = abs(i.volume) if len(i.faces) else 0.0
        if v > 0.5:
            n += 1; tag = '(ajuste previsto: eje de motor en agujero en D)' if frozenset((a, b)) in esperado else ''
            print(f'  interferencia {a} / {b}: {v:.1f} mm3 {tag}')
    print('pares con interferencia > 0,5 mm3:', n)
