// Arduino.h simulado (PC): lo justo para compilar el firmware y conectarlo a un modelo del brazo.
#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <stdio.h>
#include <string>
#include <algorithm>

typedef bool boolean;
typedef uint8_t byte;
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define CHANGE 1
#define PI 3.14159265358979f
#define A0 14
#define A1 15
#define A2 16
#define A3 17
#define A4 18
#define A5 19
template <class T, class L, class H> inline T constrain(T x, L a, H b) { return x < a ? a : (x > b ? b : x); }
using std::min; using std::max;
template <class T> inline T sq(T x) { return x * x; }
inline float min(float a, double b) { return a < b ? a : (float)b; }
inline float max(float a, double b) { return a > b ? a : (float)b; }
inline float max(double a, float b) { return a > b ? (float)a : b; }

uint32_t millis(); uint32_t micros();
void pinMode(uint8_t, uint8_t); void digitalWrite(uint8_t, uint8_t); int digitalRead(uint8_t);
void analogWrite(uint8_t, int); int analogRead(uint8_t);
inline void noInterrupts() {} inline void interrupts() {}
void attachInterrupt(uint8_t, void (*f)(), int);
inline uint8_t digitalPinToInterrupt(uint8_t p) { return p == 2 ? 0 : 1; }
extern uint8_t sim_puertos[4];
inline uint8_t digitalPinToPort(uint8_t p) { return p / 8; }
inline uint8_t digitalPinToBitMask(uint8_t p) { return 1 << (p % 8); }
inline volatile uint8_t *portInputRegister(uint8_t port) { return &sim_puertos[port]; }

// memoria de programa: en el PC es memoria normal
class __FlashStringHelper;
#define F(s) (reinterpret_cast<const __FlashStringHelper *>(s))
#define PSTR(s) (s)
typedef const char *PGM_P;
#define strcmp_P strcmp

class SimSerial {
public:
  void begin(long) {}
  int available();
  int read();
  void print(const char *s) { out(s); }
  void print(const __FlashStringHelper *s) { out((const char *)s); }
  void print(char c) { char b[2] = { c, 0 }; out(b); }
  void print(int v) { char b[16]; snprintf(b, 16, "%d", v); out(b); }
  void print(unsigned v) { char b[16]; snprintf(b, 16, "%u", v); out(b); }
  void print(long v) { char b[24]; snprintf(b, 24, "%ld", v); out(b); }
  void print(unsigned long v) { char b[24]; snprintf(b, 24, "%lu", v); out(b); }
  void print(bool v) { print((int)v); }
  void print(double v, int d = 2) { char b[32]; snprintf(b, 32, "%.*f", d, v); out(b); }
  template <class T> void println(T v) { print(v); out("\n"); }
  void println(double v, int d) { print(v, d); out("\n"); }
  void println() { out("\n"); }
  void out(const char *s);
};
extern SimSerial Serial;
