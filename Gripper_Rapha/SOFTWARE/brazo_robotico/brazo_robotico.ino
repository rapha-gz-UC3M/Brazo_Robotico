// =====================================================================================================
//  Brazo robótico de 3 GDL + pinza  -  Robot's Control Architectures (UC3M)
//
//  Placa: Arduino UNO.  Motores: 3 x JGB37-520B (12 V, 45 RPM, encoder Hall) con controladores de puente H.
//  Sensores: encoder en la base + 2 finales de carrera (homing); potenciómetros absolutos en hombro y codo.
//  Pinza: servo MG90S alimentado por un convertidor buck de 5 V (no desde el Arduino).
//
//  Estructura:
//    config.h        pines, driver, límites, ganancias de partida      motor.*      puente H (PWM con signo)
//    sensores.*      encoder (ISR), potenciómetros (filtro), finales   pid.*        PID con anti-windup
//    cinematica.*    directa e inversa                                 pinza.*      servo por apertura en mm
//    robot.*         control a 100 Hz, trayectorias, homing, seguridad, pruebas de ajuste y registro CSV
//    tareas.*        coger / dejar / apilar cubos                      comandos.*   interfaz serie
//
//  Bucle: sin delay(). El control corre cada 10 ms con micros(); el resto (serie, tareas) entre medias.
//  Perro guardián de 250 ms: si el programa se cuelga, el Arduino se reinicia y los motores se paran.
// =====================================================================================================
#include <avr/wdt.h>
#include "config.h"
#include "robot.h"
#include "tareas.h"
#include "comandos.h"

static uint32_t t_control = 0;

void setup() {
  wdt_disable();
  Serial.begin(BAUDIOS);
  Robot::begin();                 // motores a 0 antes que nada
  Serial.println(F("\nBrazo robotico listo. Motores apagados. HOME para referenciar y activar. AYUDA para comandos."));
  wdt_enable(WDTO_250MS);
  t_control = micros();
}

void loop() {
  wdt_reset();
  uint32_t ahora = micros();
  if (ahora - t_control >= PERIODO_CONTROL_US) {
    t_control += PERIODO_CONTROL_US;
    if (ahora - t_control > 5UL * PERIODO_CONTROL_US) t_control = ahora;   // se ha retrasado: no acumular
    Robot::ciclo();
  }
  Comandos::leer();
  Tareas::actualizar();
}
