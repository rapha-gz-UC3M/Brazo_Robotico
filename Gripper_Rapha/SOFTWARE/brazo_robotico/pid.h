// pid.h - PID discreto para la posición de una articulación (salida en PWM).
//  - P sobre el error, I con anti-windup (límite + integración condicional), D sobre la medida (sin pico
//    al cambiar la consigna) y filtrada.
//  - Feedforward aparte (gravedad) y compensación de la zona muerta del motor.
#pragma once
#include <Arduino.h>

class PID {
public:
  float kp = 0, ki = 0, kd = 0;
  float i_max = 120;          // límite del término integral (PWM)
  float filtro_d = 0.3f;      // 0..1
  float tolerancia = 1.0f;    // banda muerta del error (grados): dentro no empuja ni integra
  int16_t pwm_min = 0;        // compensación de zona muerta
  int16_t pwm_max = 255;

  void reset(float medida);
  // devuelve el PWM: e = consigna - medida; ff = feedforward en PWM; dt en segundos
  float calcular(float consigna, float medida, float ff, float dt);

  // términos de la última llamada (para el registro y el ajuste)
  float p = 0, i = 0, d = 0, salida = 0;
private:
  float medida_ant_ = 0, deriv_ = 0;
  bool primera_ = true;
};
