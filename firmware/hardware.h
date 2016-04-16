#ifndef HARDWARE_H
#define HARDWARE_H

#include <avr/io.h>
#include <stdint.h>

// LEDs. ***********************************************************************
// Additional LEDs.

// Orange.
#define LED2DDR DDRF
#define LED2PORT PORTF
#define LED2PIN PIN4
// Green.
#define LED1DDR DDRF
#define LED1PORT PORTF
#define LED1PIN PIN5

// Onboard LEDs.
// Yellow.
#define LED1ONBOARDDDR DDRB
#define LED1ONBOARDPORT PORTB
#define LED1ONBOARDPIN PIN0
// Green.
#define LED2ONBOARDDDR DDRD
#define LED2ONBOARDPORT PORTD
#define LED2ONBOARDPIN PIN5

// Camera trigger pin. *********************************************************
# define CAMDDR DDRB
# define CAMPORT PORTB
# define CAMPIN PIN6

// Stepper outputs. ************************************************************
// Build platform stepper. ******
// Clock.
#define BUILDCLOCKDDR DDRB
#define BUILDCLOCKPORT PORTB
#define BUILDCLOCKPOLL PINB
#define BUILDCLOCKPIN PIN5
// Dir.
#define BUILDDIRDDR DDRB
#define BUILDDIRPORT PORTB
#define BUILDDIRPIN PIN4
// Enable.
#define BUILDENABLEDDR DDRF
#define BUILDENABLEPORT PORTF
#define BUILDENABLEPIN PIN7

// Tilt stepper. ****************
// Clock.	SAME AS LED3...
#define TILTCLOCKDDR DDRC
#define TILTCLOCKPORT PORTC
#define TILTCLOCKPOLL PINC
#define TILTCLOCKPIN PIN6
// Dir.
#define TILTDIRDDR DDRD
#define TILTDIRPORT PORTD
#define TILTDIRPOLL PIND
#define TILTDIRPIN PIN4
// Enable.
#define TILTENABLEDDR DDRF
#define TILTENABLEPORT PORTF
#define TILTENABLEPIN PIN6

// Servo output. ***************************************************************
// Clock.
#define SERVODDR DDRD
#define SERVOPORT PORTD
#define SERVOPIN PIN7



// Interrupts. *****************************************************************
// Limit switches.
// Build platform top.
#define LIMITBUILDTOPDDR DDRD
#define LIMITBUILDTOPPORT PORTD
#define LIMITBUILDTOPPIN PIN1
#define LIMITBUILDTOPPOLL PIND
// Build platform bottom.
#define LIMITBUILDBOTTOMDDR DDRD
#define LIMITBUILDBOTTOMPORT PORTD
#define LIMITBUILDBOTTOMPIN PIN0
#define LIMITBUILDBOTTOMPOLL PIND
// Tilt.
#define LIMITTILTDDR DDRE
#define LIMITTILTPORT PORTE
#define LIMITTILTPIN PIN6
#define LIMITTILTPOLL PINE


void setupHardware(void);
void timer1SetCompareValue( uint16_t input );
void timer3SetCompareValue( uint16_t input );
void timer4SetCompareValue( uint8_t input );
uint8_t readADC(uint8_t channel);
void ledYellowOn( void );
void ledYellowOff( void );
void ledYellowToggle( void );
void ledGreenOn( void );
void ledGreenOff( void );
void ledGreenToggle( void );

#endif // HARDWARE_H
