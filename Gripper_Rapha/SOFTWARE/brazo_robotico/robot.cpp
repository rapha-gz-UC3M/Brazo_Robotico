#include "robot.h"
#include "config.h"
#include "motor.h"
#include "sensores.h"
#include "pid.h"
#include "pinza.h"
#include <EEPROM.h>

namespace Robot {

Ajustes aj;
static const uint16_t MAGIA = 0xB3A7;          // cambia si cambia la estructura Ajustes
static const float DT = PERIODO_CONTROL_US * 1e-6f;

static Motor motor[3];
static Potenciometro pot[2];
static PID pid[3];
static Modo modo_ = PARADO;
static bool referenciada = false;

static float q[3], qref[3], vel[3], u[3];
static float q_ant[3];

// ---- trayectoria ----
static uint8_t tray_tipo = 0;                  // 0 ninguna, 1 articular, 2 cartesiana
static uint32_t tray_t0;
static float tray_T;
static float tq0[3], tq1[3];
static Punto tp0, tp1;
static bool asentando = false, fallo_lleg = false;
static uint32_t t_dentro = 0, t_fin_tray = 0;

// ---- pruebas ----
static uint8_t prueba_j; static int16_t prueba_pwm_v; static uint32_t prueba_fin; static bool prueba_sentido = false;
static float prueba_q0, prueba_dq_ref; static bool prueba_ctrl;
static uint32_t escalon_fin = 0;
static bool registrando = false; static uint8_t div_reg = 0;
static uint32_t t_bloqueo[3] = {0, 0, 0};
static int8_t carga_j = -1; static float carga_suma = 0; static uint16_t carga_n = 0;

// ---- homing ----
static uint32_t homing_t0; static long homing_c0;

// ---- autotune (relé) ----
static struct {
  uint8_t j; int16_t d; uint8_t fase; float centro, bias, sum_b; uint16_t n_b;
  int8_t s; uint32_t t0, t_ult; float qmax, qmin; uint8_t ciclos; float sum_T, sum_a; uint8_t n;
} at;

// ======================================================================================================
static void leer_sensores() {
  pot[0].leer(); pot[1].leer();
  q[0] = Encoder::cuentas() * ENC_GRADOS_CUENTA;
  q[1] = pot[0].grados();
  q[2] = pot[1].grados();
  for (uint8_t j = 0; j < 3; j++) {
    vel[j] += 0.3f * ((q[j] - q_ant[j]) / DT - vel[j]);
    q_ant[j] = q[j];
  }
}

static float gravedad(uint8_t j) {
  const float R = 0.01745329252f;
  float s1 = sinf(q[1] * R), s12 = sinf((q[1] + q[2]) * R);
  if (j == 1) return -(aj.g_h1 * s1 + aj.g_h2 * s12);
  if (j == 2) return -(aj.g_c * s12);
  return 0;
}

// recorta el PWM si empuja más allá de un límite (software o final de carrera)
static float proteger(uint8_t j, float v) {
  if (q[j] <= LIM_MIN[j] - 2.0f && v < 0) v = 0;
  if (q[j] >= LIM_MAX[j] + 2.0f && v > 0) v = 0;
  if (j == 0) {
    if (FinalesCarrera::fc1() && v < 0) v = 0;
    if (FinalesCarrera::fc2() && v > 0) v = 0;
  }
  return v;
}

static float q_vig[3]; static uint8_t n_vig[3], reves[3]; static float q_bloq[3];
static void vigilar(uint8_t j);
static void reset_vigilancia() { for (uint8_t j = 0; j < 3; j++) { q_vig[j] = q[j]; n_vig[j] = 0; reves[j] = 0; t_bloqueo[j] = 0; } }
static void control_articulacion(uint8_t j) {
  motor[j].comandar((int16_t)lroundf(proteger(j, pid[j].calcular(qref[j], q[j], gravedad(j), DT))));
  u[j] = motor[j].pwm();                     // el PWM aplicado de verdad (tras la rampa y los límites)
  vigilar(j);
}

// Vigilancia cada 250 ms con la variación de posición (la velocidad instantánea es muy ruidosa):
//  - empuja fuerte y la articulación va hacia el otro lado -> motor invertido (o sin fuerza)
//  - PWM casi al máximo y no se mueve durante TIEMPO_BLOQUEO_MS -> bloqueado
static void vigilar(uint8_t j) {
  if (fabs(u[j]) >= 0.9f * motor[j].pwm_max) {
    if (t_bloqueo[j] == 0 || fabs(q[j] - q_bloq[j]) > 1.5f) { t_bloqueo[j] = millis(); q_bloq[j] = q[j]; }
    else if (millis() - t_bloqueo[j] > TIEMPO_BLOQUEO_MS) {
      Serial.print(F("! j=")); Serial.println(j); fallo(F("motor bloqueado")); return;
    }
  } else t_bloqueo[j] = 0;
  if (++n_vig[j] >= 25) {
    float dq = q[j] - q_vig[j];
    // dos ventanas seguidas (0,5 s): una sola puede ser la inercia al frenar
    if (fabs(u[j]) > 0.5f * motor[j].pwm_max && (u[j] > 0 ? dq < -2.0f : dq > 2.0f)) {
      if (++reves[j] >= 2) { Serial.print(F("! j=")); Serial.println(j); fallo(F("se mueve al reves del motor (SENTIDO j) o no tiene fuerza")); return; }
    } else reves[j] = 0;
    n_vig[j] = 0; q_vig[j] = q[j];
  }
}

static float minjerk(float t) {               // 0..1 -> 0..1, velocidad y aceleración nulas en los extremos
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  return t * t * t * (10.0f + t * (-15.0f + 6.0f * t));
}

static void actualizar_trayectoria() {
  if (tray_tipo) {
    float t = (millis() - tray_t0) * 0.001f / tray_T;
    float s = minjerk(t);
    if (tray_tipo == 1) {
      for (uint8_t j = 0; j < 3; j++) qref[j] = tq0[j] + s * (tq1[j] - tq0[j]);
    } else {
      Punto p = { tp0.x + s * (tp1.x - tp0.x), tp0.y + s * (tp1.y - tp0.y), tp0.z + s * (tp1.z - tp0.z) };
      float qq[3];
      if (Cinematica::inversa(p, qq)) for (uint8_t j = 0; j < 3; j++) qref[j] = qq[j];
      else { Serial.println(F("! fuera de alcance")); parar_movimiento(); fallo_lleg = true; return; }
    }
    if (t >= 1) { tray_tipo = 0; asentando = true; t_fin_tray = millis(); t_dentro = 0; }
  } else if (asentando) {
    bool dentro = true;
    for (uint8_t j = 0; j < 3; j++) if (fabs(qref[j] - q[j]) > TOLERANCIA_GRADOS[j] * 1.5f) dentro = false;
    if (dentro) {
      if (t_dentro == 0) t_dentro = millis();
      if (millis() - t_dentro >= TIEMPO_LLEGADA_MS) asentando = false;
    } else t_dentro = 0;
    if (asentando && millis() - t_fin_tray > TIEMPO_EXTRA_MS) {
      asentando = false; fallo_lleg = true;
      Serial.print(F("! no llega. Error: "));
      for (uint8_t j = 0; j < 3; j++) { Serial.print(qref[j] - q[j], 1); Serial.print(' '); }
      Serial.println();
    }
  }
}

static void registrar() {
  if (!registrando || ++div_reg < 2) return;    // 50 Hz
  div_reg = 0;
  Serial.print(F("L,")); Serial.print(millis());
  for (uint8_t j = 0; j < 3; j++) {
    Serial.print(','); Serial.print(qref[j], 2); Serial.print(','); Serial.print(q[j], 2);
    Serial.print(','); Serial.print((int)u[j]);
  }
  Serial.println();
}

// ------------------------------------------------------------------------ homing -------------------------
static void ciclo_homing() {
  control_articulacion(1); control_articulacion(2);       // hombro y codo quietos
  if (FinalesCarrera::fc2()) {
    fallo(F("homing: pisa FC2 en vez de FC1 (SENTIDO 0 o cambia los finales)"));
    return;
  }
  if (FinalesCarrera::fc1()) {
    motor[0].parar();
    Encoder::fijar(lroundf(aj.angulo_fc1 / ENC_GRADOS_CUENTA));
    q[0] = q_ant[0] = aj.angulo_fc1; vel[0] = 0;
    referenciada = true;
    for (uint8_t j = 0; j < 3; j++) { qref[j] = q[j]; pid[j].reset(q[j]); }
    reset_vigilancia();
    modo_ = CONTROL;
    Serial.println(F("OK homing"));
    float dest[3] = { 0, q[1], q[2] };
    mover_articular(dest);
    return;
  }
  uint32_t t = millis() - homing_t0;
  long dc = Encoder::cuentas() - homing_c0;
  if (t > 1500 && labs(dc) < 15) { fallo(F("homing: la base no se mueve o el encoder no cuenta")); return; }
  if (t > 1500 && dc > 0) { fallo(F("homing: encoder al reves (SENTIDO 0)")); return; }
  if (t > TIEMPO_MAX_HOMING) { fallo(F("homing: no encuentra FC1")); return; }
  motor[0].comandar(-PWM_HOMING);
}

// ------------------------------------------------------------------------ autotune ----------------------
static void ciclo_autotune() {
  for (uint8_t j = 0; j < 3; j++) if (j != at.j) control_articulacion(j);
  uint8_t j = at.j;
  uint32_t ahora = millis();
  if (at.fase == 0) {                         // 1,5 s sujetando con el PID para medir el PWM de equilibrio
    control_articulacion(j);
    if (ahora - at.t0 > 800) { at.sum_b += u[j]; at.n_b++; }
    if (ahora - at.t0 > 1500) {
      at.bias = at.n_b ? at.sum_b / at.n_b : 0;
      at.fase = 1; at.s = 1; at.t_ult = 0; at.ciclos = 0; at.n = 0; at.sum_T = at.sum_a = 0;
      at.qmax = -1e9; at.qmin = 1e9;
      Serial.print(F("autotune: equilibrio ")); Serial.println(at.bias, 1);
    }
    return;
  }
  const float h = 0.3f;                       // histéresis (grados) contra el ruido
  float e = at.centro - q[j];
  at.qmax = max(at.qmax, q[j]); at.qmin = min(at.qmin, q[j]);
  if (at.s > 0 && e < -h) at.s = -1;
  else if (at.s < 0 && e > h) {               // cambio a + : cierra un ciclo completo
    at.s = 1;
    if (at.t_ult) {
      at.ciclos++;
      if (at.ciclos > 2) { at.sum_T += (ahora - at.t_ult) * 0.001f; at.sum_a += (at.qmax - at.qmin) * 0.5f; at.n++; }
    }
    at.t_ult = ahora; at.qmax = -1e9; at.qmin = 1e9;
  }
  motor[j].comandar((int16_t)lroundf(proteger(j, at.bias + at.s * at.d)));
  u[j] = motor[j].pwm();
  bool lejos = fabs(q[j] - at.centro) > 20.0f;
  if (lejos || ahora - at.t0 > 30000UL) {
    motor[j].parar(); qref[j] = q[j]; pid[j].reset(q[j]); modo_ = CONTROL; registro(false); reset_vigilancia();
    Serial.println(lejos ? F("! autotune: baja d") : F("! autotune: sube d"));
    return;
  }
  if (at.n >= 4) {
    float Pu = at.sum_T / at.n, a = at.sum_a / at.n;
    float Ku = 4.0f * at.d / (PI * a);
    motor[j].parar(); qref[j] = at.centro; pid[j].reset(q[j]); modo_ = CONTROL; registro(false); reset_vigilancia();
    Serial.print(F("RESULTADO autotune j=")); Serial.print(j);
    Serial.print(F("  Ku=")); Serial.print(Ku, 3); Serial.print(F(" Pu=")); Serial.print(Pu, 3);
    Serial.print(F(" a=")); Serial.print(a, 2); Serial.println(F(" grados"));
    // reglas de Ziegler-Nichols (oscilación sostenida) y variantes más suaves
    Serial.print(F("  ZN clasico: ")); Serial.print(0.6f * Ku, 3); Serial.print(' ');
    Serial.print(1.2f * Ku / Pu, 3); Serial.print(' '); Serial.println(0.075f * Ku * Pu, 4);
    Serial.print(F("  ZN sin sobreosc: ")); Serial.print(0.2f * Ku, 3); Serial.print(' ');
    Serial.print(0.4f * Ku / Pu, 3); Serial.print(' '); Serial.println(0.0667f * Ku * Pu, 4);
  }
}

// ======================================================================================================
void ajustes_por_defecto() {
  aj.magia = MAGIA;
  // calibración de partida: centro del potenciómetro = 0°; se corrige con CAL
  aj.pot_adc0[0] = 512; aj.pot_k[0] = POT_GRADOS_CUENTA;
  aj.pot_adc0[1] = 512 - 100.0f / POT_GRADOS_CUENTA; aj.pot_k[1] = POT_GRADOS_CUENTA;
  for (uint8_t j = 0; j < 3; j++) { aj.kp[j] = KP_INI[j]; aj.ki[j] = KI_INI[j]; aj.kd[j] = KD_INI[j]; aj.inv_motor[j] = 0; }
  aj.pwm_min[0] = PWM_MIN_BASE; aj.pwm_min[1] = PWM_MIN_HOMBRO; aj.pwm_min[2] = PWM_MIN_CODO;
  aj.g_h1 = G_HOMBRO_1_INI; aj.g_h2 = G_HOMBRO_2_INI; aj.g_c = G_CODO_INI;
  aj.enc_signo = 1;
  aj.servo_cerrado = SERVO_CERRADO_INI; aj.servo_sentido = SERVO_SENTIDO_INI;
  aj.angulo_fc1 = ANGULO_FC1;
  aj.cubo_mm = CUBO_MM_INI;
}

bool cargar() {
  EEPROM.get(0, aj);
  if (aj.magia != MAGIA) { ajustes_por_defecto(); return false; }
  return true;
}
void guardar() { EEPROM.put(0, aj); Serial.println(F("OK ajustes guardados en la EEPROM")); }

void aplicar_ajustes() {
  pot[0].adc0 = aj.pot_adc0[0]; pot[0].k = aj.pot_k[0];
  pot[1].adc0 = aj.pot_adc0[1]; pot[1].k = aj.pot_k[1];
  for (uint8_t j = 0; j < 3; j++) {
    pid[j].kp = aj.kp[j]; pid[j].ki = aj.ki[j]; pid[j].kd = aj.kd[j];
    pid[j].pwm_min = aj.pwm_min[j];
    motor[j].invertir(aj.inv_motor[j]);
  }
  Encoder::signo = aj.enc_signo;
  Pinza::servo_cerrado = aj.servo_cerrado; Pinza::sentido = aj.servo_sentido;
}

void begin() {
  bool habia = cargar();
  motor[0].begin(PIN_M_BASE, PWM_MAX_BASE, aj.inv_motor[0]);
  motor[1].begin(PIN_M_HOMBRO, PWM_MAX_HOMBRO, aj.inv_motor[1]);
  motor[2].begin(PIN_M_CODO, PWM_MAX_CODO, aj.inv_motor[2]);
  Encoder::begin(); FinalesCarrera::begin();
  pot[0].begin(PIN_POT_HOMBRO, 0, 0); pot[1].begin(PIN_POT_CODO, 0, 0);
  for (uint8_t j = 0; j < 3; j++) {
    pid[j].i_max = I_MAX; pid[j].filtro_d = D_FILTRO; pid[j].tolerancia = TOLERANCIA_GRADOS[j];
    pid[j].pwm_max = motor[j].pwm_max;
  }
  aplicar_ajustes();
  Pinza::begin(aj.servo_cerrado, aj.servo_sentido);
  for (uint8_t i = 0; i < 8; i++) leer_sensores();
  for (uint8_t j = 0; j < 3; j++) { qref[j] = q_ant[j] = q[j]; vel[j] = 0; u[j] = 0; }
  Serial.println(habia ? F("Ajustes cargados de la EEPROM") : F("EEPROM vacia: ajustes por defecto"));
}

Modo modo() { return modo_; }

void encender() {
  if (modo_ == FALLO) { Serial.println(F("! en fallo: REARMAR")); return; }
  for (uint8_t j = 0; j < 3; j++) { qref[j] = q[j]; pid[j].reset(q[j]); }
  reset_vigilancia();
  tray_tipo = 0; asentando = false;
  modo_ = CONTROL;
  Serial.println(referenciada ? F("OK control") : F("OK control (base sin HOME)"));
}

void apagar() {
  for (uint8_t j = 0; j < 3; j++) { motor[j].parar(); u[j] = 0; }
  tray_tipo = 0; asentando = false; registro(false);
  if (modo_ != FALLO) modo_ = PARADO;
}

void fallo(const __FlashStringHelper *motivo) {
  for (uint8_t j = 0; j < 3; j++) { motor[j].parar(); u[j] = 0; }
  tray_tipo = 0; asentando = false; fallo_lleg = true; registrando = false;
  modo_ = FALLO;
  Serial.print(F("!! FALLO: ")); Serial.println(motivo);
  Serial.println(F("!! motores parados. REARMAR"));
}

void rearmar() {
  modo_ = PARADO;
  for (uint8_t j = 0; j < 3; j++) if (j > 0 && !pot[j - 1].ok()) { fallo(F("pot sin senal")); return; }
  encender();
}

void parar_movimiento() { tray_tipo = 0; asentando = false; }

void q_actual(float o[3]) { for (uint8_t j = 0; j < 3; j++) o[j] = q[j]; }
void q_consigna(float o[3]) { for (uint8_t j = 0; j < 3; j++) o[j] = qref[j]; }
bool base_referenciada() { return referenciada; }
bool moviendo() { return tray_tipo != 0 || asentando; }
bool fallo_llegada() { return fallo_lleg; }

static bool puede_mover() {
  if (modo_ != CONTROL) { Serial.println(F("! control inactivo (ON/HOME)")); return false; }
  return true;
}

bool mover_articular(const float dest[3], float dur) {
  if (!puede_mover()) return false;
  float d[3];
  for (uint8_t j = 0; j < 3; j++) d[j] = constrain(dest[j], LIM_MIN[j], LIM_MAX[j]);
  if (!referenciada && fabs(d[0] - qref[0]) > 0.5f) { Serial.println(F("! base sin HOME")); return false; }
  float T = 0;
  for (uint8_t j = 0; j < 3; j++) { tq0[j] = qref[j]; tq1[j] = d[j]; T = max(T, 1.875f * fabs(d[j] - qref[j]) / VEL_MAX[j]); }
  tray_T = max(dur, max(T, 0.3f));
  tray_t0 = millis(); tray_tipo = 1; asentando = false; fallo_lleg = false;
  return true;
}

bool mover_cartesiano(const Punto &p, float dur) {
  if (!puede_mover()) return false;
  if (!referenciada) { Serial.println(F("! base sin HOME")); return false; }
  float qf[3];
  if (!Cinematica::inversa(p, qf)) { Serial.println(F("! fuera de alcance")); return false; }
  tp0 = Cinematica::directa(qref); tp1 = p;
  float T = 0;
  for (uint8_t j = 0; j < 3; j++) T = max(T, 1.875f * fabs(qf[j] - qref[j]) / VEL_MAX[j]);
  float dist = sqrtf(sq(p.x - tp0.x) + sq(p.y - tp0.y) + sq(p.z - tp0.z));
  T = max(T, 1.875f * dist / 80.0f);         // 80 mm/s de media
  tray_T = max(dur, max(T, 0.3f));
  tray_t0 = millis(); tray_tipo = 2; asentando = false; fallo_lleg = false;
  return true;
}

void iniciar_homing() {
  if (modo_ == FALLO) { Serial.println(F("! en fallo: REARMAR")); return; }
  if (modo_ != CONTROL) encender();
  tray_tipo = 0; asentando = false;
  homing_t0 = millis(); homing_c0 = Encoder::cuentas();
  modo_ = HOMING;
  Serial.println(F("homing..."));
}

void registro(bool on) {
  if (on && !registrando) Serial.println(F("CSV,t_ms,ref0,q0,u0,ref1,q1,u1,ref2,q2,u2"));
  if (!on && registrando) Serial.println(F("FIN"));
  registrando = on; div_reg = 0;
}

void prueba_pwm(uint8_t j, int16_t pwm, uint16_t ms) {
  if (modo_ != CONTROL && modo_ != PARADO && modo_ != FALLO) return;
  prueba_ctrl = modo_ == CONTROL;             // si no hay control, el resto de motores siguen parados
  prueba_sentido = (ms == 0);                 // ms = 0 -> detectar el sentido
  prueba_j = j; prueba_pwm_v = pwm; prueba_fin = millis() + (prueba_sentido ? 350 : ms);
  prueba_q0 = q[j]; tray_tipo = 0; asentando = false;
  modo_ = PRUEBA;
  if (!prueba_sentido) registro(true);
}

void escalon(uint8_t j, float delta, uint16_t ms) {
  if (!puede_mover()) return;
  tray_tipo = 0; asentando = false;
  registro(true);
  qref[j] = constrain(qref[j] + delta, LIM_MIN[j], LIM_MAX[j]);
  escalon_fin = millis() + ms;
}

void autotune(uint8_t j, int16_t d) {
  if (!puede_mover()) return;
  tray_tipo = 0; asentando = false;
  at.j = j; at.d = d; at.fase = 0; at.centro = q[j]; at.sum_b = 0; at.n_b = 0; at.t0 = millis();
  qref[j] = q[j];
  modo_ = AUTOTUNE;
  registro(true);
  Serial.println(F("autotune..."));
}

void imprimir_carga(uint8_t j) { carga_j = j; carga_suma = 0; carga_n = 0; }

void calibrar_pot(uint8_t j, float ang) {
  static float c_adc[2], c_ang[2]; static bool tiene[2] = { false, false };
  if (j < 1 || j > 2) { Serial.println(F("! CAL j=1|2")); return; }
  uint8_t k = j - 1; float adc = pot[k].filtrado;
  if (!tiene[k] || fabs(ang - c_ang[k]) < 20.0f) {
    c_adc[k] = adc; c_ang[k] = ang; tiene[k] = true;
    aj.pot_adc0[k] = adc - ang / aj.pot_k[k];            // de momento solo desplaza el cero
    Serial.println(F("OK punto 1; repite CAL en otro angulo (>20 grados)"));
  } else {
    if (fabs(adc - c_adc[k]) < 20) { Serial.println(F("! el pot no cambia")); return; }
    aj.pot_k[k] = (ang - c_ang[k]) / (adc - c_adc[k]);
    aj.pot_adc0[k] = c_adc[k] - c_ang[k] / aj.pot_k[k];
    tiene[k] = false;
    Serial.print(F("OK calibrado: ")); Serial.print(aj.pot_k[k], 4); Serial.println(F(" grados/cuenta"));
  }
  aplicar_ajustes();
  leer_sensores(); qref[j] = q[j]; pid[j].reset(q[j]); reset_vigilancia();
}

// ======================================================================================================
void ciclo() {
  leer_sensores();
  if (modo_ != PARADO && modo_ != FALLO) {
    if (!pot[0].ok()) { fallo(F("pot del hombro sin senal")); return; }
    if (!pot[1].ok()) { fallo(F("pot del codo sin senal")); return; }
  }
  switch (modo_) {
    case CONTROL:
      actualizar_trayectoria();
      for (uint8_t j = 0; j < 3; j++) control_articulacion(j);
      if (escalon_fin && (int32_t)(millis() - escalon_fin) >= 0) { escalon_fin = 0; registro(false); }
      break;
    case HOMING: ciclo_homing(); break;
    case AUTOTUNE: ciclo_autotune(); break;
    case PRUEBA: {
      if (prueba_ctrl) for (uint8_t j = 0; j < 3; j++) if (j != prueba_j) control_articulacion(j);
      motor[prueba_j].comandar((int16_t)proteger(prueba_j, prueba_pwm_v));
      u[prueba_j] = motor[prueba_j].pwm();
      bool limite = (q[prueba_j] < LIM_MIN[prueba_j] && prueba_pwm_v < 0) || (q[prueba_j] > LIM_MAX[prueba_j] && prueba_pwm_v > 0);
      if (prueba_sentido && prueba_pwm_v > 0 && (int32_t)(millis() - prueba_fin) >= 0) {
        // SENTIDO: primero +PWM y luego -PWM; se compara (así la gravedad no engaña)
        prueba_q0 = q[prueba_j] - prueba_q0;  // guarda lo que se movió con +PWM
        prueba_pwm_v = -prueba_pwm_v; prueba_fin = millis() + 350;
        prueba_dq_ref = q[prueba_j];
        break;
      }
      if ((int32_t)(millis() - prueba_fin) >= 0 || limite) {
        motor[prueba_j].parar();
        if (prueba_sentido) {
          float dq = prueba_q0 - (q[prueba_j] - prueba_dq_ref);   // (con +PWM) - (con -PWM)
          Serial.print(F("SENTIDO j=")); Serial.print(prueba_j); Serial.print(F(" diferencia=")); Serial.print(dq, 2);
          if (fabs(dq) < 0.5f) Serial.println(F(" -> no se mueve"));
          else if (dq > 0) Serial.println(F(" -> correcto"));
          else { aj.inv_motor[prueba_j] ^= 1; motor[prueba_j].invertir(aj.inv_motor[prueba_j]);
                 Serial.println(F(" -> invertido")); }
        } else registro(false);
        if (limite) Serial.println(F("! limite"));
        qref[prueba_j] = q[prueba_j]; pid[prueba_j].reset(q[prueba_j]); reset_vigilancia();
        u[prueba_j] = 0;
        modo_ = prueba_ctrl ? CONTROL : PARADO;
      }
      break;
    }
    default: break;
  }
  Pinza::actualizar(DT);
  if (carga_j >= 0 && modo_ == CONTROL) {
    carga_suma += u[carga_j]; carga_n++;
    if (carga_n >= 100) {
      const float R = 0.01745329252f;
      Serial.print(F("CARGA j=")); Serial.print(carga_j); Serial.print(F(" PWM medio=")); Serial.print(carga_suma / carga_n, 1);
      Serial.print(F(" sin(q1)=")); Serial.print(sinf(q[1] * R), 3);
      Serial.print(F(" sin(q1+q2)=")); Serial.println(sinf((q[1] + q[2]) * R), 3);
      carga_j = -1;
    }
  }
  registrar();
}

void imprimir_estado() {
  Serial.print(F("ESTADO modo=")); Serial.print(modo_);
  Serial.print(F(" home=")); Serial.print(referenciada);
  Serial.print(F(" mov=")); Serial.println(moviendo());
  Serial.print(F(" q=")); for (uint8_t j = 0; j < 3; j++) { Serial.print(q[j], 1); Serial.print(' '); }
  Serial.print(F(" ref=")); for (uint8_t j = 0; j < 3; j++) { Serial.print(qref[j], 1); Serial.print(' '); }
  Serial.print(F(" pwm=")); for (uint8_t j = 0; j < 3; j++) { Serial.print((int)u[j]); Serial.print(' '); }
  Serial.print(F(" I=")); for (uint8_t j = 0; j < 3; j++) { Serial.print(pid[j].i, 1); Serial.print(' '); }
  Punto p = Cinematica::directa(q);
  Serial.print(F("\n TCP=")); Serial.print(p.x, 0); Serial.print(' '); Serial.print(p.y, 0); Serial.print(' '); Serial.print(p.z, 0);
  Serial.print(F(" adc=")); Serial.print(pot[0].crudo); Serial.print(' '); Serial.print(pot[1].crudo);
  Serial.print(F(" enc=")); Serial.print(Encoder::cuentas());
  Serial.print(F(" fc=")); Serial.print(FinalesCarrera::fc1()); Serial.print(FinalesCarrera::fc2());
  Serial.print(F(" pinza=")); Serial.print(Pinza::apertura_actual(), 1);
  Serial.print(F(" cubo=")); Serial.println(aj.cubo_mm, 1);
}

} // namespace Robot
