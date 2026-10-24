# Qué imprimir

Todo está en **mm**, ya apoyado en la cama y en la orientación recomendada: importar e imprimir **sin escalar ni
girar**. Cada archivo se imprime **una vez**; los que acaban en `_x2`, `_x3` o `_x4` ya traen dentro esas copias.

Configuración general: PLA, boquilla de 0,4 mm, 3–4 perímetros, compensación de pata de elefante activada.
La cama tiene que medir al menos **220 mm** (las placas `Brazo_Parte_1` miden 217,5 mm y las dos coronas 198 mm).

En la columna "Origen": **Vasil / Ignacio** = su pieza sin cambios, **modificada** = copia cambiada de la suya
(el original no se toca), **nueva** = pieza que no estaba. Qué se cambió y por qué está en
[`../ENSAMBLAJE/README.md`](../ENSAMBLAJE/README.md).

## 1_base (5 archivos)

| Archivo | Origen | Soportes | Relleno | Notas |
|---|---|---|---|---|
| `BASE_TAPA_INF` | Ignacio | **Sí**, pocos | 15–20 % | Solo bajo las 4 repisas de los finales de carrera y en el puente de la torre del motor |
| `BASE_TAPA_SUP_cuerpo` | modificada | **Sí**, en árbol y solo desde la cama | 20–25 % | Solo bajo el disco. Agujero central para el M3 que la une a la pieza del eje |
| `BASE_TAPA_SUP_pestana` | modificada | No | 100 % | Se pega bajo el disco de `SUP` con epoxi (entra por una mortaja). Acciona los finales de carrera |
| `Pieza_Eje_Giro_Base` | modificada | No | 100 % | Agujero en D para el eje del motor, prisionero lateral y taladro para el M3 de `SUP` |
| `Base_suplemento_15mm` | nueva | No | 20 % | Marco que va debajo de `BASE_TAPA_INF` para que el encoder del motor no toque la mesa. Lleva una salida de cables |

## 2_brazo (16 archivos)

| Archivo | Origen | Soportes | Relleno | Notas |
|---|---|---|---|---|
| `Brazo_Parte_1_1` | modificada | No | 30–40 % | Agujero del codo a Ø14,2 |
| `Brazo_Parte_1.1` | modificada | No | 30–40 % | Agujero del codo a Ø14,2 y alivio Ø8 frente al eje del motor del codo |
| `Brazo_Parte_2_1`, `Brazo_Parte_2.2_4` | Vasil | No | 30–40 % | Antebrazo |
| `Paleta_1` | modificada | No | 30 % | Agujero Ø14,2 y rebaje de 0,4 mm donde apoya el clip |
| `Paleta_2` | modificada | No | 30 % | Agujero Ø14,2 y avellanado para el M4 que va al revés |
| `Shield_1_placa` | modificada | No | 30 % | Cuna del motor del hombro (Ø37,6) y 6 avellanados M3 para atornillarlo |
| `Shield_1_separadores_x4` | modificada | No | 100 % | 4 tubos, entre `Shield 1` y `Paleta 2` |
| `Shield_2_placa` | modificada | No | 30 % | Parte plana para el motor del codo, agujero Ø15 para su eje y 6 avellanados M3 |
| `Shield_2_separadores_x3` | modificada | No | 100 % | 3 tubos, entre `Shield 2` y `Brazo Parte 1.1` |
| `Eje_Parte_1` | Vasil | **Sí**, en los dos escalones (~5 mm) | 100 % | De pie. 5–10 °C más caliente para que las capas peguen bien |
| `Eje_Parte_2` | Vasil | **Sí**, en los escalones | 100 % | De pie. El agujero del extremo (con un nervio) es para el potenciómetro del codo |
| `Corona_30_dientes_x2` | modificada | No | 40 %, 5 perímetros | Las 2 coronas (hombro y codo). Capa de 0,12–0,16 mm. Agujero de planos con algo más de holgura |
| `Pinon_10_dientes_x2` | modificada | No | 100 % | Los 2 piñones. Capa de 0,12–0,16 mm. Agujero en D 6,15 × 5,65 y rebaje para el resalte del motor (queda hacia arriba) |
| `Sujetador_de_eje_x2` | Vasil | No | 100 % | 2 clips. Mejor en PETG; si puedes, imprime uno o dos de más |
| `Manguito_potenciometro_x2` | nueva | No | 100 % | 2 manguitos para centrar los potenciómetros en su semicasquillo |

**No se imprimen** `Eje Parte 3` ni su clip (en la punta va el casquillo del gripper), ni la corona, el piñón, las
paletas, los shields o `BASE_TAPA_SUP` originales: los sustituyen las versiones de aquí.

## 3_gripper (10 archivos)

| Archivo | Soportes | Relleno | Notas |
|---|---|---|---|
| `acople_punta` | **Sí**, en las alas y bajo el bloque | ≥ 40 %, 4 perímetros | Brida en la cama |
| `casquillo_punta` | No | 100 % | Valona en la cama |
| `contraplaca_acople` | No | 50 % | |
| `base_plate` | No (solo algún puente pequeño) | 30 % | |
| `gear_left`, `gear_right` | No | 100 % | |
| `arm_left`, `arm_right` | No | 100 % | |
| `jaw_left`, `jaw_right` | No | 40 % | Mejor agarre con goma, TPU o cinta antideslizante |

## Orden recomendado
1. Las piezas pequeñas que encajan con algo comprado, para ajustar tolerancias:
   - `Pieza_Eje_Giro_Base` y los piñones: pruébalos en el eje del motor.
   - Un clip: pruébalo en la ranura de un eje.
   - Si van justos, activa la compensación de agujeros (+0,1 mm) en el laminador.
2. Los ejes, las placas del brazo, los shields y el gripper.
3. Lo grande (`BASE_TAPA_INF`, `BASE_TAPA_SUP_cuerpo`, el suplemento y las coronas), con las tolerancias ya ajustadas.
