// =====================================================================================================
//  config.h  -  Todo lo que depende del montaje: pines, driver de motores, sensores, límites y ganancias.
//  Los valores marcados con [CAL] se ajustan en el robot (por serie, y se guardan en la EEPROM con GUARDAR).
// =====================================================================================================
#pragma once
#include <Arduino.h>

// ---------------------------------------------- PINES (Arduino UNO) ----------------------------------
// Coinciden con la tabla de la guía de montaje. D9 y D10 no pueden dar PWM porque la librería Servo usa
// el Timer1, por eso los motores usan D5, D6 y D11, y D10 es solo una entrada (final de carrera 2).
const uint8_t PIN_ENC_A        = 2;    // encoder del motor de la base, canal A (interrupción INT0)
const uint8_t PIN_ENC_B        = 4;    // encoder de la base, canal B
const uint8_t PIN_FC1          = 3;    // final de carrera 1 (INPUT_PULLUP, pulsado = LOW)
const uint8_t PIN_FC2          = 10;   // final de carrera 2
const uint8_t PIN_SERVO        = 9;    // servo MG90S de la pinza (señal)
const uint8_t PIN_POT_HOMBRO   = A0;   // cursor del potenciómetro del hombro
const uint8_t PIN_POT_CODO     = A1;   // cursor del potenciómetro del codo

//                                    PWM   IN1/DIR  IN2
const uint8_t PIN_M_BASE[3]       = { 5,    7,       8  };
const uint8_t PIN_M_HOMBRO[3]     = { 6,    12,      13 };
const uint8_t PIN_M_CODO[3]       = { 11,   A2,      A3 };

// ---------------------------------------------- DRIVER DE MOTORES ------------------------------------
// MODO_EN_IN1_IN2 : L298N, TB6612FNG, BTS7960 en modo EN... -> PWM en EN, sentido con IN1/IN2 (por defecto)
// MODO_PWM_DIR    : Pololu Dual G2, Cytron MD10C, VNH5019... -> PWM + 1 pin de sentido (IN2 no se usa)
#define MODO_EN_IN1_IN2 0
#define MODO_PWM_DIR    1
#define MODO_DRIVER     MODO_EN_IN1_IN2

// ---------------------------------------------- MOTORES JGB37-520B (12 V, 45 RPM, 1:131) ---------------
const int16_t PWM_MAX_BASE   = 140;    // la base no tiene reducción extra: 45 RPM es rápido, se limita
const int16_t PWM_MAX_HOMBRO = 255;
const int16_t PWM_MAX_CODO   = 230;
const int16_t PWM_MIN_BASE   = 35;     // [CAL] PWM mínimo que vence el rozamiento estático (zona muerta)
const int16_t PWM_MIN_HOMBRO = 40;     // [CAL]
const int16_t PWM_MIN_CODO   = 40;     // [CAL]
const int16_t PWM_RAMPA      = 25;     // cambio máximo de PWM por ciclo de control (evita picos de corriente)

// ---------------------------------------------- ENCODER DE LA BASE -----------------------------------
// Hall de 11 pulsos por vuelta del motor; se cuentan los 2 flancos del canal A -> 22 por vuelta del motor.
// La base va directa al eje de salida (reducción 1:131): 22 * 131 = 2882 cuentas por vuelta de la base.
const float ENC_CUENTAS_VUELTA = 22.0f * 131.0f;     // [CAL] compruébalo con el comando ENC (ver README)
const float ENC_GRADOS_CUENTA  = 360.0f / ENC_CUENTAS_VUELTA;

// ---------------------------------------------- POTENCIÓMETROS (WH148, 300°) -------------------------
// Ángulo = (ADC - adc0) * grados_por_cuenta. Valores de partida; se calibran con CAL (dos posiciones).
const float POT_GRADOS_CUENTA = 300.0f / 1023.0f;
const int16_t POT_ADC_MIN_OK  = 8;      // por debajo / encima: cable cortado o cursor suelto -> paro
const int16_t POT_ADC_MAX_OK  = 1015;
const float FILTRO_POT_ALFA   = 0.35f;  // filtro exponencial (EMA) de la lectura: 1 = sin filtro

// ---------------------------------------------- GEOMETRÍA (del CAD, mm) ------------------------------
// q0: giro de la base (0 = hacia delante, + antihorario visto desde arriba)
// q1: hombro, ángulo del brazo desde la vertical (+ hacia delante)
// q2: codo, ángulo del antebrazo respecto al brazo (0 = recto; + doblado hacia delante/abajo)
const float L1_MM        = 180.0f;    // eje del hombro -> eje del codo
const float L2_MM        = 300.0f;    // eje del codo -> centro de las mordazas (TCP)
const float H_HOMBRO_MM  = 185.0f;    // altura del eje del hombro sobre la mesa (con el suplemento de 15 mm)

// ---------------------------------------------- LÍMITES DE SOFTWARE (grados) -------------------------
// Recorrido mecánico comprobado en el CAD: hombro de -90 (atrás) a +80 (delante); codo libre salvo
// plegado del todo; base entre los dos finales de carrera.
const float LIM_MIN[3] = { -75.0f, -60.0f,  15.0f };
const float LIM_MAX[3] = {  75.0f,  70.0f, 150.0f };
const float VEL_MAX[3] = {  60.0f,  35.0f,  45.0f };   // velocidad máxima de las trayectorias (°/s)

// ---------------------------------------------- HOMING DE LA BASE -------------------------------------
const int16_t PWM_HOMING          = 60;       // PWM con el que la base busca el final de carrera 1
const float   ANGULO_FC1          = -80.0f;   // [CAL] ángulo de la base cuando pisa el final de carrera 1
const uint32_t TIEMPO_MAX_HOMING  = 15000;    // ms

// ---------------------------------------------- CONTROL -----------------------------------------------
const uint16_t PERIODO_CONTROL_US = 10000;    // 100 Hz
const float    TOLERANCIA_GRADOS[3] = { 0.6f, 0.6f, 0.6f };  // dentro de esta banda el PID no empuja
const uint16_t TIEMPO_LLEGADA_MS  = 150;      // tiempo dentro de tolerancia para dar el movimiento por hecho
const uint16_t TIEMPO_EXTRA_MS    = 4000;     // margen tras el fin de la trayectoria antes de dar error
const uint16_t TIEMPO_BLOQUEO_MS  = 1500;     // PWM casi al máximo sin moverse durante este tiempo -> paro

// Ganancias PID de partida [CAL] (PWM por grado). Ajustarlas con ESCALON / AUTOTUNE / ajuste_pid.py.
//                           base    hombro   codo
const float KP_INI[3] = {    6.0f,   14.0f,   10.0f };
const float KI_INI[3] = {    4.0f,   20.0f,   16.0f };
const float KD_INI[3] = {    0.25f,   0.6f,    0.4f };
const float I_MAX     = 120.0f;   // límite del término integral (PWM)
const float D_FILTRO  = 0.3f;     // filtro de la derivada (0..1, menor = más filtrado)

// Compensación de gravedad (feedforward) [CAL] en PWM: ver comando CARGA en el README
//   hombro: -(G_HOMBRO_1 * sin(q1) + G_HOMBRO_2 * sin(q1+q2))      codo: -(G_CODO * sin(q1+q2))
const float G_HOMBRO_1_INI = 0.0f;
const float G_HOMBRO_2_INI = 0.0f;
const float G_CODO_INI     = 0.0f;

// ---------------------------------------------- PINZA (servo MG90S) ----------------------------------
// Apertura entre mordazas según el giro del servo desde la posición cerrada (simulación del CAD).
const uint8_t PINZA_N = 7;
const float PINZA_GIRO[PINZA_N]     = { 0.0f, 15.0f, 30.0f, 45.0f, 60.0f, 75.0f, 90.0f };
const float PINZA_APERTURA[PINZA_N] = { 2.3f, 25.6f, 47.3f, 65.9f, 80.2f, 89.2f, 92.3f };   // mm
const int16_t SERVO_CERRADO_INI = 45;    // [CAL] valor de servo.write() con las mordazas cerradas
const int8_t  SERVO_SENTIDO_INI = 1;     // [CAL] +1 si al aumentar el ángulo del servo la pinza se abre
const float   PINZA_APRIETE_MM  = 2.0f;  // cuánto menos que el cubo se cierra (cubo de cartulina: poco)
const float   PINZA_VEL         = 180.0f;// °/s de giro del servo (movimiento suave, sin picos de corriente)

// ---------------------------------------------- TAREA: APILAR CUBOS ----------------------------------
const float CUBO_MM_INI      = 40.0f;   // [CAL] lado del cubo (se cambia con CUBO)
const float ALTURA_SEGURA_MM = 60.0f;   // margen por encima del cubo o de la pila al moverse
const float Z_AGARRE_MM      = 4.0f;    // corrección de la altura de agarre (+ = más arriba)
const uint8_t MAX_CUBOS      = 6;
// Posición de reposo (articular) a la que vuelve el brazo al terminar
const float POSE_REPOSO[3]   = { 0.0f, 10.0f, 100.0f };

// ---------------------------------------------- SERIE --------------------------------------------------
const uint32_t BAUDIOS = 115200;
