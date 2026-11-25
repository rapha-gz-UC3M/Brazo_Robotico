// =====================================================================================================
//  brazo_prueba.ino  -  Primera prueba del brazo robótico (UC3M). Un solo archivo para el Arduino IDE.
//
//  Qué hace:
//    - Control PID de base (encoder), hombro y codo (potenciómetros) a 100 Hz.
//    - Homing de la base contra el final de carrera 1.
//    - Movimientos por órdenes desde el Monitor Serie (115200 baudios, "Nueva línea"):
//         base 20     gira la base 20 grados        hombro -10     codo 15
//    - Velocidad muy limitada y paradas de seguridad (ver "SEGURIDAD" abajo).
//
//  SIGNO: positivo = el eje del MOTOR gira en sentido HORARIO mirándolo de frente (desde la punta del eje).
//  Los grados son de la articulación. En la base el motor va directo, así que el brazo gira igual que el
//  eje. En hombro y codo hay engranajes 3:1: la articulación gira 1/3 de lo que gira el motor y en sentido
//  contrario a él, pero el signo sigue siendo el del eje del motor.
//
//  ANTES DE MOVER NADA (una vez; se guarda con "guardar"):
//    1. prueba base / prueba hombro / prueba codo
//         Da un pequeño giro positivo y luego vuelve. Mira el eje del motor en el PRIMER giro.
//         Si giró en sentido antihorario, escribe:  invertir base   (o hombro, o codo)
//    2. cero hombro / cero codo     con el brazo en la postura que quieras llamar 0 (mejor a media carrera)
//    3. home                        la base busca el final de carrera 1 y vuelve a 0
//    4. guardar
//
//  Conexiones (controladores DRV8871):
//    Base:   IN1 D5,  IN2 D7      Encoder C1 D2, C2 D4      FC1 D3 (el que se alcanza girando en +), FC2 D10
//    Hombro: IN1 D6,  IN2 D12     Potenciómetro A0
//    Codo:   IN1 D11, IN2 A2      Potenciómetro A1          Servo de la pinza: D9
// =====================================================================================================
#include <Servo.h>
#include <EEPROM.h>
#include <avr/wdt.h>

// ---------------------------------------------- PINES ------------------------------------------------
const uint8_t PIN_ENC_A = 2, PIN_ENC_B = 4, PIN_FC1 = 3, PIN_FC2 = 10, PIN_SERVO = 9;
const uint8_t PIN_POT[2] = { A0, A1 };              // hombro, codo
const uint8_t PIN_IN1[3] = { 5, 6, 11 };            // base, hombro, codo (con PWM)
const uint8_t PIN_IN2[3] = { 7, 12, A2 };           // sentido

// ---------------------------------------------- LÍMITES DE ESTA PRIMERA PRUEBA ------------------------
const int16_t PWM_MAX[3]   = { 110, 170, 150 };     // de 255. El hombro necesita más para sostener el brazo
const int16_t PWM_MIN[3]   = { 35, 40, 40 };        // PWM mínimo que vence el rozamiento (zona muerta)
const int16_t PWM_RAMPA    = 8;                     // cambio máximo de PWM por ciclo (arranques suaves)
const int16_t PWM_PRUEBA[3]= { 60, 90, 80 };        // empujón de la orden "prueba"
const int16_t PWM_HOMING   = 55;
const float   VEL_DEF[3]   = { 10, 8, 8 };          // grados/s por defecto
const float   VEL_TOPE     = 20;                    // grados/s: no se deja pasar de aquí
const float   PASO_MAX     = 45;                    // grados como máximo en una sola orden
const float   LIM_BASE     = 75;                    // ± grados de la base, después del home
const float   LIM_POT      = 70;                    // ± grados de hombro y codo respecto a su "cero"
const float   TOL          = 0.8;                   // grados: tolerancia para dar un movimiento por hecho

// ---------------------------------------------- SENSORES ---------------------------------------------
const float ENC_CUENTAS_VUELTA = 22.0 * 131.0;      // 11 pulsos x 2 flancos x reductora 1:131
const float POT_GRADOS_CUENTA  = 300.0 / 1023.0;    // potenciómetro de 300° en el eje de la articulación
const int   POT_MIN_OK = 8, POT_MAX_OK = 1015;      // fuera de esto: cable suelto -> paro

const char *NOMBRE[3] = { "base", "hombro", "codo" };
const float DT = 0.01;                              // 100 Hz

// ---------------------------------------------- AJUSTES GUARDADOS EN EEPROM ---------------------------
struct Ajustes {
  uint16_t magia;
  int8_t inv[3];          // 1 = invertir el motor para que + sea horario
  int8_t sgn[3];          // signo del sensor respecto al motor (lo mide "prueba")
  uint8_t probado[3];     // 1 = "prueba" hecha
  float cero[2];          // cero de hombro y codo (grados del sensor)
  float kp[3], ki[3], kd[3];
  float vel[3];
  float ang_fc1;          // ángulo de la base cuando pisa el final de carrera 1
};
const uint16_t MAGIA = 0xB5A2;
Ajustes aj;

void ajustesPorDefecto() {
  aj.magia = MAGIA;
  for (uint8_t j = 0; j < 3; j++) { aj.inv[j] = 0; aj.sgn[j] = 1; aj.probado[j] = 0; aj.vel[j] = VEL_DEF[j]; }
  aj.cero[0] = aj.cero[1] = 0;
  const float kp[3] = { 6, 14, 10 }, ki[3] = { 4, 20, 16 }, kd[3] = { 0.25, 0.6, 0.4 };
  for (uint8_t j = 0; j < 3; j++) { aj.kp[j] = kp[j]; aj.ki[j] = ki[j]; aj.kd[j] = kd[j]; }
  aj.ang_fc1 = 80;
}

// ---------------------------------------------- ESTADO ------------------------------------------------
enum Modo : uint8_t { APAGADO, ACTIVO, HOMING, PRUEBA, FALLO };
Modo modo = APAGADO;
volatile long enc = 0;
float potf[2] = { 512, 512 };
int potCrudo[2] = { 512, 512 };
float q[3], ref[3], objetivo[3], qAnt[3];
float integ[3], dFilt[3];
int16_t uAplic[3];
bool moviendo[3], homed = false;
float offBase = 0;                                  // q_base = sgn*crudo - offBase
uint16_t dentro[3];
uint32_t tLimite[3];
// vigilancia
uint32_t tSat[3], tVent[3]; float qSat[3], qVent[3]; uint8_t reves[3];
// homing / prueba
uint8_t fase; uint32_t tFase; long encIni; float crudoIni, crudoMed;
uint8_t pj; bool pruebaCtrl;
Servo servo; bool servoOn = false;

// ---------------------------------------------- SENSORES ---------------------------------------------
void isrEncoder() {
  bool a = PIND & (1 << 2), b = PIND & (1 << 4);    // D2 y D4 (puerto D)
  enc += (a == b) ? 1 : -1;
}
long leerEnc() { noInterrupts(); long e = enc; interrupts(); return e; }

float crudo(uint8_t j) {                            // grados del sensor, sin signo ni cero
  if (j == 0) return leerEnc() * 360.0 / ENC_CUENTAS_VUELTA;
  return (potf[j - 1] - 512) * POT_GRADOS_CUENTA;
}
void leerSensores() {
  for (uint8_t k = 0; k < 2; k++) {
    analogRead(PIN_POT[k]);                         // primera lectura descartada (cambio de canal)
    potCrudo[k] = analogRead(PIN_POT[k]);
    potf[k] += 0.35 * (potCrudo[k] - potf[k]);      // filtro exponencial
  }
  q[0] = aj.sgn[0] * crudo(0) - offBase;
  for (uint8_t j = 1; j < 3; j++) q[j] = aj.sgn[j] * crudo(j) - aj.cero[j - 1];
}
bool fc1() { return digitalRead(PIN_FC1) == LOW; }
bool fc2() { return digitalRead(PIN_FC2) == LOW; }

// ---------------------------------------------- MOTORES (DRV8871) -------------------------------------
// pwm > 0: el eje gira en sentido horario (si "inv" está bien puesto)
void escribirMotor(uint8_t j, int pwm) {
  if (aj.inv[j]) pwm = -pwm;
  pwm = constrain(pwm, -255, 255);
  if (pwm == 0)     { digitalWrite(PIN_IN2[j], LOW);  analogWrite(PIN_IN1[j], 0); }
  else if (pwm > 0) { digitalWrite(PIN_IN2[j], LOW);  analogWrite(PIN_IN1[j], pwm); }
  else              { digitalWrite(PIN_IN2[j], HIGH); analogWrite(PIN_IN1[j], 255 + pwm); }
}
void motor(uint8_t j, int pwm) {                    // con límite y rampa
  pwm = constrain(pwm, -PWM_MAX[j], PWM_MAX[j]);
  if (pwm > uAplic[j] + PWM_RAMPA) pwm = uAplic[j] + PWM_RAMPA;
  if (pwm < uAplic[j] - PWM_RAMPA) pwm = uAplic[j] - PWM_RAMPA;
  uAplic[j] = pwm;
  escribirMotor(j, pwm);
}
void pararMotores() { for (uint8_t j = 0; j < 3; j++) { uAplic[j] = 0; escribirMotor(j, 0); moviendo[j] = false; } }

// ---------------------------------------------- MODOS ---------------------------------------------------
void fallo(const __FlashStringHelper *motivo) {
  pararMotores(); modo = FALLO;
  Serial.print(F("!! PARADA: ")); Serial.println(motivo);
  Serial.println(F("   Arregla la causa y escribe: on"));
}
void resetVigilancia(uint8_t j) { tSat[j] = 0; tVent[j] = millis(); qVent[j] = q[j]; reves[j] = 0; }
void activar() {
  leerSensores();
  for (uint8_t j = 0; j < 3; j++) {
    ref[j] = objetivo[j] = qAnt[j] = q[j]; integ[j] = 0; dFilt[j] = 0; moviendo[j] = false; resetVigilancia(j);
  }
  modo = ACTIVO;
  Serial.print(F("OK control activo"));
  for (uint8_t j = 0; j < 3; j++) if (!aj.probado[j]) { Serial.print(F(" (sin prueba: ")); Serial.print(NOMBRE[j]); Serial.print(F(" libre)")); }
  Serial.println();
}
bool controlado(uint8_t j) { return aj.probado[j] && (j != 0 || homed || modo == HOMING); }

// ---------------------------------------------- PID -----------------------------------------------------
float pid(uint8_t j) {
  float e = ref[j] - q[j];
  float vel = (q[j] - qAnt[j]) / DT; qAnt[j] = q[j];
  dFilt[j] += 0.3 * (-vel - dFilt[j]);              // derivada sobre la medida, filtrada
  float p = aj.kp[j] * e, d = aj.kd[j] * dFilt[j];
  float u = p + integ[j] + d;
  bool sat = fabs(u) >= PWM_MAX[j];
  if (!sat || (u > 0) != (e > 0)) integ[j] += aj.ki[j] * e * DT;   // anti-windup: integración condicional
  float imax = PWM_MAX[j] * 0.7;
  integ[j] = constrain(integ[j], -imax, imax);
  if (fabs(e) < TOL) return integ[j];               // dentro de tolerancia: solo sostener
  u = p + integ[j] + d;
  u += (u > 0 ? PWM_MIN[j] : -PWM_MIN[j]);          // compensación de zona muerta
  return u;
}

// Protecciones de cada articulación: límites y finales de carrera
float proteger(uint8_t j, float u) {
  if (j == 0) {
    if (fc1() && u > 0) u = 0;                      // FC1 está en el lado positivo
    if (fc2() && u < 0) u = 0;
    if (homed && q[0] >= LIM_BASE + 3 && u > 0) u = 0;
    if (homed && q[0] <= -LIM_BASE - 3 && u < 0) u = 0;
  } else {
    if (q[j] >= LIM_POT + 3 && u > 0) u = 0;
    if (q[j] <= -LIM_POT - 3 && u < 0) u = 0;
  }
  return u;
}

// Bloqueo (mucho PWM sin moverse) y sentido al revés (se mueve contra el motor)
void vigilar(uint8_t j) {
  uint32_t ahora = millis();
  if (abs(uAplic[j]) >= PWM_MAX[j] * 9 / 10) {
    if (!tSat[j]) { tSat[j] = ahora; qSat[j] = q[j]; }
    else if (ahora - tSat[j] > 1500) {
      if (fabs(q[j] - qSat[j]) < 1.0) { Serial.print(NOMBRE[j]); Serial.print(F(": ")); fallo(F("motor bloqueado o sin fuerza")); return; }
      tSat[j] = ahora; qSat[j] = q[j];
    }
  } else tSat[j] = 0;
  if (ahora - tVent[j] >= 300) {
    float dq = q[j] - qVent[j];
    bool contra = abs(uAplic[j]) > PWM_MAX[j] / 2 && fabs(dq) > 2.0 && ((dq > 0) != (uAplic[j] > 0));
    reves[j] = contra ? reves[j] + 1 : 0;
    if (reves[j] >= 2) { Serial.print(NOMBRE[j]); Serial.print(F(": ")); fallo(F("gira al reves del motor: repite la prueba")); return; }
    tVent[j] = ahora; qVent[j] = q[j];
  }
}

// ---------------------------------------------- MOVIMIENTOS ---------------------------------------------
void mover(uint8_t j, float delta) {
  if (modo == FALLO) { Serial.println(F("! hay un fallo: escribe on")); return; }
  if (modo == HOMING || modo == PRUEBA) { Serial.println(F("! espera a que termine")); return; }
  if (!aj.probado[j]) { Serial.print(F("! primero: prueba ")); Serial.println(NOMBRE[j]); return; }
  if (j == 0 && !homed) { Serial.println(F("! primero: home")); return; }
  if (fabs(delta) > PASO_MAX) { Serial.print(F("! como mucho ")); Serial.print(PASO_MAX, 0); Serial.println(F(" grados por orden")); return; }
  if (modo == APAGADO) activar();
  float lim = j == 0 ? LIM_BASE : LIM_POT;
  float dest = objetivo[j] + delta;
  if (dest > lim || dest < -lim) {
    Serial.print(F("! fuera de limites (")); Serial.print(-lim, 0); Serial.print(F(" a ")); Serial.print(lim, 0);
    Serial.print(F("). Ahora en ")); Serial.println(objetivo[j], 1); return;
  }
  objetivo[j] = dest; moviendo[j] = true; dentro[j] = 0;
  tLimite[j] = millis() + (uint32_t)(fabs(dest - ref[j]) / aj.vel[j] * 1000) + 5000;
  Serial.print(F("-> ")); Serial.print(NOMBRE[j]); Serial.print(F(" a ")); Serial.print(dest, 1); Serial.println(F(" grados"));
}

void trayectoria(uint8_t j) {
  if (!moviendo[j]) return;
  float paso = aj.vel[j] * DT, e = objetivo[j] - ref[j];
  ref[j] = fabs(e) <= paso ? objetivo[j] : ref[j] + (e > 0 ? paso : -paso);
  if (ref[j] == objetivo[j] && fabs(q[j] - objetivo[j]) < TOL) {
    if (++dentro[j] >= 20) {
      moviendo[j] = false;
      Serial.print(F("OK ")); Serial.print(NOMBRE[j]); Serial.print(F(" en ")); Serial.print(q[j], 1); Serial.println(F(" grados"));
    }
  } else dentro[j] = 0;
  if ((int32_t)(millis() - tLimite[j]) > 0) { Serial.print(NOMBRE[j]); Serial.print(F(": ")); fallo(F("no llega a tiempo")); }
}

// ---------------------------------------------- HOMING DE LA BASE ----------------------------------------
void iniciarHoming() {
  if (modo == FALLO) { Serial.println(F("! hay un fallo: escribe on")); return; }
  if (!aj.probado[0]) { Serial.println(F("! primero: prueba base")); return; }
  if (fc2()) { Serial.println(F("! el final de carrera 2 esta pulsado: revisa los cables")); return; }
  if (modo != ACTIVO) activar();
  homed = false; moviendo[0] = false;
  modo = HOMING; fase = 0; tFase = millis(); crudoIni = aj.sgn[0] * crudo(0);
  Serial.println(F("homing: la base gira en + hasta el final de carrera 1..."));
}
void cicloHoming() {
  for (uint8_t j = 1; j < 3; j++) if (controlado(j)) { motor(j, proteger(j, pid(j))); vigilar(j); if (modo == FALLO) return; }
  uint32_t t = millis() - tFase;
  float avance = aj.sgn[0] * crudo(0) - crudoIni;
  if (fase == 0) {                                  // buscar FC1 despacio
    if (fc2()) { fallo(F("homing: ha pisado el final de carrera 2 (FC1 y FC2 cambiados o motor al reves)")); return; }
    if (fc1()) {
      pararMotores();
      offBase = aj.sgn[0] * crudo(0) - aj.ang_fc1;   // aquí la base está en ang_fc1
      homed = true; fase = 1; tFase = millis();
      Serial.println(F("homing: final de carrera 1 encontrado"));
      return;
    }
    if (avance < -3) { fallo(F("homing: la base gira en negativo (repite la prueba base)")); return; }
    if (t > 1500 && avance < 0.5) { fallo(F("homing: la base no se mueve")); return; }
    if (t > 20000) { fallo(F("homing: no encuentra el final de carrera 1 en 20 s")); return; }
    motor(0, PWM_HOMING);
  } else {                                          // ir a 0 con control
    leerSensores();
    for (uint8_t j = 0; j < 3; j++) { ref[j] = objetivo[j] = q[j]; integ[j] = 0; resetVigilancia(j); }
    modo = ACTIVO;
    objetivo[0] = 0; moviendo[0] = true; dentro[0] = 0;
    tLimite[0] = millis() + (uint32_t)(fabs(q[0]) / aj.vel[0] * 1000) + 5000;
    Serial.println(F("homing: volviendo a 0"));
  }
}

// ---------------------------------------------- PRUEBA DE SENTIDO ----------------------------------------
void iniciarPrueba(uint8_t j) {
  if (modo == HOMING || modo == PRUEBA) { Serial.println(F("! espera a que termine")); return; }
  if (modo == FALLO) modo = APAGADO;
  pruebaCtrl = modo == ACTIVO;                     // si había control, el resto de articulaciones se sostiene
  for (uint8_t k = 0; k < 3; k++) moviendo[k] = false;
  pj = j; fase = 0; tFase = millis(); crudoIni = crudo(j);
  if (j == 0) homed = false;
  modo = PRUEBA; uAplic[j] = 0;
  Serial.print(F("prueba ")); Serial.print(NOMBRE[j]);
  Serial.println(F(": giro POSITIVO y vuelta. Mira el eje del motor en el primer giro"));
}
void cicloPrueba() {
  for (uint8_t j = 0; j < 3; j++) if (pruebaCtrl && j != pj && controlado(j)) motor(j, proteger(j, pid(j)));
  else if (j != pj) { uAplic[j] = 0; escribirMotor(j, 0); }
  uint32_t t = millis() - tFase;
  int pw = fase == 0 ? PWM_PRUEBA[pj] : (fase == 2 ? -PWM_PRUEBA[pj] : 0);
  if (pj == 0 && ((fc1() && pw > 0) || (fc2() && pw < 0))) pw = 0;   // no empujar contra un final de carrera
  if (pj > 0 && ((q[pj] >= LIM_POT + 3 && pw * aj.sgn[pj] > 0) || (q[pj] <= -LIM_POT - 3 && pw * aj.sgn[pj] < 0)) && aj.probado[pj]) pw = 0;
  if (fase < 3) { escribirMotor(pj, pw); uAplic[pj] = pw; }
  if (fase == 0) { if (t > 400) { fase = 1; tFase = millis(); } }
  else if (fase == 1) { if (t > 300) { crudoMed = crudo(pj); fase = 2; tFase = millis(); } }
  else if (fase == 2) { if (t > 400) { fase = 3; tFase = millis(); } }
  else {
    escribirMotor(pj, 0); uAplic[pj] = 0;
    if (t < 300) return;
    float mas = crudoMed - crudoIni, menos = crudo(pj) - crudoMed;
    float dif = mas - menos;                        // así la gravedad no engaña
    Serial.print(F("prueba ")); Serial.print(NOMBRE[pj]); Serial.print(F(": sensor ")); Serial.print(mas, 1);
    Serial.print(F(" / ")); Serial.print(menos, 1); Serial.println(F(" grados"));
    if (fabs(dif) < 1.0) {
      Serial.println(F("! casi no se mueve: revisa motor, controlador, 12 V y sensor"));
    } else {
      int8_t s = dif > 0 ? 1 : -1;
      if (pj > 0) aj.cero[pj - 1] = aj.cero[pj - 1] * s * aj.sgn[pj];   // mantener la misma posición física como 0
      aj.sgn[pj] = s; aj.probado[pj] = 1;
      Serial.print(F("OK sensor ajustado. Si el eje giro ANTIHORARIO en el primer giro, escribe: invertir "));
      Serial.println(NOMBRE[pj]);
    }
    modo = APAGADO;
    if (pruebaCtrl) activar();
  }
}

// ---------------------------------------------- ESTADO ---------------------------------------------------
void imprimirEstado() {
  const char *m[] = { "apagado", "activo", "homing", "prueba", "FALLO" };
  Serial.print(F("modo ")); Serial.print(m[modo]); Serial.print(F(" | home ")); Serial.println(homed ? F("si") : F("no"));
  for (uint8_t j = 0; j < 3; j++) {
    Serial.print(F("  ")); Serial.print(NOMBRE[j]); Serial.print(F(": ")); Serial.print(q[j], 1);
    Serial.print(F(" grados, objetivo ")); Serial.print(objetivo[j], 1); Serial.print(F(", pwm ")); Serial.print(uAplic[j]);
    Serial.print(F(", vel ")); Serial.print(aj.vel[j], 0); Serial.print(F(" g/s"));
    Serial.println(aj.probado[j] ? F("") : F("  (falta prueba)"));
  }
  Serial.print(F("  sensores: enc ")); Serial.print(leerEnc()); Serial.print(F(", pot hombro ")); Serial.print(potCrudo[0]);
  Serial.print(F(", pot codo ")); Serial.print(potCrudo[1]); Serial.print(F(", FC1 ")); Serial.print(fc1());
  Serial.print(F(", FC2 ")); Serial.println(fc2());
}
void ayuda() {
  Serial.println(F("Ordenes (+ = eje del motor en sentido horario):"));
  Serial.println(F("  base N | hombro N | codo N   girar N grados (max 45 por orden)"));
  Serial.println(F("  x                            PARAR todo (motores sueltos)"));
  Serial.println(F("  on | off                     activar / soltar los motores"));
  Serial.println(F("  home                         homing de la base"));
  Serial.println(F("  prueba J | invertir J        comprobar y corregir el sentido (J = base, hombro, codo)"));
  Serial.println(F("  cero J                       la postura actual de hombro o codo pasa a ser 0"));
  Serial.println(F("  fc1 N                        angulo de la base en el final de carrera 1"));
  Serial.println(F("  vel J N                      velocidad en grados/s (max 20)"));
  Serial.println(F("  pid | pid J kp ki kd         ver / cambiar ganancias"));
  Serial.println(F("  pinza N                      servo de la pinza a N grados (0-180)"));
  Serial.println(F("  estado | guardar | defecto"));
}

// ---------------------------------------------- ÓRDENES --------------------------------------------------
int articulacion(const char *s) {
  for (uint8_t j = 0; j < 3; j++) if (!strcmp(s, NOMBRE[j])) return j;
  return -1;
}
void orden(char *l) {
  for (char *p = l; *p; p++) *p = tolower(*p);
  char *a = strtok(l, " \t"), *b = strtok(NULL, " \t"), *c = strtok(NULL, " \t"), *d = strtok(NULL, " \t"), *e = strtok(NULL, " \t");
  if (!a) return;
  int j = articulacion(a);
  if (!strcmp(a, "x") || !strcmp(a, "parar") || !strcmp(a, "stop")) { pararMotores(); modo = APAGADO; Serial.println(F("OK PARADO")); return; }
  if (j >= 0) { if (!b) { Serial.println(F("! falta el angulo, p. ej.: base 20")); return; } mover(j, atof(b)); return; }
  if (!strcmp(a, "estado") || !strcmp(a, "e")) { imprimirEstado(); return; }
  if (!strcmp(a, "ayuda") || !strcmp(a, "?")) { ayuda(); return; }
  if (!strcmp(a, "on")) { activar(); return; }
  if (!strcmp(a, "off")) { pararMotores(); modo = APAGADO; Serial.println(F("OK motores sueltos")); return; }
  if (!strcmp(a, "home")) { iniciarHoming(); return; }
  if (!strcmp(a, "guardar")) { EEPROM.put(0, aj); Serial.println(F("OK guardado")); return; }
  if (!strcmp(a, "defecto")) { pararMotores(); modo = APAGADO; homed = false; ajustesPorDefecto(); Serial.println(F("OK ajustes por defecto (sin guardar)")); return; }
  if (!strcmp(a, "pinza")) {
    if (!b) return;
    if (!servoOn) { servo.attach(PIN_SERVO); servoOn = true; }
    servo.write(constrain(atoi(b), 0, 180)); Serial.println(F("OK pinza")); return;
  }
  if (!strcmp(a, "fc1")) { if (!b) return; aj.ang_fc1 = atof(b); homed = false; Serial.println(F("OK (repite home)")); return; }
  if (!strcmp(a, "pid")) {
    if (b && e) {
      int k = articulacion(b); if (k < 0) { Serial.println(F("! articulacion?")); return; }
      aj.kp[k] = atof(c); aj.ki[k] = atof(d); aj.kd[k] = atof(e); integ[k] = 0;
    }
    for (uint8_t k = 0; k < 3; k++) {
      Serial.print(F("  ")); Serial.print(NOMBRE[k]); Serial.print(F(" kp ")); Serial.print(aj.kp[k], 2);
      Serial.print(F(" ki ")); Serial.print(aj.ki[k], 2); Serial.print(F(" kd ")); Serial.println(aj.kd[k], 3);
    }
    return;
  }
  int k = b ? articulacion(b) : -1;
  if (k < 0) { Serial.println(F("! orden no valida. Escribe: ayuda")); return; }
  if (!strcmp(a, "prueba")) { iniciarPrueba(k); return; }
  if (!strcmp(a, "invertir")) {
    pararMotores(); modo = APAGADO;
    aj.inv[k] = !aj.inv[k]; aj.sgn[k] = -aj.sgn[k];  // el sensor sigue al motor
    if (k > 0) aj.cero[k - 1] = -aj.cero[k - 1];
    if (k == 0) homed = false;
    Serial.print(F("OK ")); Serial.print(NOMBRE[k]); Serial.println(F(" invertido. Repite la prueba para comprobarlo"));
    return;
  }
  if (!strcmp(a, "cero")) {
    if (k == 0) { Serial.println(F("! la base se pone a 0 con home")); return; }
    leerSensores(); aj.cero[k - 1] += q[k];
    leerSensores(); ref[k] = objetivo[k] = q[k]; integ[k] = 0; moviendo[k] = false;
    Serial.print(F("OK ")); Serial.print(NOMBRE[k]); Serial.println(F(" = 0 aqui"));
    return;
  }
  if (!strcmp(a, "vel")) {
    if (!c) return;
    aj.vel[k] = constrain(atof(c), 1, VEL_TOPE);
    Serial.print(F("OK vel ")); Serial.print(NOMBRE[k]); Serial.print(' '); Serial.println(aj.vel[k], 0); return;
  }
  Serial.println(F("! orden no valida. Escribe: ayuda"));
}

void leerSerie() {
  static char buf[48]; static uint8_t n = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') { if (n) { buf[n] = 0; orden(buf); n = 0; } }
    else if (n < sizeof(buf) - 1) buf[n++] = ch;
  }
}

// ---------------------------------------------- BUCLE DE CONTROL -----------------------------------------
void ciclo() {
  leerSensores();
  if (modo == ACTIVO || modo == HOMING) {
    for (uint8_t k = 0; k < 2; k++)
      if (aj.probado[k + 1] && (potCrudo[k] < POT_MIN_OK || potCrudo[k] > POT_MAX_OK)) {
        fallo(k == 0 ? F("potenciometro del hombro sin senal") : F("potenciometro del codo sin senal")); return;
      }
  }
  switch (modo) {
    case ACTIVO:
      for (uint8_t j = 0; j < 3; j++) {
        if (!controlado(j)) { uAplic[j] = 0; escribirMotor(j, 0); continue; }
        trayectoria(j); if (modo != ACTIVO) return;
        motor(j, proteger(j, pid(j)));
        vigilar(j); if (modo != ACTIVO) return;
      }
      break;
    case HOMING: cicloHoming(); break;
    case PRUEBA: cicloPrueba(); break;
    default: break;
  }
}

void setup() {
  wdt_disable();
  for (uint8_t j = 0; j < 3; j++) {                 // motores parados antes que nada
    digitalWrite(PIN_IN1[j], LOW); digitalWrite(PIN_IN2[j], LOW);
    pinMode(PIN_IN1[j], OUTPUT); pinMode(PIN_IN2[j], OUTPUT);
  }
  pinMode(PIN_ENC_A, INPUT_PULLUP); pinMode(PIN_ENC_B, INPUT_PULLUP);
  pinMode(PIN_FC1, INPUT_PULLUP); pinMode(PIN_FC2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), isrEncoder, CHANGE);
  Serial.begin(115200);
  EEPROM.get(0, aj);
  bool ok = aj.magia == MAGIA;
  if (!ok) ajustesPorDefecto();
  for (uint8_t i = 0; i < 30; i++) { leerSensores(); delay(2); }
  Serial.println(F("\nBrazo: prueba por ordenes. Motores sueltos. Escribe: ayuda"));
  Serial.println(ok ? F("Ajustes cargados de la EEPROM") : F("EEPROM vacia: empieza por prueba base, prueba hombro, prueba codo"));
  wdt_enable(WDTO_250MS);                           // si el programa se cuelga, se reinicia con los motores parados
}

void loop() {
  static uint32_t t = micros();
  wdt_reset();
  if (micros() - t >= 10000) { t += 10000; if (micros() - t > 50000) t = micros(); ciclo(); }
  leerSerie();
}
