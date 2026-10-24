"""Regenera el gripper x1,5 y su acople a la punta del antebrazo de Vasil (placas Brazo Parte 2_1 y 2.2_4).

Uso (desde Gripper_Rapha):
    python scripts/generar_gripper.py            # piezas + comprobaciones
    python scripts/generar_gripper.py --step     # además el STEP del gripper montado (pip install cadquery-ocp)

Lee:     GRIPPER/original/gripper_superbtech/*.stl  y las dos placas de ../Arm_Vasil/Brazo_modificado_STL
         (o el .par de ../Arm_Vasil/Brazo_modificado). Si no están, usa las copias de GRIPPER/comprobacion/REF_*.
Escribe: IMPRIMIR/3_gripper/       las 10 piezas, en mm y orientadas para imprimir
         GRIPPER/comprobacion/     las piezas colocadas sobre las placas de Vasil (ASM_*) y las placas (REF_*)
         GRIPPER/build/            intermedios (no se suben a git)
"""
import subprocess, sys, os, shutil, glob, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rutas import SCRIPTS, REPO, IMP_GRIP, GRIP_CHK, GRIP_ORIG, BUILD, orient, export
def run(script, *args):
    print(f'\n>>> {script}', flush=True)
    subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], check=True)

MOUNT = os.path.join(BUILD, 'acople'); os.makedirs(MOUNT, exist_ok=True)
VASIL = os.path.join(REPO, 'Arm_Vasil')
refs = {}
for plate, name, ref in (('A', 'Brazo Parte 2_1', 'REF_Brazo_Parte_2_1_Vasil.stl'),
                         ('B', 'Brazo Parte 2.2_4', 'REF_Brazo_Parte_2.2_4_Vasil.stl')):
    refs[plate] = os.path.join(GRIP_CHK, ref)
    for src in (os.path.join(VASIL, 'Brazo_modificado_STL', name + '.stl'),
                os.path.join(VASIL, 'Brazo_modificado', name + '.par')):
        if os.path.exists(src):
            run('forearm_ref.py', plate, src, refs[plate]); break
    else:
        print(f'\n(no se encuentra {name}; se usa {refs[plate]})')

run('build_gripper.py', GRIP_ORIG, BUILD)
run('servo_chk.py', BUILD)
run('build_mount_vasil.py', refs['A'], refs['B'], BUILD, MOUNT)
for n in ('acople_punta_vasil', 'casquillo_punta', 'contraplaca_acople'):
    shutil.copy(os.path.join(MOUNT, n + '_x1.5.stl'), os.path.join(GRIP_CHK, f'ASM_{n}.stl'))
for f in glob.glob(os.path.join(MOUNT, 'ASM_*.stl')):
    shutil.copy(f, os.path.join(GRIP_CHK, os.path.basename(f)))

# piezas para imprimir: orientadas y apoyadas en la cama
for name, up, src in [('acople_punta', [-1, 0, 0], MOUNT), ('casquillo_punta', [0, 0, -1], MOUNT),
                      ('contraplaca_acople', [0, 0, 1], MOUNT), ('base_plate', [0, 1, 0], BUILD),
                      ('gear_left', [0, 1, 0], BUILD), ('gear_right', [0, 1, 0], BUILD), ('arm_left', [0, 1, 0], BUILD),
                      ('arm_right', [0, 1, 0], BUILD), ('jaw_left', [0, -1, 0], BUILD), ('jaw_right', [0, -1, 0], BUILD)]:
    f = os.path.join(src, ('acople_punta_vasil' if name == 'acople_punta' else name) + '_x1.5.stl')
    export(orient(trimesh.load(f), up), os.path.join(IMP_GRIP, name + '.stl'))

run('check_montaje.py', MOUNT, refs['A'], refs['B'])   # debe acabar en "colisiones: 0"
run('sweep.py', BUILD)                                  # apertura de 0° a 90° sin colisiones
if '--step' in sys.argv:
    run('stl_to_step_asm.py', GRIP_CHK, os.path.join(BUILD, 'Ensamblaje_Gripper_Brazo_Vasil_x1.5.step'))
print('\nListo: IMPRIMIR/3_gripper y GRIPPER/comprobacion actualizados.')
