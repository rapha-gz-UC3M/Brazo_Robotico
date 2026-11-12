# SOFTWARE del brazo robótico

Programa del Arduino UNO (control de las 3 articulaciones y de la pinza, homing, seguridad, trayectorias y tarea
de apilar cubos) y herramientas de PC (interfaz gráfica, registro de ensayos y ajuste del PID para el informe).

Cumple lo que piden los apuntes de la asignatura:

| Requisito | Dónde está |
|---|---|
| ≥ 3 GDL, 2 en lazo cerrado con motores DC | Base (encoder), hombro y codo (potenciómetro): los 3 en lazo cerrado con PID. La pinza es un servo |
| Homing de los sensores relativos | La base (encoder) busca el final de carrera 1 con `HOME` |
| PID con anti-windup, derivada filtrada, zona muerta | `pid.cpp` |
| Compensación de gravedad (feedforward) en el hombro | `robot.cpp` + comando `CARGA` |
| Registro CSV tiempo / consigna / posición | `LOG 1`, `ESCALON`, `PWM`, `AUTOTUNE` → `pc/registrar_pid.py` |
| Tiempo de subida, sobreoscilación, establecimiento | `pc/registrar_pid.py` (gráfica + valores) |
| Ajuste ZN / Cohen-Coon / CHR, estimación detallada u optimización (extra) | `AUTOTUNE` (ZN por relé) + `pc/ajuste_pid.py` (identificación del modelo, SIMC y optimización) |
| Seguridad: watchdog, cable del pot suelto, PWM 0 al arrancar, límites | `brazo_robotico.ino`, `robot.cpp` (ver [Seguridad](#seguridad)) |
| Sin `delay()`, encoder por interrupción, filtrado EMA | `brazo_robotico.ino`, `sensores.cpp` |
| Interfaz gráfica (extra) | `pc/brazo_gui.py` |
| Tarea: apilar cubos desde posiciones variables | `APILAR` (o con el ratón en la interfaz) |

## Qué hay en cada carpeta

| Archivo | Para qué |
|---|---|
| `brazo_robotico/brazo_robotico.ino` | Programa principal: bucle de control a 100 Hz, órdenes por serie y tareas |
| `brazo_robotico/config.h` | **Todo lo que depende del montaje**: pines, tipo de driver, límites, ganancias iniciales, cubo |
| `brazo_robotico/robot.cpp` | Lazo de control, homing, seguridad, ensayos (escalón, lazo abierto, autotune), registro, EEPROM |
| `brazo_robotico/pid.cpp` · `motor.cpp` · `sensores.cpp` | PID, driver de motores, encoder, potenciómetros y finales de carrera |
| `brazo_robotico/cinematica.cpp` | Cinemática directa e inversa (x, y, z ↔ ángulos) |
| `brazo_robotico/pinza.cpp` · `tareas.cpp` · `comandos.cpp` | Pinza (mm → servo), coger / dejar / apilar, intérprete de órdenes |
| `pc/brazo_gui.py` | Interfaz gráfica: estado en vivo, mover el brazo, apilar con el ratón, PARO |
| `pc/registrar_pid.py` | Lanza un ensayo, guarda el CSV y la gráfica con las métricas del informe |
| `pc/ajuste_pid.py` | Identifica el modelo de una articulación y calcula el PID (SIMC, ZN por relé y optimizado) |
| `pc/brazo_serial.py` · `pc/modelo.py` | Conexión serie y cinemática en Python (lee `config.h`) |
| `simulacion/` | Simulador en el PC del mismo código del Arduino, para probar sin el brazo |

## 1. Cargar el programa en el Arduino

1. Instala el **Arduino IDE 2**. Las librerías `Servo` y `EEPROM` ya vienen con él.
2. Abre `brazo_robotico/brazo_robotico.ino`. La carpeta se tiene que llamar igual que el `.ino`.
3. Placa **Arduino UNO**, el puerto COM que salga y **Subir**. Ocupa ~30,5 KB de 32 KB (93 %) y 1,2 KB de RAM.
4. Abre el **Monitor Serie** a **115200** baudios, con fin de línea **Nueva línea**. Debe salir
   `Brazo robotico listo. Motores apagados...`. Escribe `ESTADO` para ver los sensores.

Los motores **arrancan apagados**. `HOME` referencia la base y activa el control; `ON` lo activa sin referenciar.

## 2. Conexiones

Los pines están en `config.h` y coinciden con la tabla de la guía de montaje.

| Señal | Pin UNO | Notas |
|---|---|---|
| Encoder base canal A / B | D2 / D4 | D2 es la interrupción INT0. Alimentación del encoder a 5 V |
| Final de carrera 1 / 2 | D3 / D10 | Entre el pin y GND (pull-up interno, pulsado = LOW). FC1 es el del lado **horario** visto desde arriba |
| Servo pinza (señal) | D9 | Alimentación del servo a 5 V (salida de 5 V del L298N o pin 5 V del Arduino) con un **condensador de 470 µF** junto al conector. GND común |
| Pot hombro / pot codo (cursor) | A0 / A1 | Extremos del pot a 5 V y GND |
| Motor base: PWM, IN1, IN2 | D5, D7, D8 | |
| Motor hombro: PWM, IN1, IN2 | D6, D12, D13 | |
| Motor codo: PWM, IN1, IN2 | D11, A2, A3 | A2 y A3 funcionan como salidas digitales |

**Tipo de driver** (`MODO_DRIVER` en `config.h`):

- `MODO_EN_IN1_IN2` (por defecto): L298N, TB6612FNG… El PWM va a EN/ENA/PWMA y el sentido a IN1/IN2.
- `MODO_PWM_DIR`: Pololu Dual G2, Cytron MD10C, VNH5019… El PWM va a PWM y el sentido a DIR. IN2 no se usa.

Todas las masas (12 V de los motores, servo y Arduino) tienen que ir unidas. Entre +12 V y masa, cerca de los
controladores, va un condensador electrolítico de 470–1000 µF (≥ 25 V) para los picos de corriente de los motores.
Si el Arduino se reinicia al cerrar la pinza, el servo está pidiendo más corriente de la que dan los 5 V.

## 3. Puesta en marcha (una vez, con el brazo montado)

Con el brazo en una postura cómoda y **sin la pinza agarrando nada**. Después de cada paso, `ESTADO` te dice
cómo va. Todo se guarda en la EEPROM al final con `GUARDAR`.

Las reductoras no dejan girar las articulaciones a mano, así que para llevarlas a una postura se usan empujones
cortos del motor: `PWM j 80 300` o `PWM j -80 300` (articulación `j` = 0 base, 1 hombro, 2 codo; PWM 80 durante
300 ms). Funcionan con el control apagado, y el resto de motores siguen parados.

1. **Potenciómetros** (ángulos del hombro y del codo). Lleva el hombro a **vertical** y escribe `CAL 1 0`.
   Después llévalo hacia delante unos 45° (mídelo con el móvil o un transportador) y escribe `CAL 1 45`. Lo mismo
   con el codo: `CAL 2 90` con el antebrazo a 90° del brazo y `CAL 2 135` a 135°.
   - Convenio: hombro 0° = vertical, + hacia delante; codo 0° = recto, + doblado hacia delante y abajo.
   - Si te es más fácil, calibra los pots antes de montar las coronas, girando el eje a mano.
2. **Encoder de la base.** Mira el primer valor de `q=` en `ESTADO`, escribe `PWM 0 60 300` y fíjate hacia dónde
   gira la base. Si gira en sentido **antihorario** visto desde arriba, ese ángulo tiene que haber **subido**; si
   gira en sentido horario, tiene que haber bajado. Si no es así, escribe `INVENC`.
3. **Sentido de los motores.** Escribe `SENTIDO 0`, `SENTIDO 1` y `SENTIDO 2`. Cada uno da un pequeño empujón
   adelante y atrás, mira hacia dónde se mueve la articulación y **corrige el sentido del motor él solo** si hace
   falta. También puedes invertirlo a mano con `INV j`. Hazlo **después** de los pasos 1 y 2: se basa en las
   lecturas de los sensores.
4. **Ángulo del final de carrera 1.** Escribe `HOME`: la base gira en sentido horario hasta el FC1 y vuelve a 0°.
   Si al volver no mira hacia delante, mide cuántos grados se desvía y corrige `FC1` (por defecto `FC1 -80`), y repite `HOME`.
5. **Pinza.** Con el servo sin el brazo de plástico, escribe `PINZA 2` (cerrada) y monta el brazo del servo con las
   mordazas cerradas. `PINZA 40` debe abrir 40 mm (mídelo con un calibre). Si en vez de abrir cierra, usa
   `SERVO 135 -1` y vuelve a montar el brazo del servo con `PINZA 2`. Ajuste fino: `SERVO c 1` cambiando `c`.
6. **Cubo.** `CUBO 40` (el lado en mm del cubo de cartulina; mídelo una vez montado).
7. `GUARDAR`.

Si algo va mal, el brazo se para y escribe `!! FALLO: motivo`. Arregla la causa y escribe `REARMAR` (o `HOME`).

## 4. Ajuste del PID y datos para el informe

Desde la carpeta `pc` (con `pip install -r requirements.txt`). Ejemplo con el hombro (`1`); igual para 0 y 2.
Haz los ensayos con el brazo en una postura intermedia, lejos de los límites.

1. **Escalón con las ganancias de partida**, para ver de dónde partes:
   `python registrar_pid.py --puerto COM5 --escalon 1 15`
   → `resultados/..._escalon_j1_+15.csv` y `.png`, con el tiempo de subida (10-90 %), la sobreoscilación, el tiempo
   de establecimiento (banda del 2 % o 0,75°) y el error final.
2. **Ensayos en lazo abierto** (identificación del modelo). Cuatro: dos PWM bajos y dos altos, en los dos sentidos:
   `python registrar_pid.py --puerto COM5 --lazo 1 90 600` y lo mismo con `-90`, `160` y `-160`.
   El motor empuja con ese PWM fijo durante 600 ms; el programa lo corta si se acerca a un límite.
3. **Relé (autotune)**: `python registrar_pid.py --puerto COM5 --autotune 1 70`. Da `Ku` y `Pu` y las ganancias de
   Ziegler-Nichols (clásico y sin sobreoscilación).
4. **Cálculo del PID**: `python ajuste_pid.py --articulacion 1 --csv "resultados/*lazo_abierto_j1*.csv" --ku 82 --pu 1.09`
   Ajusta el modelo, compara SIMC, ZN por relé y el PID **optimizado** (mínimo ITAE con poca sobreoscilación)
   simulados con el mismo PID que el Arduino, y escribe la línea a mandar, p. ej. `PID 1 30.5 18.5 1.89`.
   El texto del principio de `ajuste_pid.py` explica por qué ZN / Cohen-Coon / CHR en lazo abierto no sirven
   tal cual para una articulación (es un proceso integrador): útil para el informe.
5. **Comprobación**: `python registrar_pid.py --puerto COM5 --escalon 1 15 --pid 30.5 18.5 1.89`. Si te gusta,
   manda `PID 1 30.5 18.5 1.89` desde el Monitor Serie o la interfaz y `GUARDAR`.

**Compensación de gravedad** (hombro y codo). Con el control activo y el brazo quieto en una postura, `CARGA 1`
escribe el PWM medio que hace falta para sostenerlo y `sin(q1)` y `sin(q1+q2)`. Haz `CARGA 1` y `CARGA 2` en dos
posturas distintas (p. ej. `J 0 0 90` y `J 0 30 60`) con `G 0 0 0`. El modelo es

    hombro:  PWM = −(G1·sin q1 + G2·sin(q1+q2))        codo:  PWM = −(Gc·sin(q1+q2))

Con las dos posturas del hombro se despejan G1 y G2 (2 ecuaciones, 2 incógnitas) y Gc con la del codo:

    import numpy as np
    G1, G2 = np.linalg.solve([[s1_A, s12_A], [s1_B, s12_B]], [-pwm_A, -pwm_B])
    Gc = -pwm_codo / s12_codo

Escribe `G G1 G2 Gc` y `GUARDAR`. Con la gravedad compensada, el integrador apenas tiene que trabajar y el PID
responde igual en todas las posturas.

## 5. Mover el brazo y apilar cubos

**Coordenadas** (mm): origen en el eje de la base, sobre la mesa. `x` hacia delante, `y` hacia la izquierda,
`z` hacia arriba. La posición es la del **centro de las mordazas**.

- `APILAR xp yp x1 y1 x2 y2 ...` coge los cubos en ese orden y los apila en (xp, yp). Hasta 6 cubos.
  Ejemplo: `APILAR 260 0 200 120 240 -100 180 60`.
- `COGER x y` y `DEJAR x y n` (n = nivel de la pila: 0 en la mesa, 1 encima de un cubo...) para hacerlo por pasos.
- Movimientos: baja y sube en línea recta y se desplaza de un sitio a otro con trayectorias suaves (jerk mínimo)
  a una altura segura por encima de la pila.

**Dónde poner los cubos** (cubo de 40 mm): entre **150 y 370 mm** del eje de la base y como mucho a ±75° del
frente. Mejor entre **160 y 300 mm**: estirado, el hombro de 45 RPM va justo de par. Coloca los cubos con una cara
mirando hacia la base (la pinza cierra de lado).

**Interfaz gráfica**: `python brazo_gui.py`. Elige el puerto y **Conectar**. En la vista de la mesa, clic
izquierdo = cubo (en orden), clic derecho = sitio de la pila, y **Apilar**. La zona verde es el alcance. También
tiene HOME / ON / OFF, mover cada articulación, ir a un punto, abrir / cerrar la pinza, una consola para cualquier
orden y el botón **PARO** (o la tecla **Esc**).

## 6. Órdenes por el puerto serie

Mayúsculas o minúsculas da igual. Los números pueden ir separados por espacios o comas.

| Orden | Qué hace |
|---|---|
| `ESTADO` (o `E`) | Modo, ángulos, consignas, PWM, integradores, posición de la pinza, lecturas de los sensores |
| `X` (o `PARO`) · `OFF` | Para todo y apaga los motores |
| `ON` · `HOME` · `REARMAR` | Activa el control · referencia la base y activa · sale de un fallo |
| `J q0 q1 q2 [s]` | Mover a esos ángulos (grados) en `s` segundos (opcional) |
| `P x y z [s]` | Mover la pinza al punto (mm) en línea recta |
| `JOG j d` | Mover la articulación `j` (0 base, 1 hombro, 2 codo) `d` grados |
| `PINZA A` · `PINZA C` · `PINZA mm` | Abrir · cerrar al tamaño del cubo · abrir a `mm` |
| `CUBO l` | Lado del cubo en mm |
| `COGER x y` · `DEJAR x y n` · `APILAR xp yp x1 y1 ...` | Tareas (ver arriba). `X` las cancela |
| `POSE k` · `IR k` | Guardar la postura actual en la memoria `k` (0-7) · ir a ella |
| `CAL j ang` | Calibrar el pot del hombro (1) o del codo (2): dos veces, en dos ángulos |
| `SENTIDO j` · `INV j` · `INVENC` | Comprobar y corregir el sentido del motor · invertirlo · invertir el encoder |
| `FC1 ang` · `ENC` | Ángulo de la base en el final de carrera 1 · cuentas del encoder |
| `SERVO c s` | Valor del servo con la pinza cerrada y sentido (+1 / −1) |
| `PID` · `PID j kp ki kd` | Ver las ganancias · cambiarlas |
| `PWMMIN j v` | Zona muerta del motor (PWM mínimo que lo mueve) |
| `G g1 g2 gc` · `CARGA j` | Compensación de gravedad · medir el PWM que sostiene la articulación |
| `PWM j v ms` | Lazo abierto: PWM fijo durante `ms` (con registro) |
| `ESCALON j d [ms]` | Escalón de `d` grados con registro (por defecto 3000 ms) |
| `AUTOTUNE j [d]` | Ensayo de relé con amplitud `d` de PWM: Ku, Pu y ganancias ZN |
| `LOG 1` · `LOG 0` | Registro continuo a 50 Hz: `L,t_ms,ref0,q0,u0,ref1,q1,u1,ref2,q2,u2` |
| `GUARDAR` · `DEFECTO` | Guardar los ajustes en la EEPROM · volver a los de `config.h` |

## Seguridad

- **Arranca con PWM 0** y los motores apagados; nada se mueve hasta `HOME` u `ON`.
- **Watchdog** de 250 ms: si el programa se cuelga, el Arduino se reinicia y los motores quedan apagados.
- **Potenciómetro desconectado** (lectura fuera de 8-1015): paro inmediato.
- **Límites de software** por articulación (`LIM_MIN` / `LIM_MAX`): las consignas se recortan y el motor no puede
  empujar más allá del límite ni contra un final de carrera pulsado.
- **Bloqueo**: PWM casi al máximo sin moverse durante 1,5 s → paro (motor atascado o sin fuerza).
- **Sentido al revés**: si la articulación se mueve contra el motor → paro, con el aviso de usar `SENTIDO j`.
- **Homing**: paro si pisa el FC2 en vez del FC1, si la base no se mueve o si tarda más de 15 s.
- **No llega**: si un movimiento no termina 4 s después de lo previsto → paro.
- **Rampa de PWM** (25 por ciclo): sin picos de corriente bruscos.

Antes de apagar, deja el brazo en reposo (`J 0 10 100`) o sujétalo: sin corriente, el hombro puede caer.

## 7. Probar sin el brazo (simulador)

El simulador compila **el mismo código** del Arduino en el PC, con un modelo de los motores, los sensores y la
gravedad. Hace falta `g++` (Linux, macOS o WSL en Windows):

    cd simulacion
    g++ -O2 -std=c++17 -Imock -I../brazo_robotico sim.cpp ../brazo_robotico/*.cpp -o sim
    ./sim guion_apilar.txt          # ejecuta las órdenes del guion (homing + apilar 3 cubos)
    ./sim --pty                     # puerto serie virtual para usar brazo_gui.py o registrar_pid.py

Los guiones son `segundos orden` por línea y acaban con `NN FIN`. Con `SIM_CABLEADO=1,-1,1` se simula un motor
conectado al revés (para probar `SENTIDO` y la detección de fallos).

## Notas

- **Hombro de 45 RPM**: sostiene bien el brazo cerca de la vertical, pero estirado va al límite. Compensa la
  gravedad (`CARGA` / `G`) y trabaja entre 160 y 300 mm.
- Las ganancias de `config.h` son de partida (ajustadas en el simulador). Hay que ajustarlas en el brazo real
  (apartado 4).
- El programa ocupa el 93 % de la memoria del UNO, así que queda poco sitio para añadir textos. Por eso `AYUDA`
  solo remite a este README.
