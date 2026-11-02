#pragma once
#include <stdint.h>
extern int sim_servo;
class Servo { public: void attach(int) {} void write(int a) { sim_servo = a; } };
