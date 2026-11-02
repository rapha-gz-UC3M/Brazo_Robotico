#include "sensores.h"
#include "config.h"

// ---------------------------------------------- ENCODER ---------------------------------------------
// Se interrumpe en los dos flancos del canal A (CHANGE) y se mira B: si A == B gira en un sentido, si no
// en el otro. La rutina es muy corta (solo suma o resta), como piden las buenas prácticas de ISR.
namespace Encoder {
  volatile long contador = 0;
  int8_t signo = 1;
  static volatile uint8_t *reg_a, *reg_b;
  static uint8_t mask_a, mask_b;

  static void isr() {
    bool a = (*reg_a & mask_a) != 0;
    bool b = (*reg_b & mask_b) != 0;
    contador += (a == b) ? 1 : -1;
  }
  void begin() {
    pinMode(PIN_ENC_A, INPUT_PULLUP); pinMode(PIN_ENC_B, INPUT_PULLUP);
    reg_a = portInputRegister(digitalPinToPort(PIN_ENC_A)); mask_a = digitalPinToBitMask(PIN_ENC_A);
    reg_b = portInputRegister(digitalPinToPort(PIN_ENC_B)); mask_b = digitalPinToBitMask(PIN_ENC_B);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), isr, CHANGE);
  }
  long cuentas() {
    noInterrupts(); long c = contador; interrupts();
    return c * signo;
  }
  void fijar(long c) {
    noInterrupts(); contador = c * signo; interrupts();
  }
}

// ---------------------------------------------- POTENCIÓMETROS --------------------------------------
void Potenciometro::leer() {
  analogRead(pin);                              // la 1ª lectura tras cambiar de canal se descarta
  long s = 0;
  for (uint8_t i = 0; i < 4; i++) s += analogRead(pin);
  crudo = (int16_t)(s / 4);
  if (filtrado < 0) filtrado = crudo;
  else filtrado += FILTRO_POT_ALFA * (crudo - filtrado);
}
bool Potenciometro::ok() const { return crudo >= POT_ADC_MIN_OK && crudo <= POT_ADC_MAX_OK; }

// ---------------------------------------------- FINALES DE CARRERA ----------------------------------
namespace FinalesCarrera {
  void begin() { pinMode(PIN_FC1, INPUT_PULLUP); pinMode(PIN_FC2, INPUT_PULLUP); }
  bool fc1() { return digitalRead(PIN_FC1) == LOW; }
  bool fc2() { return digitalRead(PIN_FC2) == LOW; }
}
