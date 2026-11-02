"""Registra la respuesta de una articulación y calcula las métricas que pide el informe.

Ejemplos (desde la carpeta SOFTWARE/pc):
    python registrar_pid.py --puerto COM5 --escalon 1 15              # escalón de +15° en el hombro
    python registrar_pid.py --puerto COM5 --escalon 1 15 --pid 14 20 0.6   # probando otras ganancias
    python registrar_pid.py --puerto COM5 --lazo 1 -120 800            # lazo abierto (para ajuste_pid.py)
    python registrar_pid.py --puerto COM5 --autotune 1 70              # relé -> Ku, Pu
    python registrar_pid.py --csv resultados/escalon_j1.csv --articulacion 1   # analizar un CSV ya guardado

Guarda en resultados/: el CSV (tiempo, consigna, posición y PWM de las 3 articulaciones) y una gráfica PNG
con la consigna, la posición real y el PWM, más el tiempo de subida, la sobreoscilación, el tiempo de
establecimiento y el error en régimen permanente.
"""
import argparse
import datetime
import os

import matplotlib
import numpy as np

NOMBRES = ["base", "hombro", "codo"]


def metricas(t, ref, y, t0=None):
    """Métricas de la respuesta a un escalón. t en s; ref y y en grados."""
    if t0 is None:                                          # instante del escalón: primer salto de la consigna
        saltos = np.where(np.abs(np.diff(ref)) > 0.5)[0]
        t0 = t[saltos[0] + 1] if len(saltos) else t[0]
    i0 = np.searchsorted(t, t0)
    y0, r = y[max(i0 - 1, 0)], ref[-1]
    d = r - y0
    if abs(d) < 0.5:
        return None
    s = np.sign(d)
    tt, yy = t[i0:] - t0, y[i0:]
    frac = (yy - y0) / d
    def cruce(f):
        k = np.where(frac >= f)[0]
        return tt[k[0]] if len(k) else np.nan
    subida = cruce(0.9) - cruce(0.1)
    sobre = max(0.0, (np.max(s * (yy - r)))) / abs(d) * 100
    banda = max(0.02 * abs(d), 0.75)        # el Arduino deja de empujar a 0,6° (tolerancia)
    fuera = np.where(np.abs(yy - r) > banda)[0]
    estab = tt[fuera[-1] + 1] if len(fuera) and fuera[-1] + 1 < len(tt) else (np.nan if len(fuera) else 0.0)
    final = yy[tt >= tt[-1] - 0.5]
    ess = r - np.mean(final)
    iae = float(np.sum(np.abs(r - yy)[:-1] * np.diff(tt)))
    return dict(t0=t0, salto=d, subida=subida, sobreoscilacion=sobre, establecimiento=estab, error_final=ess, IAE=iae)


def grafica(datos, j, titulo, ruta_png, m=None):
    import matplotlib.pyplot as plt
    t = (datos[:, 0] - datos[0, 0]) / 1000
    ref, y, u = datos[:, 1 + 3 * j], datos[:, 2 + 3 * j], datos[:, 3 + 3 * j]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.4]))
    a1.plot(t, ref, "--", color="#7a3fb5", lw=1.8, label="consigna")
    a1.plot(t, y, color="#2e9e5b", lw=1.8, label="posición real")
    a1.set_ylabel(f"{NOMBRES[j]} (grados)"); a1.grid(alpha=0.3); a1.legend(loc="best")
    if m:
        texto = (f"subida 10-90 %: {m['subida']:.2f} s\nsobreoscilación: {m['sobreoscilacion']:.1f} %\n"
                 f"establecimiento: {m['establecimiento']:.2f} s\nerror final: {m['error_final']:.2f}°")
        a1.text(0.99, 0.04, texto, transform=a1.transAxes, ha="right", va="bottom", fontsize=9,
                bbox=dict(fc="white", ec="#bbbbbb"))
    a2.plot(t, u, color="#d4762c", lw=1.4); a2.set_ylabel("PWM"); a2.set_xlabel("tiempo (s)"); a2.grid(alpha=0.3)
    a1.set_title(titulo)
    fig.tight_layout(); fig.savefig(ruta_png, dpi=130); plt.close(fig)


def guardar_csv(datos, ruta):
    from brazo_serial import COLUMNAS
    np.savetxt(ruta, datos, delimiter=",", header=",".join(COLUMNAS), comments="", fmt="%.3f")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", help="COM5, /dev/ttyACM0...")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--escalon", nargs=2, metavar=("J", "GRADOS"))
    g.add_argument("--lazo", nargs=3, metavar=("J", "PWM", "MS"))
    g.add_argument("--autotune", nargs=2, metavar=("J", "D"))
    g.add_argument("--csv", help="analizar un CSV ya guardado")
    ap.add_argument("--duracion", type=float, default=3.0, help="segundos de registro del escalón")
    ap.add_argument("--pid", nargs=3, type=float, metavar=("KP", "KI", "KD"))
    ap.add_argument("--articulacion", type=int, default=1, help="con --csv")
    ap.add_argument("--sin-ventana", action="store_true", help="no abrir la gráfica")
    a = ap.parse_args()
    if a.sin_ventana:
        matplotlib.use("Agg")
    os.makedirs("resultados", exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if a.csv:
        from brazo_serial import leer_csv
        datos, j, tipo = leer_csv(a.csv), a.articulacion, os.path.splitext(os.path.basename(a.csv))[0]
        base = os.path.join("resultados", tipo)
    else:
        from brazo_serial import Brazo
        br = Brazo(a.puerto)
        br.enviar("ON"); br.esperar(lambda l: l.startswith("OK") or l.startswith("!"), 3)
        if a.escalon:
            j, d = int(a.escalon[0]), float(a.escalon[1])
            if a.pid:
                br.enviar(f"PID {j} {a.pid[0]} {a.pid[1]} {a.pid[2]}"); br.esperar(lambda l: l.startswith("G "), 3)
            filas, _ = br.registro(f"ESCALON {j} {d} {int(a.duracion * 1000)}", a.duracion + 5)
            tipo = f"escalon_j{j}_{d:+g}" + (f"_kp{a.pid[0]:g}_ki{a.pid[1]:g}_kd{a.pid[2]:g}" if a.pid else "")
        elif a.lazo:
            j = int(a.lazo[0])
            filas, _ = br.registro(f"PWM {j} {int(a.lazo[1])} {int(a.lazo[2])}", int(a.lazo[2]) / 1000 + 5)
            tipo = f"lazo_abierto_j{j}_pwm{int(a.lazo[1])}"
        else:
            j = int(a.autotune[0])
            filas, extra = br.registro(f"AUTOTUNE {j} {int(a.autotune[1])}", 40)
            extra += br.esperar(lambda l: l.startswith("  ZN sin"), 3)
            tipo = f"autotune_j{j}"
            with open(os.path.join("resultados", f"{marca}_{tipo}.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(extra))
        br.cerrar()
        datos = np.array(filas)
        if len(datos) == 0:
            print("No han llegado datos (¿el control está activo? ¿hay un fallo?)"); return
        base = os.path.join("resultados", f"{marca}_{tipo}")
        guardar_csv(datos, base + ".csv")
        print("CSV:", base + ".csv")

    t = (datos[:, 0] - datos[0, 0]) / 1000
    m = metricas(t, datos[:, 1 + 3 * j], datos[:, 2 + 3 * j]) if "lazo" not in base else None
    if m:
        print(f"{NOMBRES[j]}: salto {m['salto']:+.1f}°  subida {m['subida']:.2f} s  sobreoscilación "
              f"{m['sobreoscilacion']:.1f} %  establecimiento {m['establecimiento']:.2f} s  "
              f"error final {m['error_final']:+.2f}°  IAE {m['IAE']:.2f}")
    grafica(datos, j, f"{os.path.basename(base)}", base + ".png", m)
    print("Gráfica:", base + ".png")
    if not a.sin_ventana:
        import matplotlib.pyplot as plt
        plt.imshow(plt.imread(base + ".png")); plt.axis("off"); plt.show()


if __name__ == "__main__":
    main()
