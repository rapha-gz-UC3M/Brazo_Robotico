// motor.h - Driver de un motor DC (puente H). Comando en PWM con signo: -255..255.
#pragma once
#include <Arduino.h>

class Motor {
public:
  void begin(const uint8_t pines[3], int16_t pwm_max, bool invertido);
  void comandar(int16_t pwm);     // aplica la rampa, el límite y la inversión
  void parar();                   // PWM 0 inmediato (sin rampa)
  int16_t pwm() const { return actual_; }
  void invertir(bool inv) { invertido_ = inv; }
  bool invertido() const { return invertido_; }
  int16_t pwm_max;
private:
  void escribir(int16_t pwm);
  uint8_t p_pwm_ = 0, p_a_ = 0, p_b_ = 0;
  int16_t actual_ = 0;
  bool invertido_ = false;
};
