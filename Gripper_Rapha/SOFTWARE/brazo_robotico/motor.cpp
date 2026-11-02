#include "motor.h"
#include "config.h"

void Motor::begin(const uint8_t pines[3], int16_t pmax, bool invertido) {
  p_pwm_ = pines[0]; p_a_ = pines[1]; p_b_ = pines[2]; pwm_max = pmax; invertido_ = invertido;
  // primero a LOW y después salidas: así no hay un pulso al arrancar
  digitalWrite(p_pwm_, LOW); digitalWrite(p_a_, LOW); digitalWrite(p_b_, LOW);
  pinMode(p_pwm_, OUTPUT); pinMode(p_a_, OUTPUT);
#if MODO_DRIVER == MODO_EN_IN1_IN2
  pinMode(p_b_, OUTPUT);
#endif
  parar();
}

void Motor::comandar(int16_t pwm) {
  pwm = constrain(pwm, -pwm_max, pwm_max);
  // rampa: limita el cambio por ciclo
  if (pwm > actual_ + PWM_RAMPA) pwm = actual_ + PWM_RAMPA;
  if (pwm < actual_ - PWM_RAMPA) pwm = actual_ - PWM_RAMPA;
  actual_ = pwm;
  escribir(invertido_ ? -pwm : pwm);
}

void Motor::parar() {
  actual_ = 0;
  escribir(0);
}

void Motor::escribir(int16_t pwm) {
  bool adelante = pwm >= 0;
  uint8_t ciclo = (uint8_t)min(abs(pwm), 255);
#if MODO_DRIVER == MODO_EN_IN1_IN2
  if (ciclo == 0) {                       // parada libre: IN1 = IN2 = 0
    digitalWrite(p_a_, LOW); digitalWrite(p_b_, LOW);
  } else {
    digitalWrite(p_a_, adelante ? HIGH : LOW);
    digitalWrite(p_b_, adelante ? LOW : HIGH);
  }
#else
  digitalWrite(p_a_, adelante ? HIGH : LOW);
#endif
  analogWrite(p_pwm_, ciclo);
}
