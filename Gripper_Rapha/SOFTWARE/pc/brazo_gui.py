"""Interfaz gráfica del brazo (extra de la práctica): estado en vivo, movimientos y tarea de apilar con el ratón.

    pip install -r requirements.txt
    python brazo_gui.py

- Vista desde arriba de la mesa: clic izquierdo = posición de un cubo (en orden), clic derecho = dónde se
  forma la pila. "Apilar" manda la tarea al Arduino. La zona verde es donde el brazo alcanza a coger y dejar
  cubos de ese tamaño; la zona más oscura, la recomendada (el hombro de 45 RPM va justo de par si se estira).
- Mover articulaciones (JOG) o la pinza a un punto (x, y, z), abrir y cerrar la pinza.
- PARO (o la tecla Esc) apaga los motores al momento.
"""
import queue
import re
import tkinter as tk
from tkinter import ttk, messagebox

import modelo
from brazo_serial import Brazo, puertos

ESCALA = 1.1            # píxeles por mm en la vista de la mesa
ANCHO, ALTO = 860, 540  # tamaño del dibujo de la mesa (px)
BASE_Y = ALTO - 30      # la base del brazo, abajo en el centro
ZONA_RECOMENDADA = (160, 300)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Brazo robótico - control")
        self.brazo = None
        self.cubos, self.pila = [], None
        self.estado = {}
        self._construir()
        self.bind("<Escape>", lambda e: self.paro())
        self.after(100, self._leer)
        self.after(500, self._sondear)

    # ------------------------------------------------------------------------------------------ interfaz
    def _construir(self):
        arriba = ttk.Frame(self, padding=6); arriba.pack(fill="x")
        ttk.Label(arriba, text="Puerto").pack(side="left")
        self.cb_puerto = ttk.Combobox(arriba, values=puertos(), width=14); self.cb_puerto.pack(side="left", padx=4)
        if self.cb_puerto["values"]:
            self.cb_puerto.current(0)
        ttk.Button(arriba, text="↻", width=3, command=lambda: self.cb_puerto.configure(values=puertos())).pack(side="left")
        self.bt_con = ttk.Button(arriba, text="Conectar", command=self.conectar); self.bt_con.pack(side="left", padx=6)
        self.lb_estado = ttk.Label(arriba, text="desconectado", foreground="#888"); self.lb_estado.pack(side="left", padx=10)
        tk.Button(arriba, text="  PARO  ", bg="#c62828", fg="white", font=("Segoe UI", 11, "bold"),
                  command=self.paro).pack(side="right")

        cuerpo = ttk.Frame(self, padding=6); cuerpo.pack(fill="both", expand=True)
        izq = ttk.Frame(cuerpo); izq.pack(side="left", fill="y")
        der = ttk.Frame(cuerpo); der.pack(side="left", fill="both", expand=True, padx=(8, 0))

        f = ttk.LabelFrame(izq, text="Robot", padding=6); f.pack(fill="x")
        for i, (t, c) in enumerate([("HOME", "HOME"), ("ON", "ON"), ("OFF", "OFF"), ("REARMAR", "REARMAR"), ("Reposo", "J 0 10 100")]):
            ttk.Button(f, text=t, width=9, command=lambda c=c: self.enviar(c)).grid(row=0, column=i, padx=1)
        self.txt_estado = tk.Text(f, width=44, height=7, font=("Consolas", 9), bg="#f6f6f6", relief="flat")
        self.txt_estado.grid(row=1, column=0, columnspan=5, pady=4)

        f = ttk.LabelFrame(izq, text="Articulaciones (JOG)", padding=6); f.pack(fill="x", pady=6)
        self.paso = tk.DoubleVar(value=5.0)
        ttk.Label(f, text="paso (°)").grid(row=0, column=0); ttk.Entry(f, textvariable=self.paso, width=6).grid(row=0, column=1)
        for j, n in enumerate(["base", "hombro", "codo"]):
            ttk.Label(f, text=n, width=8).grid(row=j + 1, column=0, sticky="w")
            ttk.Button(f, text="−", width=4, command=lambda j=j: self.enviar(f"JOG {j} {-self.paso.get()}")).grid(row=j + 1, column=1)
            ttk.Button(f, text="+", width=4, command=lambda j=j: self.enviar(f"JOG {j} {self.paso.get()}")).grid(row=j + 1, column=2)

        f = ttk.LabelFrame(izq, text="Pinza a un punto (mm)", padding=6); f.pack(fill="x")
        self.xyz = [tk.DoubleVar(value=v) for v in (220, 0, 80)]
        for i, (n, v) in enumerate(zip("xyz", self.xyz)):
            ttk.Label(f, text=n).grid(row=0, column=2 * i); ttk.Entry(f, textvariable=v, width=6).grid(row=0, column=2 * i + 1)
        ttk.Button(f, text="Ir", command=lambda: self.enviar("P " + " ".join(f"{v.get():g}" for v in self.xyz))).grid(row=0, column=6, padx=4)

        f = ttk.LabelFrame(izq, text="Pinza y cubo", padding=6); f.pack(fill="x", pady=6)
        ttk.Button(f, text="Abrir", command=lambda: self.enviar("PINZA A")).grid(row=0, column=0)
        ttk.Button(f, text="Cerrar al cubo", command=lambda: self.enviar("PINZA C")).grid(row=0, column=1)
        self.lado = tk.DoubleVar(value=modelo.P["CUBO_MM_INI"])
        ttk.Label(f, text="lado (mm)").grid(row=1, column=0); ttk.Entry(f, textvariable=self.lado, width=6).grid(row=1, column=1)
        ttk.Button(f, text="Fijar", command=self.fijar_cubo).grid(row=1, column=2)

        f = ttk.LabelFrame(izq, text="Consola", padding=6); f.pack(fill="both", expand=True)
        self.consola = tk.Text(f, width=50, height=14, font=("Consolas", 9)); self.consola.pack(fill="both", expand=True)
        self.entrada = ttk.Entry(f); self.entrada.pack(fill="x", pady=(4, 0))
        self.entrada.bind("<Return>", lambda e: (self.enviar(self.entrada.get()), self.entrada.delete(0, "end")))

        ttk.Label(der, text="Mesa vista desde arriba: clic izquierdo = cubo, clic derecho = pila "
                            "(x hacia arriba, y hacia la izquierda)").pack(anchor="w")
        self.lienzo = tk.Canvas(der, width=ANCHO, height=ALTO, bg="white", highlightthickness=1)
        self.lienzo.pack()
        self.lienzo.bind("<Button-1>", self.clic_cubo); self.lienzo.bind("<Button-3>", self.clic_pila)
        b = ttk.Frame(der); b.pack(fill="x", pady=4)
        ttk.Button(b, text="Apilar", command=self.apilar).pack(side="left")
        ttk.Button(b, text="Coger el 1º", command=self.coger_primero).pack(side="left", padx=4)
        ttk.Button(b, text="Borrar", command=self.borrar).pack(side="left")
        ttk.Button(b, text="Cancelar tarea", command=lambda: self.enviar("X")).pack(side="left", padx=4)
        self.dibujar()

    # ------------------------------------------------------------------------------------------ mesa
    def a_pantalla(self, x, y):         # x hacia arriba, y hacia la izquierda; base abajo en el centro
        return ANCHO / 2 - y * ESCALA, BASE_Y - x * ESCALA

    def a_mesa(self, px, py):
        return (BASE_Y - py) / ESCALA, (ANCHO / 2 - px) / ESCALA

    def dibujar(self):
        c = self.lienzo; c.delete("all")
        lado = self.lado.get() if self.lado.get() > 0 else 40
        rmin, rmax = modelo.alcance_cubo(lado, max(len(self.cubos), 1))
        lmin, lmax = modelo.P["LIM_MIN"][0], modelo.P["LIM_MAX"][0]
        cx, cy = self.a_pantalla(0, 0)
        def sector(r, color):
            c.create_arc(cx - r * ESCALA, cy - r * ESCALA, cx + r * ESCALA, cy + r * ESCALA, start=90 + lmin,
                         extent=lmax - lmin, fill=color, outline="")
        if rmin is not None:
            sector(rmax, "#dcefdc"); sector(min(ZONA_RECOMENDADA[1], rmax), "#b9dfb9")
            sector(max(ZONA_RECOMENDADA[0], rmin), "#dcefdc"); sector(rmin, "white")
        for r in range(100, 401, 100):
            c.create_oval(cx - r * ESCALA, cy - r * ESCALA, cx + r * ESCALA, cy + r * ESCALA, outline="#e2e2e2")
            c.create_text(cx + 4, cy - r * ESCALA - 7, text=f"{r} mm", fill="#999", anchor="w", font=("Segoe UI", 8))
        c.create_oval(cx - 82 * ESCALA, cy - 82 * ESCALA, cx + 82 * ESCALA, cy + 82 * ESCALA, fill="#cfd3d8", outline="#9aa3ad")
        c.create_text(cx, cy, text="base")
        s = lado * ESCALA / 2
        for i, (x, y) in enumerate(self.cubos):
            px, py = self.a_pantalla(x, y)
            c.create_rectangle(px - s, py - s, px + s, py + s, fill="#7fa7d9", outline="#2f5d8a")
            c.create_text(px, py, text=str(i + 1), font=("Segoe UI", 10, "bold"))
        if self.pila:
            px, py = self.a_pantalla(*self.pila)
            c.create_rectangle(px - s, py - s, px + s, py + s, outline="#2e7d32", width=3, dash=(4, 2))
            c.create_text(px, py, text="pila", fill="#2e7d32", font=("Segoe UI", 9, "bold"))
        if "tcp" in self.estado:
            x, y, _ = self.estado["tcp"]; px, py = self.a_pantalla(x, y)
            c.create_oval(px - 6, py - 6, px + 6, py + 6, fill="#d62728", outline="")
            c.create_line(cx, cy, px, py, fill="#d62728", dash=(3, 3))

    def _alcanzable(self, x, y):
        lado = self.lado.get()
        return modelo.inversa(x, y, lado / 2 + modelo.P["Z_AGARRE_MM"]) and modelo.inversa(x, y, lado + modelo.P["ALTURA_SEGURA_MM"])

    def clic_cubo(self, e):
        x, y = self.a_mesa(e.x, e.y)
        if not self._alcanzable(x, y):
            messagebox.showwarning("Fuera de alcance", f"({x:.0f}, {y:.0f}) mm no se alcanza"); return
        if len(self.cubos) >= 6:
            messagebox.showwarning("Máximo", "Como mucho 6 cubos"); return
        self.cubos.append((round(x), round(y))); self.dibujar()

    def clic_pila(self, e):
        x, y = self.a_mesa(e.x, e.y)
        if not self._alcanzable(x, y):
            messagebox.showwarning("Fuera de alcance", f"({x:.0f}, {y:.0f}) mm no se alcanza"); return
        self.pila = (round(x), round(y)); self.dibujar()

    def borrar(self):
        self.cubos, self.pila = [], None; self.dibujar()

    def apilar(self):
        if not self.cubos or not self.pila:
            messagebox.showinfo("Apilar", "Marca al menos un cubo (clic izquierdo) y la pila (clic derecho)"); return
        self.enviar("APILAR {} {} ".format(*self.pila) + " ".join(f"{x} {y}" for x, y in self.cubos))

    def coger_primero(self):
        if self.cubos:
            self.enviar("COGER {} {}".format(*self.cubos[0]))

    def fijar_cubo(self):
        self.enviar(f"CUBO {self.lado.get():g}"); self.dibujar()

    # ------------------------------------------------------------------------------------------ serie
    def conectar(self):
        if self.brazo:
            self.brazo.cerrar(); self.brazo = None
            self.bt_con.config(text="Conectar"); self.lb_estado.config(text="desconectado"); return
        try:
            self.lb_estado.config(text="conectando..."); self.update()
            self.brazo = Brazo(self.cb_puerto.get())
            self.bt_con.config(text="Desconectar"); self.lb_estado.config(text="conectado")
        except Exception as ex:
            messagebox.showerror("Puerto serie", str(ex)); self.lb_estado.config(text="desconectado")

    def enviar(self, comando):
        if not comando.strip():
            return
        if not self.brazo:
            messagebox.showinfo("Brazo", "Conecta primero el puerto serie"); return
        self.brazo.enviar(comando)
        self._consola(">> " + comando)

    def paro(self):
        if self.brazo:
            self.brazo.enviar("X"); self._consola(">> X (paro)")

    def _consola(self, t):
        self.consola.insert("end", t + "\n"); self.consola.see("end")

    def _sondear(self):
        if self.brazo:
            self.brazo.enviar("ESTADO")
        self.after(500, self._sondear)

    def _leer(self):
        if self.brazo:
            bloque = []
            try:
                while True:
                    bloque.append(self.brazo.lineas.get_nowait())
            except queue.Empty:
                pass
            for l in bloque:
                if l.startswith("L,") or l.startswith("CSV"):
                    continue
                if l.startswith(("ESTADO", "q=", "TCP=")):          # respuesta a ESTADO (cada 0,5 s)
                    self._estado(l); continue
                self._consola(l)
        self.after(100, self._leer)

    def _estado(self, l):
        num = lambda s: [float(v) for v in s.split()]
        if l.startswith("ESTADO"):
            m = dict(re.findall(r"(\w+)=(\S+)", l))
            modos = ["PARADO", "CONTROL", "HOMING", "PRUEBA", "AUTOTUNE", "FALLO"]
            self.estado.update(modo=modos[int(m.get("modo", 0))], home=m.get("home") == "1", mov=m.get("mov") == "1")
        elif l.startswith("q="):
            m = re.match(r"\s*q=(.*?)\s+ref=(.*?)\s+pwm=(.*?)\s+I=(.*)", l)
            if m:
                self.estado.update(q=num(m.group(1)), ref=num(m.group(2)), pwm=num(m.group(3)))
        else:
            m = re.match(r"\s*TCP=(\S+) (\S+) (\S+).*pinza=(\S+) cubo=(\S+)", l)
            if m:
                self.estado.update(tcp=tuple(float(m.group(i)) for i in (1, 2, 3)), pinza=float(m.group(4)))
                self._pintar_estado()

    def _pintar_estado(self):
        e = self.estado
        col = {"FALLO": "#c62828", "CONTROL": "#2e7d32"}.get(e.get("modo"), "#444")
        self.lb_estado.config(text=f"{e.get('modo')}  {'referenciado' if e.get('home') else 'sin HOME'}"
                                   f"{'  · moviendo' if e.get('mov') else ''}", foreground=col)
        t = self.txt_estado; t.delete("1.0", "end")
        if "q" in e:
            t.insert("end", "           base   hombro    codo\n")
            t.insert("end", "ángulo  " + "".join(f"{v:8.1f}" for v in e["q"]) + "\n")
            t.insert("end", "consigna" + "".join(f"{v:8.1f}" for v in e["ref"]) + "\n")
            t.insert("end", "PWM     " + "".join(f"{v:8.0f}" for v in e["pwm"]) + "\n")
        if "tcp" in e:
            t.insert("end", "pinza en x={:.0f} y={:.0f} z={:.0f} mm\napertura {:.0f} mm".format(*e["tcp"], e["pinza"]))
        self.dibujar()


if __name__ == "__main__":
    App().mainloop()
