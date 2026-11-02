#include "cinematica.h"
#include "config.h"

static const float RAD = 0.01745329252f;

Punto Cinematica::directa(const float q[3]) {
  float a1 = q[1] * RAD, a12 = (q[1] + q[2]) * RAD, a0 = q[0] * RAD;
  float r = L1_MM * sinf(a1) + L2_MM * sinf(a12);
  Punto p;
  p.x = r * cosf(a0);
  p.y = r * sinf(a0);
  p.z = H_HOMBRO_MM + L1_MM * cosf(a1) + L2_MM * cosf(a12);
  return p;
}

bool Cinematica::inversa(const Punto &p, float q[3]) {
  float r = sqrtf(p.x * p.x + p.y * p.y);
  float h = p.z - H_HOMBRO_MM;                      // altura relativa al hombro
  float D2 = r * r + h * h;
  float c2 = (D2 - L1_MM * L1_MM - L2_MM * L2_MM) / (2.0f * L1_MM * L2_MM);
  if (c2 > 1.0f || c2 < -1.0f) return false;        // fuera de alcance
  float a2 = acosf(c2);                             // codo hacia delante (q2 > 0)
  // ángulo del objetivo medido desde la vertical (+ hacia delante)
  float phi = atan2f(r, h);
  float a1 = phi - atan2f(L2_MM * sinf(a2), L1_MM + L2_MM * cosf(a2));
  float res[3] = { atan2f(p.y, p.x) / RAD, a1 / RAD, a2 / RAD };
  if (r < 1.0f) res[0] = 0;                         // sobre el eje: la base no importa
  for (uint8_t j = 0; j < 3; j++)
    if (res[j] < LIM_MIN[j] || res[j] > LIM_MAX[j]) return false;
  for (uint8_t j = 0; j < 3; j++) q[j] = res[j];
  return true;
}
