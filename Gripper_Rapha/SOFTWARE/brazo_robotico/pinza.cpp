#include "pinza.h"
#include "config.h"
#include <Servo.h>

namespace Pinza {
  int16_t servo_cerrado = SERVO_CERRADO_INI;
  int8_t sentido = SERVO_SENTIDO_INI;
  static Servo servo;
  static float giro = 0, giro_obj = 0;      // giro desde "cerrado" (0..90°)

  static void escribir() {
    int16_t v = servo_cerrado + (int16_t)lroundf(giro) * sentido;
    servo.write(constrain(v, 0, 180));
  }

  // interpolación lineal en la tabla del CAD (giro del servo <-> apertura entre mordazas)
  static float interp(float x, const float *xs, const float *ys) {
    if (x <= xs[0]) return ys[0];
    for (uint8_t i = 1; i < PINZA_N; i++)
      if (x <= xs[i]) return ys[i - 1] + (x - xs[i - 1]) * (ys[i] - ys[i - 1]) / (xs[i] - xs[i - 1]);
    return ys[PINZA_N - 1];
  }
  float giro_desde_apertura(float mm) { return interp(mm, PINZA_APERTURA, PINZA_GIRO); }
  float apertura_actual() { return interp(giro, PINZA_GIRO, PINZA_APERTURA); }

  void begin(int16_t cerrado, int8_t s) {
    servo_cerrado = cerrado; sentido = s;
    giro = giro_obj = giro_desde_apertura(40.0f);   // arranca a media apertura
    servo.attach(PIN_SERVO);
    escribir();
  }
  void apertura(float mm) { giro_obj = giro_desde_apertura(mm); }
  void abrir() { giro_obj = PINZA_GIRO[PINZA_N - 1] * 0.85f; }   // ~85 mm, sin forzar el tope
  void agarrar(float cubo_mm) { apertura(max(cubo_mm - PINZA_APRIETE_MM, PINZA_APERTURA[0])); }
  void actualizar(float dt) {
    float paso = PINZA_VEL * dt;
    if (giro < giro_obj) giro = min(giro + paso, giro_obj);
    else if (giro > giro_obj) giro = max(giro - paso, giro_obj);
    escribir();
  }
  bool quieta() { return fabs(giro - giro_obj) < 0.5f; }
}
