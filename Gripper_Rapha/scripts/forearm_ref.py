"""Prepara el antebrazo de Vasil (Brazo Parte 2_1) como STL en mm para las comprobaciones.

Acepta el STL exportado por Solid Edge (detecta si está en pulgadas y lo pasa a mm)
o, si no hay STL, el .par (lee la malla de visualización con par_cache.py).
Además comprueba que la interfaz con el acople sigue siendo la esperada.

Uso: python forearm_ref.py <Brazo Parte 2_1.stl | .par> <salida.stl>
"""
import sys, os, numpy as np, trimesh
src, out = sys.argv[1], sys.argv[2]

if src.lower().endswith('.par'):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from par_cache import forearm_solid
    m, _ = forearm_solid(src)
else:
    m = trimesh.load(src)
    if m.extents.max() < 20:                      # exportado en pulgadas (Solid Edge por defecto)
        m.apply_scale(25.4); print('STL en pulgadas -> convertido a mm')

def diam_at(z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return None
    for e in s.discrete:
        p = np.array(e); c = (p.min(0) + p.max(0)) / 2
        if abs(c[0] - 150) < 2 and abs(c[1]) < 2 and np.ptp(p[:, 0]) < 30: return float(np.ptp(p[:, 0]))
checks = {
    'cara plana z=-27': abs(m.bounds[0][2] + 27) < 0.05,
    'cara superior z=-19.5': abs(m.bounds[1][2] + 19.5) < 0.05,
    'ancho 30 mm': abs(m.extents[1] - 30) < 0.05,
    'agujero punta Ø15': diam_at(-25.5) is not None and abs(diam_at(-25.5) - 15) < 0.2,
    'avellanado Ø24 hasta z=-24': diam_at(-21) is not None and abs(diam_at(-21) - 24) < 0.2 and abs(diam_at(-24.3) - 15) < 0.2,
}
for k, ok in checks.items(): print(('OK   ' if ok else 'FALLA'), k)
if not all(checks.values()):
    sys.exit('La punta del antebrazo ha cambiado: hay que revisar las cotas de build_mount_vasil.py')
m.export(out)
print('volumen %.0f mm3, límites %s' % (m.volume, np.round(m.bounds, 2).tolist()))
