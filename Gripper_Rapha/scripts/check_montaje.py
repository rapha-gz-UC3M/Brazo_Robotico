"""Comprueba el montaje: colisiones entre todas las piezas (antebrazo de Vasil + acople + gripper)
y holguras de las superficies de apoyo.  Uso: python check_montaje.py <carpeta acople> <placaA.stl> <placaB.stl>"""
import trimesh, numpy as np, glob, os, itertools, sys
from trimesh.proximity import closest_point
B, FA, FB = sys.argv[1:4]
P = {'Parte_2_1_Vasil': trimesh.load(FA), 'Parte_2.2_4_Vasil': trimesh.load(FB)}
for n in ('acople_punta_vasil_x1.5', 'casquillo_punta_x1.5', 'contraplaca_acople_x1.5'):
    P[n.replace('_x1.5', '')] = trimesh.load(os.path.join(B, n + '.stl'))
for f in sorted(glob.glob(os.path.join(B, 'ASM_*.stl'))): P[os.path.basename(f)[4:-4]] = trimesh.load(f)
bad = 0
for a, b in itertools.combinations(P, 2):
    if not (np.all(P[a].bounds[0] < P[b].bounds[1]) and np.all(P[b].bounds[0] < P[a].bounds[1])): continue
    i = trimesh.boolean.intersection([P[a], P[b]], engine='manifold'); v = abs(i.volume) if len(i.faces) else 0
    if v > 0.5: print(f'COLISIÓN {a} x {b}: {v:.1f} mm3'); bad += 1
for a, b in [('acople_punta_vasil', 'Parte_2_1_Vasil'), ('acople_punta_vasil', 'Parte_2.2_4_Vasil'),
             ('casquillo_punta', 'Parte_2_1_Vasil'), ('casquillo_punta', 'Parte_2.2_4_Vasil'),
             ('contraplaca_acople', 'Parte_2_1_Vasil'), ('acople_punta_vasil', 'base_plate')]:
    _, d, _ = closest_point(P[b], P[a].sample(4000)); print(f'distancia mínima {a} - {b}: {d.min():.2f} mm')
print('colisiones:', bad)
