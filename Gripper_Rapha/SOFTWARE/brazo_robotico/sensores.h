// sensores.h - Encoder de la base (interrupción), potenciómetros del hombro y del codo, finales de carrera.
#pragma once
#include <Arduino.h>

namespace Encoder {
  void begin();
  long cuentas();                 // lectura atómica del contador
  void fijar(long c);             // pone el contador a un valor (homing)
  extern int8_t signo;            // +1 / -1: sentido de cuenta (se invierte con INV E)
}

// Potenciómetro con filtro EMA y calibración lineal de dos puntos: ángulo = (adc - adc0) * k
struct Potenciometro {
  uint8_t pin;
  float adc0;          // ADC que corresponde a 0°
  float k;             // grados por cuenta (con signo)
  float filtrado = -1; // ADC filtrado
  int16_t crudo = 0;   // última lectura sin filtrar
  void begin(uint8_t p, float a0, float kk) { pin = p; adc0 = a0; k = kk; }
  void leer();                       // 4 muestras + EMA
  float grados() const { return (filtrado - adc0) * k; }
  bool ok() const;                   // falso si el cursor está en un extremo (cable suelto)
};

namespace FinalesCarrera {
  void begin();
  bool fc1();     // true = pulsado
  bool fc2();
}
