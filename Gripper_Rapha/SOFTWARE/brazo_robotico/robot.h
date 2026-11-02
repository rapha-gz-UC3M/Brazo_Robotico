// robot.h - Las tres articulaciones (sensores + PID + motor), trayectorias, homing, seguridad y registro.
//  Articulaciones: 0 = base (encoder + finales de carrera), 1 = hombro (potenciómetro), 2 = codo (pot.).
#pragma once
#include <Arduino.h>
#include "cinematica.h"

namespace Robot {
  enum Modo : uint8_t { PARADO, CONTROL, HOMING, PRUEBA, AUTOTUNE, FALLO };

  // Lo que se calibra y se guarda en la EEPROM (comando GUARDAR)
  struct Ajustes {
    uint16_t magia;
    float pot_adc0[2], pot_k[2];          // hombro, codo
    float kp[3], ki[3], kd[3];
    float g_h1, g_h2, g_c;                // compensación de gravedad (PWM)
    uint8_t inv_motor[3];                 // 1 = invertir el sentido del motor
    int8_t enc_signo;
    int16_t servo_cerrado; int8_t servo_sentido;
    float angulo_fc1;
    float cubo_mm;
    int16_t pwm_min[3];
  };
  extern Ajustes aj;

  void begin();
  void ciclo();                                   // llamar a 100 Hz
  Modo modo();
  void encender();                                // control activo manteniendo la postura actual
  void apagar();                                  // motores a 0, sin control
  void fallo(const __FlashStringHelper *motivo);
  void rearmar();
  void aplicar_ajustes();
  void ajustes_por_defecto();
  void guardar();
  bool cargar();

  // Movimientos (no bloqueantes). dur = 0 -> se calcula con las velocidades máximas.
  bool mover_articular(const float q[3], float dur = 0);
  bool mover_cartesiano(const Punto &p, float dur = 0);   // en línea recta
  bool moviendo();                                // trayectoria en curso o aún no asentado
  bool fallo_llegada();                           // la última trayectoria no llegó a tiempo
  void parar_movimiento();                        // congela la consigna donde está

  void q_actual(float q[3]);
  void q_consigna(float q[3]);
  bool base_referenciada();
  void iniciar_homing();

  // Pruebas para el ajuste del PID (todas registran en CSV por serie)
  void prueba_pwm(uint8_t j, int16_t pwm, uint16_t ms);   // lazo abierto
  void escalon(uint8_t j, float delta, uint16_t ms);       // respuesta a un escalón de consigna
  void autotune(uint8_t j, int16_t d);                     // relé (Åström–Hägglund)
  void registro(bool on);
  void imprimir_estado();
  void imprimir_carga(uint8_t j);                          // PWM medio para sostener la postura
  void calibrar_pot(uint8_t j, float angulo);              // j = 1 hombro, 2 codo (dos posiciones)
}
