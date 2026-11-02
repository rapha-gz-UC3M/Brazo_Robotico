#include "pid.h"

void PID::reset(float medida) {
  i = 0; d = 0; deriv_ = 0; medida_ant_ = medida; primera_ = false; salida = 0;
}

float PID::calcular(float consigna, float medida, float ff, float dt) {
  if (primera_) reset(medida);
  float e = consigna - medida;

  // Derivada sobre la medida (no salta al cambiar la consigna), con filtro paso bajo
  float dmed = (medida - medida_ant_) / dt;
  medida_ant_ = medida;
  deriv_ += filtro_d * (dmed - deriv_);
  d = -kd * deriv_;

  p = kp * e;
  bool dentro = fabs(e) <= tolerancia;

  // Integral con anti-windup: no integra dentro de la tolerancia ni si la salida ya está saturada en el
  // sentido del error; además se limita a ±i_max.
  float u_sin_i = p + d + ff;
  bool saturado = (u_sin_i + i >= pwm_max && e > 0) || (u_sin_i + i <= -pwm_max && e < 0);
  if (!dentro && !saturado) i += ki * e * dt;
  i = constrain(i, -i_max, i_max);

  float u;
  if (dentro) {
    u = ff + i;                                   // sujeta (gravedad + integral) sin buscar más
  } else {
    u = p + i + d + ff;
    // zona muerta: el motor no se mueve con PWM pequeños; se suma el mínimo en el sentido del empuje
    if (u > 0) u += pwm_min; else if (u < 0) u -= pwm_min;
  }
  salida = constrain(u, -pwm_max, pwm_max);
  return salida;
}
