"""Regenera TODO lo de Gripper_Rapha en orden: gripper, piezas sin cambios, piezas modificadas y ensamblaje.

Uso (desde Gripper_Rapha):
    pip install trimesh manifold3d shapely scipy rtree olefile matplotlib
    python scripts/generar_todo.py
"""
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
for s in ('generar_gripper.py', 'preparar_impresion.py', 'piezas_modificadas.py', 'montar_ensamblaje.py'):
    print(f'\n========== {s} ==========', flush=True)
    subprocess.run([sys.executable, os.path.join(HERE, s)], check=True)
print('\nListo: IMPRIMIR/, ENSAMBLAJE/ y GRIPPER/comprobacion actualizados.')
