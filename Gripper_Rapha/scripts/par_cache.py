"""Lee la malla de visualización que Solid Edge guarda dentro de un .par (Display/Cache0)
y reconstruye el antebrazo de Vasil (Brazo Parte 2_1) como sólido extruido, en las
coordenadas propias del .par (mm).

Solo las caras planas se leen de forma fiable, que es todo lo que necesita una pieza 2,5D
como esta: placa de 7,5 mm con un rebaje de 4,5 mm por una cara.

Uso: python par_cache.py "<Brazo Parte 2_1.par>" <salida.stl>
"""
import io, re, struct, sys, zlib
import numpy as np, olefile, trimesh, shapely.geometry as sg, shapely.ops as so

def _lod0(path):
    o = olefile.OleFileIO(path)
    inner = olefile.OleFileIO(io.BytesIO(o.openstream('Display/Cache0').read()))
    b = inner.openstream('L0-T1').read()
    return zlib.decompress(b[8:])

def planar_triangles(path):
    """Triángulos (en mm) de las tiras de la caché de visualización."""
    b = _lod0(path); tris = []
    for m in re.finditer(re.escape(bytes.fromhex('02000302')), b):
        p = m.start()
        L, N, nb, magic = struct.unpack('<4I', b[p+4:p+20])
        if magic != 681575250 or N == 0 or N*24 > L: continue
        pts = np.frombuffer(b[p+20:p+20+N*24], dtype='<f8').reshape(N, 3)
        with np.errstate(all='ignore'): pts = pts * 1000.0
        cur = []
        for q in pts:
            if not np.isfinite(q).all() or np.abs(q).max() > 5000:
                cur = []; continue
            cur.append(q)
            if len(cur) >= 3:
                i = len(cur) - 3
                a, c, d = (cur[i], cur[i+1], cur[i+2]) if i % 2 == 0 else (cur[i+1], cur[i], cur[i+2])
                tris.append([a, c, d])
    T = np.array(tris)
    n = np.cross(T[:, 1]-T[:, 0], T[:, 2]-T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return T, n

def face_polygon(T, n, z, tol=0.01):
    sel = (np.abs(n[:, 2]) > 0.999) & (np.abs(T[:, :, 2].mean(1) - z) < tol)
    poly = so.unary_union([sg.Polygon(t[:, :2]).buffer(1e-3, join_style=2) for t in T[sel]]).buffer(-1e-3, join_style=2)
    poly = poly.simplify(0.005).buffer(0)
    geoms = poly.geoms if hasattr(poly, 'geoms') else [poly]
    keep = []
    for g in geoms:                                   # quitar astillas y huecos diminutos
        if g.area < 1.0: continue
        holes = [h for h in g.interiors if sg.Polygon(h).area > 1.0]
        keep.append(sg.Polygon(g.exterior, holes))
    return so.unary_union(keep)

def extrude(poly, z0, z1):
    geoms = poly.geoms if hasattr(poly, 'geoms') else [poly]
    parts = []
    for g in geoms:
        m = trimesh.creation.extrude_polygon(g, z1 - z0); m.apply_translation([0, 0, z0]); parts.append(m)
    return parts

def forearm_solid(path):
    T, n = planar_triangles(path)
    zs = sorted(set(np.round(T[np.abs(n[:, 2]) > 0.999][:, :, 2].mean(1), 2)))
    z_bot, z_mid, z_top = zs[0], zs[1], zs[-1]             # -27, -24, -19.5
    lower = extrude(face_polygon(T, n, z_bot), z_bot, z_mid)
    upper = extrude(face_polygon(T, n, z_top), z_mid, z_top)
    return trimesh.boolean.union(lower + upper, engine='manifold'), (z_bot, z_mid, z_top)

if __name__ == '__main__':
    solid, z = forearm_solid(sys.argv[1])
    solid.export(sys.argv[2])
    print('caras planas z =', z, '| estanco:', solid.is_watertight, '| volumen %.0f mm3' % solid.volume,
          '| límites', np.round(solid.bounds, 2).tolist())
