"""Prepara una placa del antebrazo de Vasil como STL en mm para las comprobaciones y verifica
que la punta sigue teniendo las cotas para las que está diseñado el acople.

  A = Brazo Parte 2_1    (z de -27 a -19,5; agujero Ø15 + avellanado Ø24 hacia +z)
  B = Brazo Parte 2.2_4  (z de -7,5 a 0;    agujero Ø15 + avellanado Ø24 hacia -z; orejetas Ø6 en (138, ±26,2))

Acepta el STL exportado por Solid Edge (detecta si está en pulgadas y lo pasa a mm) o el .par
(lee la malla de visualización con par_cache.py).

Uso: python forearm_ref.py A|B <pieza.stl | pieza.par> <salida.stl>
"""
import sys, os, numpy as np, trimesh
plate, src, out = sys.argv[1].upper(), sys.argv[2], sys.argv[3]

if src.lower().endswith('.par'):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from par_cache import forearm_solid
    m, _ = forearm_solid(src)
else:
    m = trimesh.load(src)
    if m.extents.max() < 20:                      # exportado en pulgadas (Solid Edge por defecto)
        m.apply_scale(25.4); print('STL en pulgadas -> convertido a mm')

def diam_at(z, cx=150.0, cy=0.0):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return -1
    for e in s.discrete:
        p = np.array(e); c = (p.min(0) + p.max(0)) / 2
        if abs(c[0] - cx) < 2 and abs(c[1] - cy) < 2 and np.ptp(p[:, 0]) < 30: return float(np.ptp(p[:, 0]))
    return -1
near = lambda a, b, t=0.2: abs(a - b) < t
if plate == 'A':
    checks = {'caras z=-27 y z=-19,5': near(m.bounds[0][2], -27, .05) and near(m.bounds[1][2], -19.5, .05),
              'ancho 30 mm': near(m.extents[1], 30, .05),
              'agujero punta Ø15': near(diam_at(-25.5), 15),
              'avellanado Ø24 de z=-24 a -19,5': near(diam_at(-21), 24) and near(diam_at(-24.3), 15)}
else:
    checks = {'caras z=-7,5 y z=0': near(m.bounds[0][2], -7.5, .05) and near(m.bounds[1][2], 0, .05),
              'agujero punta Ø15': near(diam_at(-1.5), 15),
              'avellanado Ø24 de z=-7,5 a -3': near(diam_at(-5), 24) and near(diam_at(-2.7), 15),
              'orejetas Ø6 en (138, ±26,2)': near(diam_at(-1.5, 138, 26.2), 6) and near(diam_at(-1.5, 138, -26.2), 6)}
for k, ok in checks.items(): print(('OK   ' if ok else 'FALLA'), f'placa {plate}:', k)
if not all(checks.values()):
    sys.exit('La punta del antebrazo ha cambiado: hay que revisar las cotas de build_mount_vasil.py')
m.export(out)
print('volumen %.0f mm3, límites %s' % (m.volume, np.round(m.bounds, 2).tolist()))
