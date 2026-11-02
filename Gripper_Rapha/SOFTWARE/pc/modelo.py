"""Cinemática del brazo en Python, con los mismos datos que el Arduino (se leen de brazo_robotico/config.h)."""
import math
import os
import re

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "brazo_robotico", "config.h")


def _leer_config():
    p = dict(L1_MM=180.0, L2_MM=300.0, H_HOMBRO_MM=185.0, LIM_MIN=[-75, -60, 15], LIM_MAX=[75, 70, 150],
             CUBO_MM_INI=40.0, ALTURA_SEGURA_MM=60.0, Z_AGARRE_MM=4.0)
    try:
        txt = open(CONFIG, encoding="utf-8").read()
        for k in ("L1_MM", "L2_MM", "H_HOMBRO_MM", "CUBO_MM_INI", "ALTURA_SEGURA_MM", "Z_AGARRE_MM"):
            m = re.search(rf"{k}\s*=\s*(-?[\d.]+)f?", txt)
            if m:
                p[k] = float(m.group(1))
        for k in ("LIM_MIN", "LIM_MAX"):
            m = re.search(rf"{k}\[3\]\s*=\s*\{{([^}}]*)\}}", txt)
            if m:
                p[k] = [float(x.strip().rstrip("f")) for x in m.group(1).split(",")]
    except OSError:
        pass
    return p


P = _leer_config()


def directa(q):
    """q en grados -> (x, y, z) en mm del centro de las mordazas."""
    a0, a1, a12 = (math.radians(v) for v in (q[0], q[1], q[1] + q[2]))
    r = P["L1_MM"] * math.sin(a1) + P["L2_MM"] * math.sin(a12)
    return r * math.cos(a0), r * math.sin(a0), P["H_HOMBRO_MM"] + P["L1_MM"] * math.cos(a1) + P["L2_MM"] * math.cos(a12)


def inversa(x, y, z):
    """(x, y, z) mm -> q en grados, o None si no se alcanza o se sale de los límites."""
    L1, L2 = P["L1_MM"], P["L2_MM"]
    r, h = math.hypot(x, y), z - P["H_HOMBRO_MM"]
    c2 = (r * r + h * h - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if abs(c2) > 1:
        return None
    a2 = math.acos(c2)
    a1 = math.atan2(r, h) - math.atan2(L2 * math.sin(a2), L1 + L2 * math.cos(a2))
    q = [math.degrees(math.atan2(y, x)) if r > 1 else 0.0, math.degrees(a1), math.degrees(a2)]
    if any(q[j] < P["LIM_MIN"][j] or q[j] > P["LIM_MAX"][j] for j in range(3)):
        return None
    return q


def alcance_cubo(lado, niveles=1):
    """Radios (mm) donde se puede coger y dejar un cubo: agarre en la mesa y altura segura por encima."""
    zs = [lado * 0.5 + P["Z_AGARRE_MM"], lado * niveles + P["ALTURA_SEGURA_MM"]]
    ok = [r for r in range(0, 600, 2) if all(inversa(r, 0, z) for z in zs)]
    return (min(ok), max(ok)) if ok else (None, None)
