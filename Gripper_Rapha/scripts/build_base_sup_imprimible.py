"""Versión imprimible de BASE_TAPA_SUP (pieza de Ignacio; el original no se toca).

Problema del original: la pestaña que cuelga bajo el disco (22,5 x 6 mm, hasta 50 mm por debajo del faldón)
y el cubo central (0,5 mm más bajo que el faldón) impiden apoyar la pieza plana en la cama.

Cambios:
  1. La pestaña se imprime aparte (tumbada, sin soportes) con una espiga que atraviesa el disco por una
     mortaja, y se pega (cianoacrilato o epoxi). Una vez pegada queda en la misma posición que en el original.
  2. Se recortan los 0,5 mm inferiores del cubo central para que quede a ras del faldón: la pieza apoya
     plana sobre el faldón y el cubo. El encaje de Pieza_Eje_Giro_Base pierde solo 0,5 mm de profundidad.
Todo lo demás (faldón, disco, ranuras de las paletas, agujeros) queda igual.

Uso: python build_base_sup_imprimible.py <BASE_TAPA_SUP.stl> <carpeta de salida>
(en <salida>/comprobacion quedan las dos piezas en la posición de montaje)
"""
import sys, os, numpy as np, trimesh
SRC, OUT = sys.argv[1], sys.argv[2]; CHK = os.path.join(OUT, 'comprobacion'); os.makedirs(CHK, exist_ok=True)
D = lambda a, *b: trimesh.boolean.difference([a, *b], engine='manifold')
U = lambda *a: trimesh.boolean.union(list(a), engine='manifold')
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold')
def box(x0, x1, y0, y1, z0, z1): return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])

m = trimesh.load(SRC)
if m.extents.max() < 20: m.apply_scale(25.4)                     # STL de Solid Edge en pulgadas
# coordenadas propias (mm, y hacia arriba): disco y 0..3, faldón y -19,5..0, cubo y -20..0, pestaña y -70..0
TAB = (37.25, 59.75, -3.0, 3.0)                                   # x0, x1, z0, z1 de la pestaña
Y_FALDON = -19.5
CLR = 0.2                                                         # holgura por lado de la espiga en la mortaja
TEN = (40.0, 57.0, -1.75, 1.75)                                   # espiga 17 x 3,5 mm
tab_zone = box(TAB[0] - 0.05, TAB[1] + 0.05, -71, 0.0, TAB[2] - 0.05, TAB[3] + 0.05)

# --- cuerpo principal ---
body = D(m, tab_zone)
body = D(body, box(-40, 40, -25, Y_FALDON, -40, 40))             # cubo a ras del faldón
body = D(body, box(TEN[0] - CLR, TEN[1] + CLR, -1, 4, TEN[2] - CLR, TEN[3] + CLR))   # mortaja pasante
body = max(body.split(only_watertight=False), key=lambda p: p.volume)

# --- pestaña con espiga (la espiga atraviesa los 3 mm del disco) ---
tab = I(m, box(TAB[0] - 0.05, TAB[1] + 0.05, -71, -0.001, TAB[2] - 0.05, TAB[3] + 0.05))
tab = U(tab, box(TEN[0], TEN[1], -0.5, 3.0, TEN[2], TEN[3]))

# comprobaciones: piezas juntas = original (salvo mortaja y 0,5 mm del cubo)
juntas = U(body, tab)
print('volumen original %.0f mm3 | cuerpo %.0f + pestaña %.0f | diferencia con el original %.0f mm3'
      % (m.volume, body.volume, tab.volume, m.volume - juntas.volume))
print('cuerpo: estanco %s, apoyo plano en y=%.2f; pestaña: estanca %s' % (body.is_watertight, body.bounds[0][1], tab.is_watertight))
body.export(os.path.join(CHK, 'BASE_TAPA_SUP_imprimible_posicion_montaje.stl'))
tab.export(os.path.join(CHK, 'BASE_TAPA_SUP_pestana_posicion_montaje.stl'))

# --- orientados para imprimir (Z hacia arriba, sobre z=0) ---
yup2zup = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])      # y -> z
b = body.copy(); b.apply_transform(yup2zup); b.apply_translation([0, 0, -b.bounds[0][2]])
t = tab.copy(); t.apply_translation([-(TAB[0] + TAB[1]) / 2, 0, -TAB[2]])   # tumbada: cara z=-3 en la cama
t.apply_translation([0, -t.bounds[0][1], 0]); t.apply_translation([0, 0, -t.bounds[0][2]])
b.export(os.path.join(OUT, 'BASE_TAPA_SUP_imprimible.stl'))
t.export(os.path.join(OUT, 'BASE_TAPA_SUP_pestana.stl'))
print('para imprimir: cuerpo %s mm, pestaña %s mm' % (np.round(b.extents, 1).tolist(), np.round(t.extents, 1).tolist()))
