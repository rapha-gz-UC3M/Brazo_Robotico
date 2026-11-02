// tareas.h - Coger, dejar y apilar cubos. Máquina de estados no bloqueante (el control sigue a 100 Hz).
//
//  Para cada cubo:  abrir pinza -> encima del cubo -> bajar en línea recta -> cerrar -> subir
//                   -> encima de la pila -> bajar hasta su nivel -> abrir -> subir
//  Al terminar vuelve a la posición de reposo. Las alturas dependen del lado del cubo (CUBO).
#pragma once
#include <Arduino.h>

namespace Tareas {
  void coger(float x, float y);                     // un cubo apoyado en la mesa en (x, y)
  void dejar(float x, float y, uint8_t nivel);      // sobre la pila en (x, y): nivel 0 = en la mesa
  // n cubos en (xs[i], ys[i]); la pila se forma en (xp, yp) empezando en el nivel 'nivel0'
  void apilar(uint8_t n, const float xs[], const float ys[], float xp, float yp, uint8_t nivel0 = 0);
  void actualizar();                                // llamar en cada vuelta del loop
  void cancelar();
  bool ocupada();
}
