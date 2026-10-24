"""Prepara para imprimir las piezas de Vasil e Ignacio que se usan SIN CAMBIOS (solo pasadas a mm y orientadas).

Lee (solo lectura): ../Arm_Vasil/Brazo_modificado_STL/*.stl y ../Base_Ignacio/*.stl (Solid Edge, en pulgadas)
Escribe:            IMPRIMIR/1_base/BASE_TAPA_INF.stl
                    IMPRIMIR/2_brazo/Brazo_Parte_2_1, Brazo_Parte_2.2_4, Eje_Parte_1, Eje_Parte_2, Sujetador_de_eje_x2
Las piezas cambiadas las hace piezas_modificadas.py. No se imprime Eje Parte 3 (en la punta va el gripper).

Uso (desde Gripper_Rapha):  python scripts/preparar_impresion.py
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rutas import VAS, IGN, IMP_BASE, IMP_BRAZO, load_mm, orient, row, export

def save(folder, name, m):
    export(m, os.path.join(folder, name + '.stl')); print(f'  {os.path.basename(folder)}/{name}.stl  {np.round(m.extents, 1).tolist()} mm')

save(IMP_BASE, 'BASE_TAPA_INF', orient(load_mm(os.path.join(IGN, 'BASE_TAPA_INF.stl')), [0, 1, 0]))
V = lambda n: load_mm(os.path.join(VAS, n + '.stl'))
for src, name, up in [('Brazo Parte 2_1', 'Brazo_Parte_2_1', [0, 0, 1]), ('Brazo Parte 2.2_4', 'Brazo_Parte_2.2_4', [0, 0, -1]),
                      ('Eje Parte 1 - 2.0_1', 'Eje_Parte_1', [0, 0, 1]),
                      # el agujero del extremo de Eje Parte 2 (Ø6 con un nervio) es el acople del potenciómetro del codo
                      ('Eje Parte 2 - 2.0_1', 'Eje_Parte_2', [0, 0, 1])]:
    save(IMP_BRAZO, name, orient(V(src), up))
clip = orient(V('Sujetador de eje_2'), [0, 0, 1])
save(IMP_BRAZO, 'Sujetador_de_eje_x2', row([clip, clip], gap=8.0))
print('preparar_impresion: hecho')
