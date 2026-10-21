"""Regenera el gripper x1,5 y su acople a la punta del antebrazo de Vasil (dos placas: Parte 2_1 y Parte 2.2_4).

Uso (desde la carpeta Gripper_Rapha):
    pip install trimesh manifold3d shapely scipy rtree olefile
    python scripts/run_all.py            # STL + comprobaciones
    python scripts/run_all.py --step     # además el ensamblaje STEP (pip install cadquery-ocp)

Entradas (solo lectura):
  original/gripper_superbtech/*.stl                               pinza original (thing:5149951)
  ../Arm_Vasil/Brazo_modificado_STL/Brazo Parte 2_1.stl  (o el .par de Brazo_modificado)    placa A
  ../Arm_Vasil/Brazo_modificado_STL/Brazo Parte 2.2_4.stl (o el .par de Brazo_modificado)   placa B
  si no se encuentran, se usan las copias de referencia/
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
refs = {}
for plate, name, ref in (('A', 'Brazo Parte 2_1', 'Brazo_Parte_2_1_Vasil.stl'),
                         ('B', 'Brazo Parte 2.2_4', 'Brazo_Parte_2.2_4_Vasil.stl')):
    refs[plate] = P('referencia', ref)
    for src in (os.path.join(VASIL, 'Brazo_modificado_STL', name + '.stl'),
                os.path.join(VASIL, 'Brazo_modificado', name + '.par')):
        if os.path.exists(src):
            run('forearm_ref.py', plate, src, refs[plate]); break
    else:
        print(f'\n(no se encuentra {name}; se usa {os.path.relpath(refs[plate], ROOT)})')

run('build_gripper.py', P('original', 'gripper_superbtech'), BUILD)
run('servo_chk.py', BUILD)
run('build_mount_vasil.py', refs['A'], refs['B'], BUILD, MOUNT)

for f in glob.glob(os.path.join(BUILD, '*_x1.5.stl')):
    shutil.copy(f, P('imprimir', os.path.basename(f)))
for n in ('acople_punta_vasil', 'casquillo_punta', 'contraplaca_acople'):
    shutil.copy(os.path.join(MOUNT, n + '_x1.5.stl'), P('imprimir', n + '_x1.5.stl'))
    shutil.copy(os.path.join(MOUNT, n + '_x1.5.stl'), P('comprobacion', f'ASM_{n}.stl'))
for f in glob.glob(os.path.join(MOUNT, 'ASM_*.stl')):
    shutil.copy(f, P('comprobacion', os.path.basename(f)))
shutil.copy(refs['A'], P('comprobacion', 'REF_Brazo_Parte_2_1_Vasil.stl'))
shutil.copy(refs['B'], P('comprobacion', 'REF_Brazo_Parte_2.2_4_Vasil.stl'))

run('check_montaje.py', MOUNT, refs['A'], refs['B'])   # debe acabar en "colisiones: 0"
run('sweep.py', BUILD)                                  # apertura de 0° a 90° sin colisiones
if os.path.exists(P('ensamblaje_completo', 'transformaciones.json')):
    run('montar_ensamblaje.py')                         # brazo entero en ensamblaje_completo/
if '--step' in sys.argv:
    run('stl_to_step_asm.py', P('comprobacion'), P('build', 'Ensamblaje_Gripper_Brazo_Vasil_x1.5.step'))
print('\nListo: imprimir/ y comprobacion/ actualizados.')
