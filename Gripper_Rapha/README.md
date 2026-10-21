# Gripper (Rapha) – pinza con servo MG90S, escala x1,5

Pinza de mordazas paralelas accionada por un servo **MG90S**, fijada **sin grado de libertad** a la punta
del antebrazo de Vasil (`Arm_Vasil/Brazo_modificado/Brazo Parte 2_1.par`, la versión definitiva). **No modifica ninguna pieza de Vasil**: el acople
abraza el extremo del antebrazo usando el agujero Ø15 y el avellanado Ø24 que ya tiene.
Todo está a **escala x1,5**, salvo lo que encaja con piezas compradas (servo y tornillos), a tamaño real.

![Montaje en el antebrazo](imagenes/montaje_antebrazo_vasil.png)

## Carpetas

| Carpeta | Contenido |
|---|---|
| `imprimir/` | STL listos para laminar, 1 unidad de cada |
| `solid_edge/Ensamblaje_Gripper_Brazo_Vasil/` | Ensamblaje STEP para abrir en Solid Edge: antebrazo real de Vasil (de `Brazo_modificado_STL`) + acople + contraplaca + gripper + servo |
| `comprobacion/` | Los mismos componentes en STL, colocados en las coordenadas del `.par` de Vasil |
| `referencia/` | `Brazo_Parte_2_1_Vasil.stl`: el STL de Vasil pasado a mm, para comprobar (**no se imprime**; lo imprime Vasil) |
| `original/` | STL de partida de la pinza |
| `scripts/` | Código Python que genera todas las piezas y las comprobaciones |
| `imagenes/` | Vistas del montaje |

## Interfaz con el brazo de Vasil

Medida en `Arm_Vasil/Brazo_modificado_STL/Brazo Parte 2_1.stl` (= `Brazo_modificado/Brazo Parte 2_1.par`), en las coordenadas
de la propia pieza, en mm. `scripts/forearm_ref.py` comprueba estas cotas cada vez que se regenera:

- Antebrazo de 150 mm entre centros, placa de 30 mm de ancho y 7,5 mm de grosor (z de −27 a −19,5).
- Punta en x = 150: agujero pasante **Ø15** y avellanado **Ø24 × 4,5 mm** por la cara del rebaje (z = −19,5).

El acople es un "vaso" que entra por la cara del rebaje:
- Un **resalte Ø23,5** encaja en el avellanado Ø24 y centra el acople.
- Unos **labios laterales** abrazan los cantos de la placa con 0,3 mm de holgura e impiden el giro.
- Por la cara plana va la **contraplaca**, y un **tornillo M5** aprieta el conjunto a través del agujero Ø15.
- En el `.par` de Vasil, el gripper queda alineado con el eje del antebrazo y las mordazas abren en la dirección del
  eje de las articulaciones, es decir, en horizontal.

En Solid Edge, si se inserta el `.par` real de Vasil en el origen del ensamblaje STEP, coincide con la
pieza de referencia.

## Piezas a imprimir

| Archivo | Qué es | Notas |
|---|---|---|
| `base_plate_x1.5` | Placa base | Hueco del MG90S (12,6 × 23,2 mm) y taladros guía Ø1,8 a tamaño real; pared trasera con 4 × M3 |
| `gear_left_x1.5`, `gear_right_x1.5` | Engranajes-manivela | `gear_right` va al estriado del servo (Ø4,9) con cajeado Ø7 para el tornillo |
| `arm_left_x1.5`, `arm_right_x1.5` | Bielas | |
| `jaw_left_x1.5`, `jaw_right_x1.5` | Mordazas | Mejor agarre con goma, TPU o cinta antideslizante |
| `acople_punta_vasil_x1.5` | Une el gripper a la punta del antebrazo | Imprimir con la brida (cara de apoyo del gripper) en la cama; soporte solo dentro del vaso. 4 perímetros, ≥40 % relleno |
| `contraplaca_acople_x1.5` | Arandela grande bajo la cara plana del antebrazo | Plana, sin soportes |

## Montaje

1. Servo en la placa base con sus tornillos autorroscantes; `gear_right` al estriado con el tornillo del servo.
2. Engranaje izquierdo y bielas a la placa, y mordazas a engranajes y bielas, con M3 × 20 y tuerca autoblocante
   (apretar sin frenar el giro).
3. Pared del gripper a la brida del acople con 4 × M3 × 16 (tuercas en los alojamientos hexagonales de la parte
   trasera de la brida).
4. Encajar el acople en la punta del antebrazo por la cara del avellanado; contraplaca por la cara plana.
5. Tornillo M5 × 20 desde la contraplaca, con la tuerca en el alojamiento hexagonal de arriba del acople.

## Tornillería

| Uso | Cant. | Tornillo |
|---|---|---|
| Pivotes en la placa (engranaje izq. + 2 bielas) | 3 | M3 × 20 + tuerca autoblocante |
| Pivotes de las mordazas | 4 | M3 × 20 + tuerca autoblocante |
| Gripper ↔ acople | 4 | M3 × 16 + tuerca M3 |
| Acople ↔ antebrazo | 1 | M5 × 20 + tuerca M5 (+ arandela bajo la cabeza) |
| Servo a la placa | 2 | Los que trae el MG90S |
| Engranaje al eje del servo | 1 | El del horn del MG90S + arandela |

## Datos del mecanismo

- Paralelogramo: manivela y biela de 45 mm entre ejes, las mordazas no giran.
- Engranajes de 32 dientes (sector), 33 mm entre centros, módulo ≈ 1,03.
- Hueco entre mordazas según el giro del servo: 2,3 mm (0°), ~47 mm (30°), ~66 mm (45°), ~80 mm (60°).
  Sin colisiones de 0° a 90°; los dientes siguen engranados hasta ~120°.
- Fuerza estimada con MG90S (1,8–2,2 kg·cm): ~2–2,4 N por mordaza, para objetos de ~100–150 g.
- Las mordazas acaban ~160 mm más allá del eje de la punta del antebrazo.
- Volumen impreso: gripper ~73 cm³ + acople y contraplaca ~37 cm³ (con 40 % de relleno, unos 80–90 g en PLA)
  + servo 13,4 g + tornillería ~15 g. Este peso lo tiene que sostener el motor del codo.

## Regenerar las piezas

```
pip install trimesh manifold3d shapely scipy rtree olefile
python scripts/run_all.py            # rehace imprimir/ y comprobacion/ y pasa las comprobaciones
python scripts/run_all.py --step     # además el STEP del ensamblaje (pip install cadquery-ocp)
```

`run_all.py` lee el antebrazo de `../Arm_Vasil/Brazo_modificado_STL/Brazo Parte 2_1.stl` (o, si no está, del `.par`
de `Brazo_modificado`), solo lectura, y comprueba que la punta sigue igual; si Vasil la cambia, avisa.

> Los STL de `Arm_Vasil/Brazo_modificado_STL` están exportados en **pulgadas** (opción por defecto de Solid Edge).
> Los scripts lo detectan, pero **al laminarlos hay que escalarlos ×25,4** o reexportarlos en mm. Las cotas del acople están al principio de `scripts/build_mount_vasil.py`.

## Base de partida y licencias

| Qué | Origen | Licencia |
|---|---|---|
| Pinza | *Servo Gripper Arm for SG90/MG90S*, SuperbTech – [thing:5149951](https://www.thingiverse.com/thing:5149951) | CC BY (citar al autor) |

## Pendiente de confirmar al montar

- La altura del estriado del MG90S respecto a sus orejetas se ha tomado del diseño original; si el engranaje
  queda flojo o alto, se corrige con una arandela.
- Comprobar con Vasil que nada de su montaje ocupa la punta del antebrazo (en su carpeta actual no hay ninguna
  pieza ahí).
