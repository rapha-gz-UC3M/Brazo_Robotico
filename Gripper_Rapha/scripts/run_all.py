"""Regenera el gripper x1,5 y su acople a la punta del antebrazo de Vasil.

Uso (desde la carpeta Gripper_Rapha):
    pip install trimesh manifold3d shapely scipy rtree olefile
    python scripts/run_all.py            # STL + comprobaciones
    python scripts/run_all.py --step     # además el ensamblaje STEP (pip install cadquery-ocp)

Entradas:
  original/gripper_superbtech/*.stl                         pinza original (thing:5149951)
  ../Arm_Vasil/Brazo_modificado_STL/Brazo Parte 2_1.stl     antebrazo de Vasil (solo se lee); si no está,
  ../Arm_Vasil/Brazo_modificado/Brazo Parte 2_1.par         se prueba con el .par y, si tampoco,
  referencia/Brazo_Parte_2_1_Vasil.stl                      con la copia de referencia
Salidas: imprimir/, comprobacion/, referencia/ (y build/ con intermedios)
"""
import subprocess, sys, os, shutil, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
P = lambda *a: os.path.join(ROOT, *a)
def run(script, *args):
    print(f'\n>>> {script}', flush=True)
    subprocess.run([sys.executable, os.path.join(HERE, script), *args], check=True)

BUILD = P('build'); MOUNT = P('build', 'acople')
for d in (BUILD, MOUNT, P('imprimir'), P('comprobacion'), P('referencia')): os.makedirs(d, exist_ok=True)

VASIL = os.path.join(os.path.dirname(ROOT), 'Arm_Vasil')
ref = P('referencia', 'Brazo_Parte_2_1_Vasil.stl')
for src in (os.path.join(VASIL, 'Brazo_modificado_STL', 'Brazo Parte 2_1.stl'),
            os.path.join(VASIL, 'Brazo_modificado', 'Brazo Parte 2_1.par')):
    if os.path.exists(src):
        run('forearm_ref.py', src, ref); break
else:
    print(f'\n(no se encuentra el antebrazo de Vasil; se usa {os.path.relpath(ref, ROOT)})')

run('build_gripper.py', P('original', 'gripper_superbtech'), BUILD)
run('servo_chk.py', BUILD)
run('build_mount_vasil.py', ref, BUILD, MOUNT)

for f in glob.glob(os.path.join(BUILD, '*_x1.5.stl')):
    shutil.copy(f, P('imprimir', os.path.basename(f)))
for n in ('acople_punta_vasil_x1.5.stl', 'contraplaca_acople_x1.5.stl'):
    shutil.copy(os.path.join(MOUNT, n), P('imprimir', n))
for f in glob.glob(os.path.join(MOUNT, 'ASM_*.stl')):
    shutil.copy(f, P('comprobacion', os.path.basename(f)))
shutil.copy(os.path.join(MOUNT, 'acople_punta_vasil_x1.5.stl'), P('comprobacion', 'ASM_acople_punta_vasil.stl'))
shutil.copy(os.path.join(MOUNT, 'contraplaca_acople_x1.5.stl'), P('comprobacion', 'ASM_contraplaca_acople.stl'))
shutil.copy(ref, P('comprobacion', 'REF_Brazo_Parte_2_1_Vasil.stl'))

run('check_montaje.py', MOUNT, ref)     # colisiones con el antebrazo (debe acabar en "colisiones: 0")
run('sweep.py', BUILD)                  # apertura de 0° a 90° sin colisiones
if '--step' in sys.argv:
    run('stl_to_step_asm.py', P('comprobacion'), P('build', 'Ensamblaje_Gripper_Brazo_Vasil_x1.5.step'))
print('\nListo: imprimir/ y comprobacion/ actualizados.')
