#ifndef ROTARYENCODER_H
#define ROTARYENCODER_H

#include <avr/io.h>
#include <stdint.h>

// Rotary encoder channel A.
#define ROTARYENCODERADDR DDRF
#define ROTARYENCODERAPORT PORTF
#define ROTARYENCODERAPIN PIN5
#define ROTARYENCODERAPOLL PINF
// Rotary encoder channel B.
#define ROTARYENCODERBDDR DDRF
#define ROTARYENCODERBPORT PORTF
#define ROTARYENCODERBPIN PIN6
#define ROTARYENCODERBPOLL PINF

void rotaryEncoderInit(void);
int8_t rotaryEncoderCheck(void);

#endif // ROTARYENCODER_H
