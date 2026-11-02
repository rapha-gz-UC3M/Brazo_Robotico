#include "tareas.h"
#include "config.h"
#include "robot.h"
#include "pinza.h"
#include "cinematica.h"

namespace Tareas {

enum Paso : uint8_t {
  LIBRE,
  // coger
  C_ABRIR, C_ENCIMA, C_BAJAR, C_CERRAR, C_SUBIR,
  // dejar
  D_ENCIMA, D_BAJAR, D_SOLTAR, D_SUBIR,
  REPOSO, FIN
};

static Paso paso = LIBRE;
static bool esperando = false;          // esperando a que termine el movimiento / la pinza
static uint32_t t_espera = 0;
static uint8_t n_cubos = 0, i_cubo = 0, nivel_base = 0;
static float cx[MAX_CUBOS], cy[MAX_CUBOS], px, py;
static bool solo_coger = false, solo_dejar = false;

static float lado() { return Robot::aj.cubo_mm; }
static float z_agarre(uint8_t nivel) { return lado() * (nivel + 0.5f) + Z_AGARRE_MM; }
static float z_segura(uint8_t nivel) { return lado() * (nivel + 1) + ALTURA_SEGURA_MM; }

static void error(const __FlashStringHelper *m) {
  Serial.print(F("! tarea cancelada: ")); Serial.println(m);
  Robot::parar_movimiento();
  paso = LIBRE; esperando = false;
}

// recta = true: línea recta (para bajar y subir en vertical); false: interpolación articular (traslados)
static bool ir(float x, float y, float z, bool recta) {
  Punto p = { x, y, z };
  bool ok;
  if (recta) ok = Robot::mover_cartesiano(p);
  else { float q[3]; ok = Cinematica::inversa(p, q) && Robot::mover_articular(q); }
  if (!ok) { error(F("punto inalcanzable")); return false; }
  esperando = true; return true;
}


static void empezar(Paso p) {
  if (Robot::modo() != Robot::CONTROL) { Serial.println(F("! control inactivo (HOME)")); return; }
  if (!Robot::base_referenciada()) { Serial.println(F("! haz HOME antes")); return; }
  paso = p; esperando = false;
}

void coger(float x, float y) {
  cx[0] = x; cy[0] = y; n_cubos = 1; i_cubo = 0; solo_coger = true; solo_dejar = false;
  empezar(C_ABRIR);
}

void dejar(float x, float y, uint8_t nivel) {
  px = x; py = y; nivel_base = nivel; n_cubos = 1; i_cubo = 0; solo_dejar = true; solo_coger = false;
  empezar(D_ENCIMA);
}

void apilar(uint8_t n, const float xs[], const float ys[], float xp, float yp, uint8_t nivel0) {
  n_cubos = min(n, MAX_CUBOS);
  for (uint8_t i = 0; i < n_cubos; i++) { cx[i] = xs[i]; cy[i] = ys[i]; }
  px = xp; py = yp; nivel_base = nivel0; i_cubo = 0; solo_coger = solo_dejar = false;
  Serial.print(F("apilar: ")); Serial.print(n_cubos); Serial.println(F(" cubos"));
  empezar(C_ABRIR);
}

void cancelar() { if (paso != LIBRE) { Robot::parar_movimiento(); paso = LIBRE; esperando = false; Serial.println(F("OK tarea cancelada")); } }
bool ocupada() { return paso != LIBRE; }

void actualizar() {
  if (paso == LIBRE) return;
  if (Robot::modo() != Robot::CONTROL) { error(F("el control se ha detenido")); return; }

  // esperar a que termine lo que se ha mandado
  if (esperando) {
    if (paso == C_ABRIR || paso == C_CERRAR || paso == D_SOLTAR) {
      if (!Pinza::quieta() || millis() - t_espera < 300) return;     // + 0,3 s para que asiente
    } else {
      if (Robot::moviendo()) return;
      if (Robot::fallo_llegada()) { error(F("el brazo no llega")); return; }
    }
    esperando = false;
    switch (paso) {                                   // paso terminado -> el siguiente
      case C_ABRIR:  paso = C_ENCIMA; break;
      case C_ENCIMA: paso = C_BAJAR; break;
      case C_BAJAR:  paso = C_CERRAR; break;
      case C_CERRAR: paso = C_SUBIR; break;
      case C_SUBIR:  paso = solo_coger ? FIN : D_ENCIMA; break;
      case D_ENCIMA: paso = D_BAJAR; break;
      case D_BAJAR:  paso = D_SOLTAR; break;
      case D_SOLTAR: paso = D_SUBIR; break;
      case D_SUBIR:
        Serial.print(F("OK cubo ")); Serial.print(i_cubo + 1); Serial.println(F(" colocado"));
        i_cubo++;
        paso = (solo_dejar || i_cubo >= n_cubos) ? REPOSO : C_ABRIR; break;
      case REPOSO:   paso = FIN; break;
      default: break;
    }
    return;
  }

  uint8_t nivel = nivel_base + i_cubo;
  // la altura segura tiene en cuenta la pila ya hecha
  float zs = max(z_segura(0), z_segura(nivel));
  switch (paso) {
    case C_ABRIR:
      Serial.print(F("cubo ")); Serial.print(i_cubo + 1); Serial.println(F(": coger"));
      Pinza::apertura(min(lado() + 30.0f, 85.0f)); t_espera = millis(); esperando = true; break;
    case C_ENCIMA: ir(cx[i_cubo], cy[i_cubo], zs, false); break;
    case C_BAJAR:  ir(cx[i_cubo], cy[i_cubo], z_agarre(0), true); break;
    case C_CERRAR: Pinza::agarrar(lado()); t_espera = millis(); esperando = true; break;
    case C_SUBIR:  ir(cx[i_cubo], cy[i_cubo], zs, true); break;
    case D_ENCIMA: ir(px, py, zs, false); break;
    case D_BAJAR:  ir(px, py, z_agarre(nivel) + 2.0f, true); break; // 2 mm de holgura al soltar
    case D_SOLTAR: Pinza::apertura(min(lado() + 20.0f, 85.0f)); t_espera = millis(); esperando = true; break;
    case D_SUBIR:  ir(px, py, zs, true); break;
    case REPOSO: {
      if (!Robot::mover_articular(POSE_REPOSO)) { error(F("no puede ir al reposo")); return; }
      esperando = true; break;
    }
    case FIN:
      Serial.println(F("OK tarea terminada"));
      paso = LIBRE; break;
    default: paso = LIBRE; break;
  }
}

} // namespace Tareas
