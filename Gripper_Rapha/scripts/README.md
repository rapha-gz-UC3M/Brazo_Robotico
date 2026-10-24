# Scripts

Regeneran todo lo de `Gripper_Rapha` a partir de los STL del repo. Los archivos de Vasil
(`../Arm_Vasil/Brazo_modificado_STL`) y de Ignacio (`../Base_Ignacio`) solo se leen.

```
pip install trimesh manifold3d shapely scipy rtree olefile matplotlib
python scripts/generar_todo.py          # desde la carpeta Gripper_Rapha
```

`generar_todo.py` ejecuta, en este orden:

| Script | Qué hace | Escribe en |
|---|---|---|
| `generar_gripper.py` | Gripper ×1,5 y acople a la punta del antebrazo; comprueba colisiones y apertura (`--step`: STEP del gripper montado) | `IMPRIMIR/3_gripper`, `GRIPPER/comprobacion` |
| `preparar_impresion.py` | Piezas de Vasil e Ignacio que se usan sin cambios: a mm y orientadas | `IMPRIMIR/1_base`, `IMPRIMIR/2_brazo` |
| `piezas_modificadas.py` | Piezas cambiadas y nuevas (shields, paletas, coronas, piñones, base…) | `IMPRIMIR/`, `ENSAMBLAJE/piezas_colocadas` |
| `montar_ensamblaje.py` | Brazo entero, motores, interferencias y vistas (`--barrido`: recorre el hombro) | `ENSAMBLAJE/` |

Auxiliares (los llaman los anteriores): `rutas.py` (carpetas y utilidades comunes), `build_gripper.py`,
`build_mount_vasil.py`, `forearm_ref.py`, `par_cache.py`, `servo_chk.py`, `check_montaje.py`, `sweep.py`,
`build_base_sup_imprimible.py` y `stl_to_step_asm.py`.

Las cotas que se pueden ajustar están al principio de cada script: las del acople del gripper en
`build_mount_vasil.py`, y las de los motores y los cambios del brazo en `piezas_modificadas.py` y
`montar_ensamblaje.py`.
