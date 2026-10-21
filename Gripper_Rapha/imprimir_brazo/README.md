# Todo lo que hay que imprimir del brazo

Todas las piezas están en **mm**, ya apoyadas en la cama (z = 0) y en la orientación recomendada: importar e
imprimir, **sin escalar ni girar**. Se generan con `python scripts/preparar_impresion.py` a partir de los STL de
Vasil y de Ignacio, que no se modifican.

Configuración general: PLA, boquilla de 0,4 mm, 3–4 perímetros, compensación de pata de elefante activada.
La cama tiene que medir al menos 220 mm (las piezas `Brazo Parte 1` miden 217,5 mm).

## 1_base_Ignacio

| Archivo | Cant. | Soportes | Relleno | Notas |
|---|---|---|---|---|
| `BASE_TAPA_INF` | 1 | **Sí**, pocos | 15–20 % | Van debajo de las 4 repisas interiores de los finales de carrera (2 a cada lado, con un hueco de 6,7 mm entre ellas) y en el puente de la torre del motor. Lo demás no los necesita |
| `BASE_TAPA_SUP_imprimible` | 1 | **Sí**, en árbol y solo desde la cama | 20–25 % | Solo bajo el disco: la pieza está abierta por abajo y se quitan bien. **Modificada** (ver `base_sup_imprimible/`) |
| `BASE_TAPA_SUP_pestana` | 1 | No | 100 % | Se pega por debajo del disco de `SUP` con epoxi. Es la pieza que acciona los finales de carrera |
| `Pieza_Eje_Giro_Base` | 1 | No | 100 % | Agujero en D para el eje del JGB37 |

## 2_brazo_Vasil

| Archivo | Cant. | Soportes | Relleno | Notas |
|---|---|---|---|---|
| `Brazo_Parte_1_1`, `Brazo_Parte_1.1_2.0_1`, `Brazo_Parte_2_1`, `Brazo_Parte_2.2_4` | 1 de cada | No | 30–40 % | Planas |
| `Base_Tapa_Superior_Paleta_1`, `Paleta_2` | 1 de cada | No | 30 % | Planas |
| `Shield_1_imprimible`, `Shield_2_imprimible` | 1 de cada | No | 30 % | **Modificadas**: los separadores van aparte (ver `shields_imprimibles/`) |
| `Shield_1_separadores_x4` | 1 archivo = 4 tubos | No | 100 % | Entre `Shield 1` y `Paleta 2` |
| `Shield_2_separadores_x3` | 1 archivo = 3 tubos | No | 100 % | Entre `Shield 2` y `Brazo Parte 1.1` |
| `Eje_Parte_1_2.0_1` | 1 | **Sí**, en los dos escalones (~5 mm) | 100 % | De pie. 5–10 °C más caliente para que las capas peguen bien |
| `Eje_Parte_2_2.0_agujero_D_6.15` | 1 | **Sí**, en los escalones | 100 % | De pie. **Modificado**: ver más abajo |
| `Corona_30_dientes_modulo_2_1` | 1 | No | 40 %, 5 perímetros | Capa de 0,12–0,16 mm. El agujero va justo sobre el eje: puede necesitar lija |
| `Pinon_10_dientes_modulo_3_agujero_D_6.15` | 1 | No | 100 % | Capa de 0,12–0,16 mm. **Modificado**: ver más abajo |
| `Sujetador_de_eje_x2` | 1 archivo = 2 clips | No | 100 % | Mejor en PETG. Si puedes, imprime uno o dos de más |

**No se imprime `Eje Parte 3`**: en la punta va el casquillo del gripper.

### Cambios para que encajen las piezas compradas
- **Piñón**: el agujero en D pasa de 6,0 × 5,5 a **6,15 × 5,65**. Medía lo mismo que el eje del JGB37, sin
  holgura; ahora tiene la misma que la `Pieza_Eje_Giro_Base` de Ignacio.
- **Eje Parte 2**: el agujero del extremo, donde entra el motor del codo, pasa de redondo Ø6 con un nervio
  central a una **D de 6,15 × 5,65** de 15 mm de fondo, para que el eje en D del JGB37 entre y arrastre.
  Ojo: la pared alrededor del agujero es fina (~1 mm por el lado estrecho), así que hay que imprimirlo al 100 %.

### Sigue pendiente con Vasil (no se ha cambiado)
- La cuna del motor de `Shield 1` (Ø35,5) no deja sitio para la reductora del JGB37 (Ø37) y está centrada a
  8,1 mm del eje del piñón en vez de a 7.
- Los Shields no tienen agujeros para atornillar el motor.
- `Shield 2` no tiene sitio para un JGB37 en el codo.

## 3_gripper_Rapha

| Archivo | Cant. | Soportes | Relleno | Notas |
|---|---|---|---|---|
| `acople_punta_vasil_x1.5` | 1 | **Sí**, en las alas y bajo el bloque | ≥40 %, 4 perímetros | Brida en la cama |
| `casquillo_punta_x1.5` | 1 | No | 100 % | Valona en la cama |
| `contraplaca_acople_x1.5` | 1 | No | 50 % | |
| `base_plate_x1.5` | 1 | No (solo algún puente pequeño) | 30 % | |
| `gear_left_x1.5`, `gear_right_x1.5` | 1 de cada | No | 100 % | |
| `arm_left_x1.5`, `arm_right_x1.5` | 1 de cada | No | 100 % | |
| `jaw_left_x1.5`, `jaw_right_x1.5` | 1 de cada | No | 40 % | |

## Orden recomendado
1. Las piezas pequeñas que encajan con algo comprado, para ajustar tolerancias:
   - `Pieza_Eje_Giro_Base` y el piñón: pruébalos en el eje del JGB37.
   - Un clip: pruébalo en la ranura de un eje.
   - Si van justos, activa la compensación de agujeros (+0,1 mm) en el laminador.
2. Los ejes, las placas del brazo y el gripper.
3. Lo grande (`BASE_TAPA_INF`, `BASE_TAPA_SUP` y la corona), cuando ya tengas las tolerancias ajustadas.
