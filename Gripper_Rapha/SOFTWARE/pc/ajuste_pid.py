"""Ajuste del PID con un modelo identificado (no solo a mano): identificación + 3 métodos + simulación.

1. Identificación. Con uno o varios ensayos en lazo abierto (registrar_pid.py --lazo J PWM MS) se ajusta,
   por mínimos cuadrados, un modelo de la articulación:

        velocidad:  τ·dω/dt + ω = K·(u + b − f·sign(u + b))     (con un retardo θ en u)
        posición :  dq/dt = ω

   K (°/s por unidad de PWM), τ (s) y θ (s) son la dinámica del motor; b es la carga de la gravedad (PWM)
   y f el rozamiento seco (PWM). Visto desde el PWM, la posición es un proceso INTEGRADOR con retardo:
   G(s) = K·e^(−θs) / (s·(τs + 1)). Por eso las tablas de Ziegler-Nichols, Cohen-Coon y CHR en lazo
   abierto (pensadas para procesos que se estabilizan, de primer orden con retardo) no se aplican tal cual.

2. Candidatos:
   - SIMC (Skogestad), la regla específica para integrador + retardo + constante de tiempo.
   - Ziegler-Nichols por relé (si se pasan Ku y Pu del comando AUTOTUNE): clásico y "sin sobreoscilación".
   - Optimizado: minimiza el ITAE de la respuesta simulada a un escalón, penalizando la sobreoscilación,
     partiendo del SIMC.
3. Simulación de cada candidato con EL MISMO PID que el Arduino (100 Hz, anti-windup, derivada sobre la
   medida filtrada, banda de tolerancia, compensación de zona muerta, saturación y rampa de PWM).

Ejemplo:
    python ajuste_pid.py --articulacion 1 --csv resultados/*lazo_abierto_j1*.csv --ku 82 --pu 1.09
Salida: tabla con las métricas, gráfica en resultados/ajuste_pid_j1.png y la línea "PID 1 kp ki kd"
para mandar al brazo.
"""
import argparse
import glob
import os

import matplotlib
import numpy as np
from scipy.optimize import least_squares, minimize

from brazo_serial import leer_csv
from registrar_pid import metricas, NOMBRES

DT = 0.01  # periodo de control del Arduino


# ------------------------------------------------------------------------------------- modelo
def simular_lazo_abierto(par, t, u, q0):
    """Simula el modelo con el PWM registrado (se mantiene entre muestras) en pasos de 1 ms."""
    K, tau, theta, b, f = par
    h = 0.001
    tt = np.arange(t[0], t[-1] + h / 2, h)
    uu = u[np.clip(np.searchsorted(t, tt - theta, side="right") - 1, 0, len(u) - 1)]   # retardo θ
    w, q = 0.0, q0
    out = np.empty(len(tt))
    for k in range(len(tt)):
        v = uu[k] + b
        ef = 0.0 if abs(v) <= f else v - f * np.sign(v)
        w += (K * ef - w) * h / max(tau, 1e-3)
        q += w * h
        out[k] = q
    return np.interp(t, tt, out)


def identificar(ensayos, f_fijo):
    """ensayos: lista de (t, u, q). Ajusta K, tau, theta, b (y f si hay ensayos en los dos sentidos)."""
    ambos = len({np.sign(np.median(u[np.abs(u) > 1])) for _, u, _ in ensayos}) > 1
    def res(x):
        K, tau, theta, b = x[:4]; f = x[4] if ambos else f_fijo
        return np.concatenate([simular_lazo_abierto((K, tau, theta, b, f), t, u, q[0]) - q for t, u, q in ensayos])
    x0 = [0.4, 0.06, 0.01, 0.0] + ([f_fijo] if ambos else [])
    lo = [1e-3, 0.005, 0.0, -255] + ([0] if ambos else [])
    hi = [5.0, 1.0, 0.3, 255] + ([150] if ambos else [])
    r = least_squares(res, x0, bounds=(lo, hi))
    K, tau, theta, b = r.x[:4]; f = r.x[4] if ambos else f_fijo
    rmse = np.sqrt(np.mean(r.fun ** 2))
    return dict(K=K, tau=tau, theta=theta, b=b, f=f, rmse=rmse, f_ajustado=ambos)


# ------------------------------------------------------------------------------------- PID del Arduino
def simular_pid(gan, mod, salto=15.0, T=3.0, pwm_max=255, pwm_min=40, tol=0.6, i_max=120, filtro_d=0.3, rampa=25):
    kp, ki, kd = gan
    K, tau, theta, b, f = mod["K"], mod["tau"], mod["theta"], mod["b"], mod["f"]
    n = int(T / DT); t = np.arange(n) * DT
    q = 0.0; w = 0.0; i = 0.0; deriv = 0.0; q_ant = 0.0; u_act = 0.0
    ret = int(round(theta / DT)); hist = [0.0] * (ret + 1)
    Q = np.zeros(n); U = np.zeros(n); R = np.full(n, salto)
    sub = 10                                    # la planta se integra 10 veces más fino que el control
    # en reposo antes del escalón: el integrador ya sostiene la gravedad (como en el robot)
    i = float(np.clip(-b, -i_max, i_max))
    for k in range(n):
        e = salto - q
        dmed = (q - q_ant) / DT; q_ant = q
        deriv += filtro_d * (dmed - deriv)
        d = -kd * deriv; p = kp * e
        dentro = abs(e) <= tol
        sin_i = p + d
        sat = (sin_i + i >= pwm_max and e > 0) or (sin_i + i <= -pwm_max and e < 0)
        if not dentro and not sat:
            i += ki * e * DT
        i = float(np.clip(i, -i_max, i_max))
        if dentro:
            u = i
        else:
            u = p + i + d
            u += pwm_min * np.sign(u) if u != 0 else 0
        u = float(np.clip(u, -pwm_max, pwm_max))
        u = float(np.clip(u, u_act - rampa, u_act + rampa)); u_act = u
        hist.append(u); ud = hist.pop(0)
        for _ in range(sub):
            v = ud + b
            ef = 0.0 if abs(v) <= f else v - f * np.sign(v)
            w += (K * ef - w) * (DT / sub) / max(tau, 1e-3)
            q += w * DT / sub
        Q[k] = q; U[k] = u
    return t, R, Q, U


def coste(gan, mod, salto, **kw):
    if min(gan) < 0:
        return 1e9
    t, R, Q, U = simular_pid(gan, mod, salto, **kw)
    e = np.abs(R - Q)
    itae = np.sum(t * e) * DT
    sobre = max(0.0, np.max(np.sign(salto) * (Q - salto))) / abs(salto) * 100
    oscil = np.sum(np.abs(np.diff(np.sign(np.diff(Q[t > 0.2]))))) / 2   # cambios de sentido
    return itae + 0.05 * sobre ** 2 + 0.02 * oscil + 1e-6 * np.sum(np.diff(U) ** 2)


# ------------------------------------------------------------------------------------- reglas
def simc(mod, tau_c=None):
    K, tau, theta = mod["K"], mod["tau"], mod["theta"]
    tau_c = tau_c if tau_c is not None else max(theta, 0.1)
    Kc = 1.0 / (K * (tau_c + theta)); Ti = 4 * (tau_c + theta); Td = tau
    return (Kc * (1 + Td / Ti), Kc / Ti, Kc * Td)          # forma en serie -> paralela (la del Arduino)


def zn_rele(Ku, Pu):
    return {"ZN relé clásico": (0.6 * Ku, 1.2 * Ku / Pu, 0.075 * Ku * Pu),
            "ZN relé sin sobreosc.": (0.2 * Ku, 0.4 * Ku / Pu, 0.0667 * Ku * Pu)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--articulacion", type=int, required=True)
    ap.add_argument("--csv", nargs="+", required=True, help="ensayos en lazo abierto (se admiten comodines)")
    ap.add_argument("--pwm-min", type=float, default=40, help="zona muerta del Arduino (PWMMIN)")
    ap.add_argument("--ku", type=float); ap.add_argument("--pu", type=float)
    ap.add_argument("--salto", type=float, default=15.0, help="escalón de prueba (grados)")
    ap.add_argument("--pwm-max", type=float, default=None)
    ap.add_argument("--actual", nargs=3, type=float, metavar=("KP", "KI", "KD"), help="ganancias que tenéis ahora")
    ap.add_argument("--sin-ventana", action="store_true")
    a = ap.parse_args()
    if a.sin_ventana:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    j = a.articulacion
    pwm_max = a.pwm_max or [140, 255, 230][j]
    tol = 0.6

    ficheros = [f for patron in a.csv for f in glob.glob(patron)]
    ensayos = []
    for fch in ficheros:
        d = leer_csv(fch)
        t = (d[:, 0] - d[0, 0]) / 1000; u = d[:, 3 + 3 * j]; q = d[:, 2 + 3 * j]
        ensayos.append((t, u, q))
    mod = identificar(ensayos, a.pwm_min)
    print(f"Modelo de {NOMBRES[j]} ({len(ensayos)} ensayo/s):  K = {mod['K']:.3f} °/s por PWM  τ = {mod['tau'] * 1000:.0f} ms  "
          f"θ = {mod['theta'] * 1000:.0f} ms  gravedad b = {mod['b']:+.1f} PWM  rozamiento f = {mod['f']:.1f} PWM"
          f"{'' if mod['f_ajustado'] else ' (fijado)'}  error del ajuste = {mod['rmse']:.2f}°")

    cand = {}
    if a.actual:
        cand["Actual"] = tuple(a.actual)
    cand["SIMC"] = simc(mod)
    if a.ku and a.pu:
        cand.update(zn_rele(a.ku, a.pu))
    kw = dict(pwm_max=pwm_max, pwm_min=a.pwm_min, tol=tol)
    x0 = np.log(np.maximum(cand["SIMC"], 1e-3))
    r = minimize(lambda x: coste(np.exp(x), mod, a.salto, **kw), x0, method="Nelder-Mead",
                 options=dict(maxiter=600, xatol=1e-3, fatol=1e-4))
    cand["Optimizado (ITAE)"] = tuple(np.exp(r.x))

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.4]))
    print(f"\n{'método':24s} {'Kp':>8s} {'Ki':>8s} {'Kd':>8s} {'subida':>8s} {'sobreos.':>9s} {'establ.':>8s} {'ITAE':>7s}")
    for nombre, g in cand.items():
        t, R, Q, U = simular_pid(g, mod, a.salto, **kw)
        m = metricas(np.concatenate([[-DT], t]), np.concatenate([[0], R]), np.concatenate([[0], Q]), t0=0.0)
        itae = np.sum(t * np.abs(R - Q)) * DT
        print(f"{nombre:24s} {g[0]:8.3f} {g[1]:8.3f} {g[2]:8.4f} {m['subida']:7.2f}s {m['sobreoscilacion']:8.1f}% "
              f"{m['establecimiento']:7.2f}s {itae:7.3f}")
        a1.plot(t, Q, lw=1.8, label=f"{nombre}  (Kp {g[0]:.1f}, Ki {g[1]:.1f}, Kd {g[2]:.2f})")
        a2.plot(t, U, lw=1.2)
    a1.axhline(a.salto, ls="--", color="k", lw=1, label="consigna")
    a1.set_ylabel(f"{NOMBRES[j]} (grados)"); a1.grid(alpha=0.3); a1.legend(fontsize=8)
    a1.set_title(f"Escalón de {a.salto:g}° simulado con el modelo identificado — {NOMBRES[j]}")
    a2.set_ylabel("PWM"); a2.set_xlabel("tiempo (s)"); a2.grid(alpha=0.3)
    fig.tight_layout()
    os.makedirs("resultados", exist_ok=True)
    ruta = os.path.join("resultados", f"ajuste_pid_j{j}.png"); fig.savefig(ruta, dpi=130)
    g = cand["Optimizado (ITAE)"]
    print(f"\nGráfica: {ruta}\nPara probarlo en el brazo:   PID {j} {g[0]:.3f} {g[1]:.3f} {g[2]:.4f}"
          f"\ny comprobarlo con:            python registrar_pid.py --puerto COMx --escalon {j} {a.salto:g}")
    if not a.sin_ventana:
        plt.show()


if __name__ == "__main__":
    main()
