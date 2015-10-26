#ifndef BUTTON_H
#define BUTTON_H

#include <avr/io.h>
#include <stdint.h>

#define BUTTONDDR DDRF
#define BUTTONPORT PORTF
#define BUTTONPIN PIN7
#define BUTTONPOLL PINF

uint8_t buttonCheck(void);
void buttonInit(void);

#endif // BUTTON_H
