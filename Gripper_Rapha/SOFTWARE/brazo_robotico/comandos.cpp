#include "comandos.h"
#include "config.h"
#include "robot.h"
#include "pinza.h"
#include "tareas.h"
#include "sensores.h"
#include <EEPROM.h>

namespace Comandos {

static char linea[72];
static uint8_t largo = 0;
static char *tok[16];
static uint8_t ntok = 0;

static bool es(uint8_t i, PGM_P s) { return i < ntok && strcmp_P(tok[i], s) == 0; }
static float a_num(const char *t);
static float num(uint8_t i, float def = 0) { return i < ntok ? a_num(tok[i]) : def; }
static bool faltan(uint8_t n) {
  if (ntok < n) { Serial.println(F("! faltan argumentos")); return true; }
  return false;
}
static bool articulacion_ok(int j) {
  if (j < 0 || j > 2) { Serial.println(F("! j: 0 base 1 hombro 2 codo")); return false; }
  return true;
}

// Posturas guardadas en la EEPROM, después de los ajustes
static const uint8_t N_POSES = 8;
static int dir_pose(uint8_t k) { return sizeof(Robot::Ajustes) + 4 + k * 3 * sizeof(float); }

void ayuda() { Serial.println(F("Comandos: ver SOFTWARE/README.md (ESTADO, HOME, J, P, PINZA, APILAR, PID, ESCALON...)")); }

// atof() ocupa mucho en el UNO: lector propio de números con signo y decimales
static float a_num(const char *t) {
  float v = 0, esc = 0; bool neg = false;
  if (*t == '-') { neg = true; t++; } else if (*t == '+') t++;
  for (; *t; t++) {
    if (*t == '.') { esc = 1; continue; }
    if (*t < '0' || *t > '9') break;
    v = v * 10 + (*t - '0'); if (esc) esc *= 10;
  }
  if (esc) v /= esc;
  return neg ? -v : v;
}

static void ejecutar() {
  if (ntok == 0) return;
  if (es(0, PSTR("?")) || es(0, PSTR("AYUDA"))) { ayuda(); return; }
  if (es(0, PSTR("ESTADO")) || es(0, PSTR("E"))) { Robot::imprimir_estado(); return; }
  if (es(0, PSTR("X")) || es(0, PSTR("PARO"))) { Tareas::cancelar(); Robot::apagar(); Serial.println(F("OK paro")); return; }
  if (es(0, PSTR("OFF"))) { Tareas::cancelar(); Robot::apagar(); Serial.println(F("OK motores apagados")); return; }
  if (es(0, PSTR("ON"))) { Robot::encender(); return; }
  if (es(0, PSTR("REARMAR"))) { Robot::rearmar(); return; }
  if (es(0, PSTR("HOME"))) { Tareas::cancelar(); Robot::iniciar_homing(); return; }

  if (Tareas::ocupada() && !es(0, PSTR("LOG"))) { Serial.println(F("! tarea en marcha (X)")); return; }

  if (es(0, PSTR("J"))) {
    if (faltan(4)) return;
    float q[3] = { num(1), num(2), num(3) };
    if (Robot::mover_articular(q, num(4))) Serial.println(F("OK"));
    return;
  }
  if (es(0, PSTR("P"))) {
    if (faltan(4)) return;
    Punto p = { num(1), num(2), num(3) };
    if (Robot::mover_cartesiano(p, num(4))) Serial.println(F("OK"));
    return;
  }
  if (es(0, PSTR("JOG"))) {
    if (faltan(3)) return;
    int j = (int)num(1); if (!articulacion_ok(j)) return;
    float q[3]; Robot::q_consigna(q); q[j] += num(2);
    if (Robot::mover_articular(q)) Serial.println(F("OK"));
    return;
  }
  if (es(0, PSTR("PINZA"))) {
    if (faltan(2)) return;
    if (es(1, PSTR("A"))) Pinza::abrir();
    else if (es(1, PSTR("C"))) Pinza::agarrar(Robot::aj.cubo_mm);
    else Pinza::apertura(num(1));
    Serial.println(F("OK")); return;
  }
  if (es(0, PSTR("CUBO"))) {
    if (faltan(2)) return;
    Robot::aj.cubo_mm = constrain(num(1), 10.0f, 80.0f);
    Serial.print(F("OK cubo de ")); Serial.print(Robot::aj.cubo_mm, 1); Serial.println(F(" mm"));
    return;
  }
  if (es(0, PSTR("COGER"))) { if (faltan(3)) return; Tareas::coger(num(1), num(2)); return; }
  if (es(0, PSTR("DEJAR"))) { if (faltan(4)) return; Tareas::dejar(num(1), num(2), (uint8_t)num(3)); return; }
  if (es(0, PSTR("APILAR"))) {
    if (faltan(5) || (ntok - 3) % 2) { Serial.println(F("! APILAR xp yp x1 y1 ..")); return; }
    float xs[MAX_CUBOS], ys[MAX_CUBOS]; uint8_t n = 0;
    for (uint8_t i = 3; i + 1 < ntok && n < MAX_CUBOS; i += 2, n++) { xs[n] = num(i); ys[n] = num(i + 1); }
    Tareas::apilar(n, xs, ys, num(1), num(2));
    return;
  }
  if (es(0, PSTR("POSE")) || es(0, PSTR("IR"))) {
    if (faltan(2)) return;
    uint8_t k = (uint8_t)num(1); if (k >= N_POSES) { Serial.println(F("! k de 0 a 7")); return; }
    float q[3];
    if (es(0, PSTR("POSE"))) { Robot::q_actual(q); EEPROM.put(dir_pose(k), q); Serial.println(F("OK postura guardada")); }
    else { EEPROM.get(dir_pose(k), q); if (isnan(q[0])) { Serial.println(F("! postura vacia")); return; }
           if (Robot::mover_articular(q)) Serial.println(F("OK")); }
    return;
  }

  // ------------------------------------------------ calibración y ajuste ----------------------------
  if (es(0, PSTR("CAL"))) { if (faltan(3)) return; Robot::calibrar_pot((uint8_t)num(1), num(2)); return; }
  if (es(0, PSTR("SENTIDO"))) {
    if (faltan(2)) return;
    int j = (int)num(1); if (!articulacion_ok(j)) return;
    Robot::prueba_pwm(j, Robot::aj.pwm_min[j] + 40, 0); return;
  }
  if (es(0, PSTR("INV"))) {
    if (faltan(2)) return;
    int j = (int)num(1); if (!articulacion_ok(j)) return;
    Robot::aj.inv_motor[j] ^= 1; Robot::aplicar_ajustes(); Serial.println(F("OK")); return;
  }
  if (es(0, PSTR("INVENC"))) { Robot::aj.enc_signo = -Robot::aj.enc_signo; Robot::aplicar_ajustes(); Serial.println(F("OK")); return; }
  if (es(0, PSTR("FC1"))) { if (faltan(2)) return; Robot::aj.angulo_fc1 = num(1); Serial.println(F("OK")); return; }
  if (es(0, PSTR("SERVO"))) {
    if (faltan(3)) return;
    Robot::aj.servo_cerrado = (int16_t)num(1); Robot::aj.servo_sentido = num(2) < 0 ? -1 : 1;
    Robot::aplicar_ajustes(); Pinza::apertura(Pinza::apertura_actual()); Serial.println(F("OK")); return;
  }
  if (es(0, PSTR("ENC"))) {
    Serial.print(F("ENC cuentas=")); Serial.print(Encoder::cuentas());
    Serial.print(F(" grados=")); Serial.println(Encoder::cuentas() * ENC_GRADOS_CUENTA, 2); return;
  }
  if (es(0, PSTR("PID"))) {
    if (ntok >= 5) {
      int j = (int)num(1); if (!articulacion_ok(j)) return;
      Robot::aj.kp[j] = num(2); Robot::aj.ki[j] = num(3); Robot::aj.kd[j] = num(4); Robot::aplicar_ajustes();
    }
    for (uint8_t j = 0; j < 3; j++) {
      Serial.print(F("PID ")); Serial.print(j); Serial.print(' '); Serial.print(Robot::aj.kp[j], 3); Serial.print(' ');
      Serial.print(Robot::aj.ki[j], 3); Serial.print(' '); Serial.print(Robot::aj.kd[j], 4);
      Serial.print(F("  pwm_min ")); Serial.println(Robot::aj.pwm_min[j]);
    }
    Serial.print(F("G ")); Serial.print(Robot::aj.g_h1, 1); Serial.print(' '); Serial.print(Robot::aj.g_h2, 1);
    Serial.print(' '); Serial.println(Robot::aj.g_c, 1);
    return;
  }
  if (es(0, PSTR("PWMMIN"))) {
    if (faltan(3)) return;
    int j = (int)num(1); if (!articulacion_ok(j)) return;
    Robot::aj.pwm_min[j] = (int16_t)num(2); Robot::aplicar_ajustes(); Serial.println(F("OK")); return;
  }
  if (es(0, PSTR("G"))) {
    if (faltan(4)) return;
    Robot::aj.g_h1 = num(1); Robot::aj.g_h2 = num(2); Robot::aj.g_c = num(3); Serial.println(F("OK")); return;
  }
  if (es(0, PSTR("CARGA"))) { if (faltan(2)) return; Robot::imprimir_carga((uint8_t)num(1)); return; }
  if (es(0, PSTR("PWM"))) {
    if (faltan(4)) return;
    int j = (int)num(1); if (!articulacion_ok(j)) return;
    Robot::prueba_pwm(j, (int16_t)num(2), (uint16_t)max(num(3), 50.0f)); return;
  }
  if (es(0, PSTR("ESCALON"))) {
    if (faltan(3)) return;
    int j = (int)num(1); if (!articulacion_ok(j)) return;
    Robot::escalon(j, num(2), (uint16_t)num(3, 3000)); return;
  }
  if (es(0, PSTR("AUTOTUNE"))) {
    if (faltan(2)) return;
    int j = (int)num(1); if (!articulacion_ok(j)) return;
    Robot::autotune(j, (int16_t)num(2, 70)); return;
  }
  if (es(0, PSTR("LOG"))) { Robot::registro(num(1) != 0); return; }
  if (es(0, PSTR("GUARDAR"))) { Robot::guardar(); return; }
  if (es(0, PSTR("DEFECTO"))) { Robot::ajustes_por_defecto(); Robot::aplicar_ajustes(); Serial.println(F("OK defecto")); return; }

  Serial.print(F("! comando desconocido: ")); Serial.println(tok[0]);
}

void leer() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      linea[largo] = 0;
      ntok = 0;
      for (char *t = strtok(linea, " ,;\t"); t && ntok < 16; t = strtok(NULL, " ,;\t")) {
        for (char *p = t; *p; p++) *p = toupper(*p);
        tok[ntok++] = t;
      }
      ejecutar();
      largo = 0;
    } else if (largo < sizeof(linea) - 1) linea[largo++] = c;
  }
}

} // namespace Comandos
