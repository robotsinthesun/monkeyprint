#ifndef HARDWARE_H
#define HARDWARE_H

#include <avr/io.h>
#include <stdint.h>

// LEDs. ***********************************************************************
// Orange.
#define LED2DDR DDRF
#define LED2PORT PORTF
#define LED2PIN PIN4
// Green.
#define LED1DDR DDRF
#define LED1PORT PORTF
#define LED1PIN PIN5

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
#define SERVOCLOCKDDR DDRD
#define SERVOCLOCKPORT PORTD
#define SERVOCLOCKPIN PIN7



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

/*
#ifndef HARDWARE_H
#define HARDWARE_H

#include <avr/io.h>
#include <stdint.h>

// LEDs. ***********************************************************************
// Yellow 1.
//#define LED1DDR DDRB		// DONT USE --> CONNECTED TO LCD.
//#define LED1PORT PORTB
//#define LED1PIN PIN0
// Yellow 2.
//#define LED2DDR DDRD
//#define LED2PORT PORTD
//#define LED2PIN PIN5
// Green 1.
//#define LED3DDR DDRC		// DONT USE --> CONNECTED TO STEPPER.
//#define LED3PORT PORTC
//#define LED3PIN PIN7

// ALTERNATIVE NAME FOR LED2 TO AVOID CONFUSION. USE LED ONLY!
#define LEDDDR DDRD
#define LEDPORT PORTD
#define LEDPIN PIN5

// Stepper outputs. ************************************************************
// Build platform stepper. ******
// Clock.
#define BUILDCLOCKDDR DDRC
#define BUILDCLOCKPORT PORTC
#define BUILDCLOCKPOLL PINC
#define BUILDCLOCKPIN PIN6
// Dir.
#define BUILDDIRDDR DDRD
#define BUILDDIRPORT PORTD
#define BUILDDIRPIN PIN4
// Enable.
#define BUILDENABLEDDR DDRD
#define BUILDENABLEPORT PORTD
#define BUILDENABLEPIN PIN7
// Beamer stepper. **************
// Clock.
#define BEAMERCLOCKDDR DDRB
#define BEAMERCLOCKPORT PORTB
#define BEAMERCLOCKPOLL PINB
#define BEAMERCLOCKPIN PIN5
// Dir.
#define BEAMERDIRDDR DDRD
#define BEAMERDIRPORT PORTD
#define BEAMERDIRPIN PIN0
// Enable.
#define BEAMERENABLEDDR DDRB
#define BEAMERENABLEPORT PORTB
#define BEAMERENABLEPIN PIN6
// Tilt stepper. ****************
// Clock.	SAME AS LED3...
#define TILTCLOCKDDR DDRC
#define TILTCLOCKPORT PORTC
#define TILTCLOCKPOLL PINC
#define TILTCLOCKPIN PIN7
// Dir.
#define TILTDIRDDR DDRD
#define TILTDIRPORT PORTD
#define TILTDIRPOLL PIND
#define TILTDIRPIN PIN6
// Enable.
#define TILTENABLEDDR DDRB
#define TILTENABLEPORT PORTB
#define TILTENABLEPIN PIN7

// Interrupts. *****************************************************************
// Limit switches.
// Build platform top.
#define LIMITBUILDTOPDDR DDRB
#define LIMITBUILDTOPPORT PORTB
#define LIMITBUILDTOPPIN PIN4
#define LIMITBUILDTOPPOLL PINB
// Build platform bottom.
#define LIMITBUILDBOTTOMDDR DDRD
#define LIMITBUILDBOTTOMPORT PORTD
#define LIMITBUILDBOTTOMPIN PIN1
#define LIMITBUILDBOTTOMPOLL PIND
// Tilt.
#define LIMITTILTDDR DDRE
#define LIMITTILTPORT PORTE
#define LIMITTILTPIN PIN6
#define LIMITTILTPOLL PINE
// Beamer top.
#define LIMITBEAMERTOPDDR DDRD
#define LIMITBEAMERTOPPORT PORTD
#define LIMITBEAMERTOPPIN PIN2
#define LIMITBEAMERTOPPOLL PIND
// Beamer bottom.
#define LIMITBEAMERBOTTOMDDR DDRD
#define LIMITBEAMERBOTTOMPORT PORTD
#define LIMITBEAMERBOTTOMPIN PIN3
#define LIMITBEAMERBOTTOMPOLL PIND


void setupHardware(void);
void timer1SetCompareValue( uint16_t input );
void timer3SetCompareValue( uint16_t input );
void timer4SetCompareValue( uint8_t input );
uint8_t readADC(uint8_t channel);

#endif // HARDWARE_H
*/
