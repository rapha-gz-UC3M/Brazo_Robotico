# Tornillería del brazo completo

Para la versión final del brazo: piezas de `IMPRIMIR/` y motores **JGB37-520B de 12 V y 45 RPM con encoder**.
Las longitudes están calculadas con las piezas montadas, agujero por agujero, y comprobadas moviendo el hombro y
el codo para que ninguna cabeza ni tuerca choque. Todo es métrico; "cabeza Allen" = DIN 912.

> **Tornillos de los motores:** los agujeros de la cara del JGB37 solo tienen **4 mm de rosca**. Si el tornillo
> entra más, hace tope antes de apretar el motor. Por eso los del hombro y el codo son M3 × 6 y los de la base
> llevan arandela.

## Lista de compra

| Tornillo | Cant. | Tuercas / arandelas | Dónde |
|---|---|---|---|
| M2 × 16 | 4 | 4 tuercas M2 | Finales de carrera |
| M3 × 6 **avellanado** (DIN 7991) | 12 | — (roscan en el motor) | Motores del hombro y del codo |
| M3 × 8 | 6 | 6 arandelas M3 | Motor de la base |
| M3 × 12 | 1 | — | `BASE_TAPA_SUP` → `Pieza_Eje_Giro_Base` |
| Prisionero M3 × 6 (DIN 913) | 1 | — | `Pieza_Eje_Giro_Base` → eje del motor |
| M3 × 16 | 4 | 4 tuercas M3 | Gripper → acople |
| M3 × 20 | 7 | 7 tuercas M3 autoblocantes | Pivotes del gripper |
| M4 × 30 **avellanado** (DIN 7991) | 2 | 2 tuercas M4 + 2 arandelas | `Shield 1` + `Paleta 2` |
| M4 × 35 **avellanado** (DIN 7991) | 2 | 2 tuercas M4 + 2 arandelas | `Shield 1` + `Paleta 2` + `SUP` |
| M5 × 16 cabeza Allen | 2 | 2 tuercas M5 + 4 arandelas | `Paleta 1` → `SUP` |
| M5 × 30 cabeza Allen | 2 | 2 tuercas M5 + 2 arandelas | Orejetas del antebrazo → acople |
| M5 × 30 **cabeza baja** (DIN 7984) | 2 | 2 tuercas M5 + 2 arandelas | `Shield 2` → `Brazo Parte 1.1` |
| M5 × 40 cabeza Allen | 1 | 1 tuerca M5 + 1 arandela | Eje de la punta |
| M6 × 30 cabeza Allen | 1 | 1 tuerca M6 + 1 arandela | `Shield 2` → `Brazo Parte 1.1` |
| Bridas (zip ties) de 3–4 mm | 2 | — | Potenciómetros |
| Tirafondo para aglomerado Ø4 × 35 (tabla de 16 mm) o Ø4 × 40 (tabla de 19 mm o más) | 4 | 4 arandelas M4 | Base → tabla de aglomerado, a través del suplemento |
| Tirafondo Ø3 × 12 (o separadores adhesivos) | 8–12 | — | Arduino y controladores → tabla |

Además: los tornillos que vienen con el servo MG90S y con los finales de carrera.

## Dónde va cada uno

### Base
| Unión | Tornillos | Notas |
|---|---|---|
| Motor de la base → techo de la torre de `BASE_TAPA_INF` | 6 × M3 × 8 + arandela | Desde arriba del techo (4 mm), antes de poner `Pieza_Eje_Giro_Base`. Con la arandela entran 3,5 mm en el motor. Cables hacia abajo |
| 2 finales de carrera → repisas interiores de `BASE_TAPA_INF` | 4 × M2 × 16 + tuerca | Cada pulsador (micro de 20 × 10 × 6,5, agujeros a 9,5 mm) va entre las dos repisas de su lado. Los acciona la pestaña de `BASE_TAPA_SUP` |
| `Pieza_Eje_Giro_Base` → eje del motor | 1 prisionero M3 × 6 | En el agujero del lateral, contra el plano de la D del eje |
| `BASE_TAPA_SUP` → `Pieza_Eje_Giro_Base` | 1 × M3 × 12 | Desde arriba, por el agujero central del disco (cabeza rebajada). Une la tapa al eje: así no vuelca. Sin forzar |
| `BASE_TAPA_SUP` sobre `BASE_TAPA_INF` | — | Apoya y gira |
| `BASE_TAPA_INF` + `Base_suplemento_15mm` → tabla de aglomerado | 4 tirafondos Ø4 + arandela | Por las 4 orejetas de la base (agujeros de 4,7 mm) y los 4 agujeros del suplemento: 25 mm de plástico. Ø4 × 35 entra 10 mm en la tabla y no asoma en una de 16 mm; Ø4 × 40 entra 15 mm, para tablas de 19 mm o más. Alternativa: 4 × M4 pasantes con arandela y tuerca por debajo (25 mm + grosor de la tabla + 8 mm). Los cables del motor salen por la salida de cables del suplemento |

### Hombro
| Unión | Tornillos | Notas |
|---|---|---|
| Motor del hombro → `Shield 1` | 6 × **M3 × 6 avellanado** | Cabeza en la cara interior de `Shield 1` (a ras), eje del motor hacia dentro |
| `Paleta 1` → pared derecha de `BASE_TAPA_SUP` | 2 × M5 × 16 + arandela + tuerca | Cabeza por fuera de la paleta, tuerca por dentro de la pared |
| `Shield 1` + separador + `Paleta 2` + pared izquierda de `SUP` (2 agujeros de abajo) | 2 × **M4 × 35 avellanado** + tuerca | Cabeza en el avellanado de la cara exterior de `Shield 1`, tuerca por dentro de la pared de `SUP` |
| `Shield 1` + separador + `Paleta 2` (agujero de atrás, junto a la cuna del motor) | 1 × **M4 × 30 avellanado** + tuerca | Cabeza en el avellanado de `Shield 1`, tuerca en la cara interior de `Paleta 2` |
| `Shield 1` + separador + `Paleta 2` (agujero de arriba) | 1 × **M4 × 30 avellanado** + tuerca, **al revés** | Cabeza **desde dentro**, en el avellanado de `Paleta 2`, y tuerca por fuera de `Shield 1`. Ahí la paleta está a 0,15 mm de `Brazo Parte 1.1`: una tuerca por dentro chocaría al inclinar el brazo hacia delante más de ~55° |
| Potenciómetro del hombro | 1 brida | Dentro de su manguito, en el semicasquillo de `Shield 1` |
| Corona, piñón y clip | — | La corona entra en los planos de `Eje Parte 1`, el piñón en el eje del motor y el clip a presión |

### Brazo y codo
| Unión | Tornillos | Notas |
|---|---|---|
| Motor del codo → parte plana de `Shield 2` | 6 × **M3 × 6 avellanado** | Cabeza en la cara interior de `Shield 2` (asiento rebajado), eje por el agujero Ø15 nuevo |
| `Shield 2` + separador lateral + `Brazo Parte 1.1` (orejetas) | 2 × **M5 × 30 cabeza baja** + arandela + tuerca | Cabeza **por dentro** del brazo y tuerca por fuera de `Shield 2`. La tuerca y la arandela quedan a ~5 mm del motor del codo |
| `Shield 2` + separador central + `Brazo Parte 1.1` | 1 × M6 × 30 + arandela + tuerca | Cabeza por fuera de `Shield 2` (justa junto a su pared, a 0,5 mm), tuerca por dentro del brazo |
| Potenciómetro del codo | 1 brida | Dentro de su manguito, en el semicasquillo de `Shield 2` |
| Corona del codo, piñón y clip | — | Igual que en el hombro, en `Eje Parte 2` |

### Gripper y punta del antebrazo
| Unión | Tornillos | Notas |
|---|---|---|
| Engranaje izquierdo y 2 bielas → placa base | 3 × M3 × 20 + autoblocante | Apretar sin frenar el giro |
| Mordazas → engranajes y bielas | 4 × M3 × 20 + autoblocante | Igual |
| Pared del gripper → brida del acople | 4 × M3 × 16 + tuerca | Tuercas en los alojamientos del acople |
| Eje de la punta: casquillo + 2 placas + contraplaca | 1 × M5 × 40 + arandela + tuerca | Sustituye a `Eje Parte 3`. Tuerca en el alojamiento de la contraplaca |
| Orejetas de `Brazo Parte 2.2_4` → alas del acople | 2 × M5 × 30 + arandela + tuerca | Tuercas en los alojamientos de las alas |
| Servo MG90S → placa base, engranaje → eje del servo | Los del servo | |

## Agujeros que no hace falta usar
- `Brazo Parte 1_1` (75, 0) y `Brazo Parte 2_1` / `2.2_4` (60, 0): agujeros Ø7,4 enfrentados entre las dos placas
  de cada tramo, de un tornillo pasante del diseño original. Las placas ya quedan unidas por los ejes y el
  acople. Si se usan, necesitan un separador impreso entre placas (36 mm en el brazo y 21 mm en el antebrazo, que
  no están en el repo), y en el antebrazo las cabezas limitan el cierre del codo a ~40°.
- Pared de `Shield 2`: 4 agujeros Ø3,5 (rectángulo de 30 × 24 mm), para M3 si se quiere sujetar algo ahí.
- Agujero Ø15 de `Shield 2` a 45 mm del codo (del diseño original): no se usa. El piñón del codo va en el agujero
  nuevo, a 60 mm, y este queda tapado en parte por la reductora del motor.
