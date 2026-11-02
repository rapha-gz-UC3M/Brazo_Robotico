#pragma once
#include <string.h>
#include <stdint.h>
struct SimEEPROM {
  uint8_t mem[1024];
  SimEEPROM() { memset(mem, 0xFF, sizeof(mem)); }
  template <class T> T &get(int a, T &t) { memcpy(&t, mem + a, sizeof(T)); return t; }
  template <class T> const T &put(int a, const T &t) { memcpy(mem + a, &t, sizeof(T)); return t; }
};
extern SimEEPROM EEPROM;
