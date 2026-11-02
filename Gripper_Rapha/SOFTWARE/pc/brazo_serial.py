"""Conexión serie con el brazo (Arduino UNO a 115200 baudios) y utilidades compartidas por las herramientas.

Las líneas que empiezan por "L," son datos de registro a 50 Hz:
    L,t_ms,ref0,q0,u0,ref1,q1,u1,ref2,q2,u2      (0 base, 1 hombro, 2 codo; grados y PWM)
"FIN" marca el final de un registro.
"""
import queue
import threading
import time

import serial
import serial.tools.list_ports

COLUMNAS = ["t_ms", "ref0", "q0", "u0", "ref1", "q1", "u1", "ref2", "q2", "u2"]


def puertos():
    """Lista de puertos serie disponibles (en Windows, COM3, COM4...)."""
    return [p.device for p in serial.tools.list_ports.comports()]


class Brazo:
    """Abre el puerto y lee en segundo plano. Las líneas llegan a self.lineas (cola)."""

    def __init__(self, puerto, baudios=115200):
        self.ser = serial.Serial(puerto, baudios, timeout=0.1)
        time.sleep(2.0)                      # el UNO se reinicia al abrir el puerto
        self.lineas = queue.Queue()
        self._vivo = True
        threading.Thread(target=self._leer, daemon=True).start()

    def _leer(self):
        buf = b""
        while self._vivo:
            try:
                buf += self.ser.read(256)
            except serial.SerialException:
                break
            while b"\n" in buf:
                linea, buf = buf.split(b"\n", 1)
                self.lineas.put(linea.decode(errors="replace").strip())

    def enviar(self, comando):
        self.ser.write((comando.strip() + "\n").encode())

    def esperar(self, condicion, timeout=10.0, eco=print):
        """Lee líneas hasta que condicion(linea) sea cierta. Devuelve las líneas leídas."""
        leidas, fin = [], time.time() + timeout
        while time.time() < fin:
            try:
                l = self.lineas.get(timeout=0.1)
            except queue.Empty:
                continue
            leidas.append(l)
            if eco and not l.startswith("L,"):
                eco(l)
            if condicion(l):
                break
        return leidas

    def registro(self, comando, timeout=60.0):
        """Manda un comando que registra (ESCALON, PWM, AUTOTUNE) y devuelve las filas hasta FIN."""
        while not self.lineas.empty():
            self.lineas.get_nowait()
        self.enviar(comando)
        lineas = self.esperar(lambda l: l == "FIN" or l.startswith("!!"), timeout)
        filas = [list(map(float, l.split(",")[1:])) for l in lineas if l.startswith("L,")]
        extra = [l for l in lineas if not l.startswith("L,")]
        return filas, extra

    def cerrar(self):
        self._vivo = False
        self.ser.close()


def leer_csv(ruta):
    """Lee un CSV guardado por registrar_pid.py (o líneas L, copiadas del monitor serie)."""
    import numpy as np
    filas = []
    for l in open(ruta, encoding="utf-8"):
        l = l.strip()
        if l.startswith("L,"):
            l = l[2:]
        if not l or not (l[0].isdigit() or l[0] == "-"):
            continue
        filas.append([float(x) for x in l.split(",")])
    return np.array(filas)
