// pinza.h - Gripper con servo MG90S. Se manda por apertura entre mordazas (mm) y el servo se mueve suave.
#pragma once
#include <Arduino.h>

namespace Pinza {
  void begin(int16_t servo_cerrado, int8_t sentido);
  void apertura(float mm);          // consigna de apertura entre mordazas (2,3 .. 92 mm)
  void abrir();                     // abre del todo (o lo justo para el cubo + margen)
  void agarrar(float cubo_mm);      // cierra hasta cubo - apriete
  void actualizar(float dt);        // mueve el servo hacia la consigna a velocidad limitada
  bool quieta();                    // ha llegado a la consigna
  float apertura_actual();
  float giro_desde_apertura(float mm);
  extern int16_t servo_cerrado;     // [CAL]
  extern int8_t sentido;            // [CAL]
}
