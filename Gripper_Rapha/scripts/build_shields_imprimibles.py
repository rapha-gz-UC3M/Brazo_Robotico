"""Versión imprimible de Shield 1 y Shield 2 de Vasil (los originales no se tocan).

Problema: cada Shield tiene piezas a los dos lados de la placa (casquillos separadores por un lado y las cunas
del motor por el otro), así que no hay ninguna cara plana para apoyar en la cama.

Cambio: los casquillos separadores se imprimen aparte. Son tubos que van entre el Shield y la pieza de al lado
(Paleta 2 o Brazo Parte 1.1) y quedan apretados por el mismo tornillo que los atraviesa, así que no hace falta
pegarlos. La placa se imprime con la cara de los casquillos sobre la cama y las cunas hacia arriba (paredes
verticales, sin soportes). Medidas, agujeros y cunas, sin cambios.

Uso: python build_shields_imprimibles.py <carpeta Arm_Vasil/Brazo_modificado_STL> <carpeta de salida>
"""
import sys, os, numpy as np, trimesh
SRC, OUT = sys.argv[1], sys.argv[2]; CHK = os.path.join(OUT, 'comprobacion'); os.makedirs(CHK, exist_ok=True)
D = lambda a, *b: trimesh.boolean.difference([a, *b], engine='manifold')
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold')
U = lambda *a: trimesh.boolean.union(list(a), engine='manifold')
def box(lo, hi): return trimesh.creation.box(bounds=[lo, hi])
def load(name):
    m = trimesh.load(os.path.join(SRC, name + '.stl'))
    if m.extents.max() < 20: m.apply_scale(25.4)               # STL de Solid Edge en pulgadas
    return m
def on_bed(m):
    m = m.copy(); m.apply_translation([-m.bounds[:, 0].mean(), -m.bounds[:, 1].mean(), -m.bounds[0][2]]); return m
def row(parts, gap=6.0):                                         # coloca los separadores en fila sobre la cama
    out, x = [], 0.0
    for p in parts:
        p = on_bed(p); p.apply_translation([x - p.bounds[0][0], 0, 0]); x = p.bounds[1][0] + gap; out.append(p)
    return trimesh.util.concatenate(out)

# (nombre, eje normal a la placa, cara de la placa del lado de los casquillos, rotación para imprimir)
SHIELDS = [('Shield 1 - 2.0_1', 0, 3.0, trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])),  # x -> -z
           ('Shield 2 - 2.0_1', 2, 4.5, trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))]      # z -> -z
for name, ax, face, R in SHIELDS:
    m = load(name); tag = name.split(' - ')[0].replace(' ', '_')
    lo, hi = m.bounds[0] - 1, m.bounds[1] + 1; lo2 = lo.copy(); lo2[ax] = face
    side = box(lo2, hi)                                           # todo lo que queda del lado de los casquillos
    plate = D(m, side); plate = max(plate.split(only_watertight=False), key=lambda p: p.volume)
    lo3 = lo2.copy(); lo3[ax] = face + 1e-3                     # evita láminas de espesor cero en la cara de corte
    seps = [p for p in I(m, box(lo3, hi)).split(only_watertight=False) if p.volume > 1]
    juntas = U(plate, *seps)
    print(f'{tag}: original {m.volume:.0f} mm3 | placa {plate.volume:.0f} + {len(seps)} separadores '
          f'({", ".join("%.0f" % s.volume for s in seps)}) | diferencia {abs(m.volume - juntas.volume):.1f} mm3')
    for s in seps:
        e = np.delete(s.extents, ax); print('   separador Ø%.1f x %.1f mm en %s' % (e.max(), s.extents[ax], np.round(np.delete(s.bounds.mean(0), ax), 1).tolist()))
    plate.export(os.path.join(CHK, f'{tag}_placa_posicion_montaje.stl'))
    trimesh.util.concatenate(seps).export(os.path.join(CHK, f'{tag}_separadores_posicion_montaje.stl'))
    # para imprimir: la cara de los casquillos sobre la cama
    p = plate.copy(); p.apply_transform(R); p = on_bed(p)
    n, c, a = p.face_normals, p.triangles_center, p.area_faces
    ov = a[(n[:, 2] < -0.7) & (c[:, 2] > 0.05)].sum()
    print(f'   placa para imprimir: {np.round(p.extents, 1).tolist()} mm, apoyo {a[(n[:, 2] < -0.99) & (c[:, 2] < 0.05)].sum():.0f} mm2, '
          f'voladizos {ov:.0f} mm2')
    p.export(os.path.join(OUT, f'{tag}_imprimible.stl'))
    up = []
    for s in seps:                                                # separadores de pie (eje vertical)
        s = s.copy()
        if ax == 0: s.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
        up.append(s)
    row(up).export(os.path.join(OUT, f'{tag}_separadores_x{len(seps)}.stl'))
