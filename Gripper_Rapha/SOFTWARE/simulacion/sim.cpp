// Simulador en el PC: ejecuta el firmware real (brazo_robotico/*.cpp) contra un modelo de los motores,
// los sensores y la gravedad, y le manda comandos por un "puerto serie" desde un guion.
//
//   g++ -O2 -std=c++17 -Imock -I../brazo_robotico sim.cpp ../brazo_robotico/*.cpp -o sim
//   ./sim guion.txt [estado.csv]
//
// Guion: una línea por comando, "segundos comando" (p. ej. "1.0 HOME"). "#" = comentario. "35 FIN" = acaba.
// SIM_CABLEADO="1,-1,1": simula motores conectados al revés (para probar SENTIDO).
#include "Arduino.h"
#include "EEPROM.h"
#include "Servo.h"
#include "../brazo_robotico/config.h"
#include <vector>
#include <deque>
#include <fstream>
#include <sstream>
#include <iostream>
#include <random>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>
#include <chrono>
#include <thread>

// --------------------------------------------------------------------- reloj y E/S simuladas
static uint64_t sim_us = 0;
uint32_t millis() { return (uint32_t)(sim_us / 1000); }
uint32_t micros() { return (uint32_t)sim_us; }
uint8_t sim_puertos[4] = { 0, 0, 0, 0 };
SimEEPROM EEPROM;
int sim_servo = 90;
SimSerial Serial;
static std::deque<char> entrada;
static std::string linea_salida;
int SimSerial::available() { return (int)entrada.size(); }
int SimSerial::read() { if (entrada.empty()) return -1; char c = entrada.front(); entrada.pop_front(); return c; }
static int pty_fd = -1;          // modo --pty: el firmware habla por un puerto serie virtual
void SimSerial::out(const char *s) {
  if (pty_fd >= 0) { ssize_t r = write(pty_fd, s, strlen(s)); (void)r; return; }
  for (; *s; s++) {
    if (*s == '\n') {
      if (linea_salida.rfind("L,", 0) != 0 && linea_salida.rfind("CSV", 0) != 0)
        printf("[%7.2f] %s\n", sim_us * 1e-6, linea_salida.c_str());
      else { static FILE *lg = fopen("registro_sim.csv", "w"); fprintf(lg, "%s\n", linea_salida.c_str()); fflush(lg); }
      linea_salida.clear();
    } else linea_salida += *s;
  }
}

static uint8_t dig[20], modo_pin[20];
static int pwm_pin[20];
static void (*isr_a)() = nullptr;
void pinMode(uint8_t p, uint8_t m) { modo_pin[p] = m; }
void digitalWrite(uint8_t p, uint8_t v) { dig[p] = v; }
void analogWrite(uint8_t p, int v) { pwm_pin[p] = v; }
void attachInterrupt(uint8_t, void (*f)(), int) { isr_a = f; }

// --------------------------------------------------------------------- modelo del brazo
struct Junta { float q, w; float w0, tau, fric, qmin, qmax; int8_t cableado; };
static Junta J[3] = {
  //  q     w   w0(°/s) tau   rozam. tope-  tope+  cableado (+1 normal, -1 motor al revés)
  { 20.0f, 0, 270.0f, 0.04f, 0.12f, -85.0f, 85.0f,  1 },     // base: arranca a 20° (el encoder no lo sabe)
  { 10.0f, 0,  90.0f, 0.06f, 0.14f, -95.0f, 85.0f,  1 },     // hombro (ya con los engranajes 3:1)
  { 95.0f, 0,  90.0f, 0.06f, 0.14f,   5.0f, 165.0f, 1 },     // codo
};
static const float PAR_BLOQUEO = 10.8f * 3.0f;   // kg·cm en la articulación (45 RPM, 3:1)
static long enc_n = 0;                           // cuentas "reales" del encoder
static std::mt19937 rng(1);

static float u_motor(int j) {
  const uint8_t *p = j == 0 ? PIN_M_BASE : (j == 1 ? PIN_M_HOMBRO : PIN_M_CODO);
  float d = pwm_pin[p[0]] / 255.0f;
#if MODO_DRIVER == MODO_EN_IN1_IN2
  if (dig[p[1]] && !dig[p[2]]) return d;
  if (!dig[p[1]] && dig[p[2]]) return -d;
  return 0;
#else
  return dig[p[1]] ? d : -d;
#endif
}

static void paso_planta(float dt) {
  const float R = PI / 180;
  float g[3] = { 0,
    (6.0f * sinf(J[1].q * R) + 8.0f * sinf((J[1].q + J[2].q) * R)) / PAR_BLOQUEO,
    (6.0f * sinf((J[1].q + J[2].q) * R)) / PAR_BLOQUEO };
  for (int j = 0; j < 3; j++) {
    Junta &a = J[j];
    float drive = u_motor(j) * a.cableado + g[j];
    float ef;
    if (fabsf(drive) <= a.fric) ef = 0; else ef = drive - copysignf(a.fric, drive);
    a.w += (a.w0 * ef - a.w) * dt / a.tau;
    a.q += a.w * dt;
    if (a.q < a.qmin) { a.q = a.qmin; a.w = 0; }
    if (a.q > a.qmax) { a.q = a.qmax; a.w = 0; }
  }
  // encoder de la base: un flanco del canal A por cuenta; B indica el sentido
  long n = lroundf((J[0].q - 20.0f) / ENC_GRADOS_CUENTA);
  while (enc_n != n) {
    bool sube = n > enc_n; enc_n += sube ? 1 : -1;
    uint8_t a = (enc_n & 1) ? 1 : 0, b = sube ? a : !a;
    sim_puertos[0] = (sim_puertos[0] & ~((1 << 2) | (1 << 4))) | (a << 2) | (b << 4);
    if (isr_a) isr_a();
  }
}

int digitalRead(uint8_t p) {
  if (p == PIN_FC1) return J[0].q <= -80.0f ? LOW : HIGH;
  if (p == PIN_FC2) return J[0].q >= 80.0f ? LOW : HIGH;
  return dig[p];
}
int analogRead(uint8_t p) {
  std::uniform_int_distribution<int> ruido(-1, 1);
  float k = 300.0f / 1023.0f;
  float adc = p == PIN_POT_HOMBRO ? 512 + J[1].q / k : 512 + (J[2].q - 100.0f) / k;
  return constrain((int)lroundf(adc) + ruido(rng), 0, 1023);
}

// --------------------------------------------------------------------- firmware
#include "../brazo_robotico/brazo_robotico.ino"
#include "../brazo_robotico/cinematica.h"

// ./sim --pty : crea un puerto serie virtual (/dev/pts/N) y corre en tiempo real, para probar las
// herramientas del PC (brazo_gui.py, registrar_pid.py) sin el robot.
static int modo_pty() {
  pty_fd = posix_openpt(O_RDWR | O_NOCTTY);
  grantpt(pty_fd); unlockpt(pty_fd);
  termios t; tcgetattr(pty_fd, &t); cfmakeraw(&t); tcsetattr(pty_fd, TCSANOW, &t);
  fcntl(pty_fd, F_SETFL, O_NONBLOCK);
  fprintf(stderr, "puerto serie simulado: %s\n", ptsname(pty_fd));
  { int s = open(ptsname(pty_fd), O_RDWR | O_NOCTTY); termios t2; tcgetattr(s, &t2); cfmakeraw(&t2); tcsetattr(s, TCSANOW, &t2); close(s); }
  setup();
  auto t0 = std::chrono::steady_clock::now();
  for (;;) {
    char b[64]; ssize_t n = read(pty_fd, b, sizeof b);
    for (ssize_t i = 0; i < n; i++) entrada.push_back(b[i]);
    for (int k = 0; k < 10; k++) { loop(); for (int i = 0; i < 2; i++) { sim_us += 50; paso_planta(50e-6f); } }
    auto real = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - t0).count();
    if ((long long)sim_us > real) std::this_thread::sleep_for(std::chrono::microseconds(sim_us - real));
  }
}

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "uso: sim guion.txt [estado.csv]  |  sim --pty\n"); return 1; }
  if (const char *c = getenv("SIM_CABLEADO")) sscanf(c, "%hhd,%hhd,%hhd", &J[0].cableado, &J[1].cableado, &J[2].cableado);
  if (std::string(argv[1]) == "--pty") return modo_pty();
  std::vector<std::pair<double, std::string>> guion;
  std::ifstream f(argv[1]); std::string l;
  double fin = 0;
  while (std::getline(f, l)) {
    if (l.empty() || l[0] == '#') continue;
    std::istringstream ss(l); double t; ss >> t; std::string resto; std::getline(ss, resto);
    resto.erase(0, resto.find_first_not_of(' '));
    if (resto == "FIN") { fin = t; continue; }
    guion.push_back({ t, resto });
  }
  std::ofstream csv(argc > 2 ? argv[2] : "estado.csv");
  csv << "t,q0,q1,q2,x,y,z,servo\n";
  setup();
  size_t k = 0;
  uint64_t t_csv = 0;
  while (sim_us * 1e-6 < fin) {
    while (k < guion.size() && guion[k].first <= sim_us * 1e-6) {
      printf("[%7.2f] >> %s\n", sim_us * 1e-6, guion[k].second.c_str());
      for (char c : guion[k].second) entrada.push_back(c);
      entrada.push_back('\n'); k++;
    }
    loop();
    for (int i = 0; i < 2; i++) { sim_us += 50; paso_planta(50e-6f); }
    if (sim_us - t_csv >= 20000) {
      t_csv = sim_us;
      float q[3] = { J[0].q, J[1].q, J[2].q };
      Punto p = Cinematica::directa(q);
      csv << sim_us * 1e-6 << ',' << q[0] << ',' << q[1] << ',' << q[2] << ',' << p.x << ',' << p.y << ',' << p.z << ',' << sim_servo << '\n';
    }
  }
  return 0;
}
