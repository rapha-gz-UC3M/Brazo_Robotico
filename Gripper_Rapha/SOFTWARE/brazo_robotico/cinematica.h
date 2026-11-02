// cinematica.h - Cinemática directa e inversa del brazo de 3 GDL (base + hombro + codo).
//
//  Marco de la tarea (mm): origen en el eje de la base, sobre la mesa. X hacia delante (q0 = 0),
//  Y a la izquierda, Z hacia arriba. TCP = centro de las mordazas, alineado con el antebrazo.
//
//    r = L1·sin(q1) + L2·sin(q1+q2)          (distancia horizontal al eje de la base)
//    z = H + L1·cos(q1) + L2·cos(q1+q2)      (altura sobre la mesa)
//    x = r·cos(q0),  y = r·sin(q0)
//
//  La muñeca es fija: la orientación de la pinza la deciden q1 y q2. La inversa tiene una sola solución
//  útil (codo hacia delante, q2 > 0), que es la configuración del montaje.
#pragma once

struct Punto { float x, y, z; };

namespace Cinematica {
  Punto directa(const float q[3]);
  // true si hay solución dentro de los límites; q en grados
  bool inversa(const Punto &p, float q[3]);
}
