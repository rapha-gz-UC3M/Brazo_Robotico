"""Rutas y utilidades comunes de los scripts de Gripper_Rapha.

Estructura:
  Gripper_Rapha/
    IMPRIMIR/1_base, 2_brazo, 3_gripper     lo que se imprime, en mm, ya orientado
    ENSAMBLAJE/                             brazo entero montado + piezas colocadas + transformaciones.json
    GRIPPER/                                diseño de la pinza: original, comprobación, Solid Edge, imágenes
    scripts/                                estos scripts
Los STL de Vasil (../Arm_Vasil/Brazo_modificado_STL) y de Ignacio (../Base_Ignacio) solo se leen.
"""
import os, numpy as np, trimesh

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
GR = os.path.dirname(SCRIPTS); REPO = os.path.dirname(GR)
VAS = os.path.join(REPO, 'Arm_Vasil', 'Brazo_modificado_STL')
IGN = os.path.join(REPO, 'Base_Ignacio')
IMP = os.path.join(GR, 'IMPRIMIR')
IMP_BASE, IMP_BRAZO, IMP_GRIP = (os.path.join(IMP, d) for d in ('1_base', '2_brazo', '3_gripper'))
ENS = os.path.join(GR, 'ENSAMBLAJE'); COL = os.path.join(ENS, 'piezas_colocadas')
TF_JSON = os.path.join(ENS, 'transformaciones.json')
GRIP = os.path.join(GR, 'GRIPPER'); GRIP_CHK = os.path.join(GRIP, 'comprobacion')
GRIP_ORIG = os.path.join(GRIP, 'original', 'gripper_superbtech'); BUILD = os.path.join(GRIP, 'build')
for d in (IMP_BASE, IMP_BRAZO, IMP_GRIP, COL, GRIP_CHK, BUILD): os.makedirs(d, exist_ok=True)


def load_mm(p):
    """Carga un STL; si viene de Solid Edge en pulgadas (lo normal), lo pasa a mm."""
    m = trimesh.load(p)
    if m.extents.max() < 20: m.apply_scale(25.4)
    return m


def orient(m, up):
    """Gira la pieza para que 'up' (dirección propia) apunte a +Z, la apoya en z=0 y la centra en XY."""
    m = m.copy()
    if up is not None: m.apply_transform(trimesh.geometry.align_vectors(np.asarray(up, float), [0, 0, 1.0]))
    m.apply_translation([-m.bounds[:, 0].mean(), -m.bounds[:, 1].mean(), -m.bounds[0][2]]); return m


def row(parts, gap=6.0):
    """Pone varias piezas (ya orientadas) en fila sobre la cama, en un solo STL."""
    out, x = [], 0.0
    for p in parts:
        p = p.copy(); p.apply_translation([x - p.bounds[0][0], -p.bounds[:, 1].mean(), -p.bounds[0][2]])
        x = p.bounds[1][0] + gap; out.append(p)
    r = trimesh.util.concatenate(out); r.apply_translation([-r.bounds[:, 0].mean(), 0, 0]); return r


def clean(t, tol=0.003):
    """Quita astillas y vértices casi repetidos para que el STL (float32) siga siendo un sólido cerrado."""
    import manifold3d as mf
    if not t.is_volume: return t
    m = mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32))).simplify(tol)
    g = m.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts))


def export(m, path, check=True):
    """Exporta y comprueba que, al volver a leerlo, sigue siendo un sólido cerrado (si la pieza lo era)."""
    vol = m.is_volume
    m = clean(m) if vol else m
    m.export(path)
    if check and vol and not trimesh.load(path).is_volume:
        raise RuntimeError('no es un sólido cerrado tras exportar: ' + path)
    return m
