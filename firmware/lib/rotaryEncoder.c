#include <avr/io.h>
#include <stdio.h>
#include <stdint.h>
		
#include "rotaryEncoder.h"
#include "hardware.h"	// Needed for testing to use LEDs.

// *****************************************************************************
// Declare variables. **********************************************************
// *****************************************************************************
int8_t rotaryEncoderState = 0;
uint8_t phaseACount = 0;
uint8_t phaseDelay = 50;
uint8_t phaseA = 1;
uint8_t phaseAOld = 1;
uint8_t phaseBCount = 0;
uint8_t phaseB = 1;


// *****************************************************************************
// Function: set up encoder pins.
// *****************************************************************************
void rotaryEncoderInit(void)
{
	ROTARYENCODERADDR &= ~(1 << ROTARYENCODERAPIN);	// Set as input.
	ROTARYENCODERAPORT |= (1 << ROTARYENCODERAPIN); 	// Activate pull-up.
	ROTARYENCODERBDDR &= ~(1 << ROTARYENCODERBPIN);	// Set as input.
	ROTARYENCODERBPORT |= (1 << ROTARYENCODERBPIN); 	// Activate pull-up.
}


// *****************************************************************************
// Function: check rotary encoder turn. 
// Should be called every main loop.
// Returns 0 if encoder has not been turned.
// Returns 1 for clockwise turn.
// Returns -1 for counter-clockwise turn.
// *****************************************************************************

int8_t rotaryEncoderCheck(void)
{

//	// Test rotary encoder phases. *******************************************s
//	if ( !(ROTARYENCODERAPOLL & (1 << ROTARYENCODERAPIN)) ) LED3PORT |= (1 << LED3PIN);
//	else LED3PORT &= ~(1 << LED3PIN);
//	if ( !(ROTARYENCODERBPOLL & (1 << ROTARYENCODERBPIN)) ) LED2PORT |= (1 << LED2PIN);
//	else LED2PORT &= ~(1 << LED2PIN);

		
	// Check encoder channel A and debounce. **********************************
	if (!(ROTARYENCODERAPOLL & (1 << ROTARYENCODERAPIN)))	// Check if pin low.
	{			
		if (phaseACount++ == phaseDelay)	// Debounce.
		{	
			// Debounce time reached.
			phaseACount = 0;				// Reset counter.
			phaseA = 0;					// Set phase A flag.
		}
	}
	else
	{
		// Reset counter and stay calm.
		phaseACount = 0;
		phaseA = 1;
	}
	
	// Check encoder channel B and debounce. **********************************
	if (!(ROTARYENCODERBPOLL & (1 << ROTARYENCODERBPIN)))	// Check if pin low.
	{			
		if (phaseBCount++ == phaseDelay)		// Debounce.
		{	
			// Debounce time reached.
			phaseBCount = 0;				// Reset counter.
			phaseB = 0;					// Set phase B flag.
		}
	}
	else
	{
		// Reset counter and stay calm.
		phaseBCount = 0;
		phaseB = 1;
	}
	
	
	
//	// Flash some LEDs for testing. *******************************************
//	if ( phaseA==0 ) LED3PORT |= (1 << LED3PIN);
//	else LED3PORT &= ~(1 << LED3PIN);
//	if ( phaseB==0 ) LED2PORT |= (1 << LED2PIN);
//	else LED2PORT &= ~(1 << LED2PIN);
	
	
	// Check for fall in phase A. *********************************************
	if (phaseAOld==1 && phaseA==0)
	{
		// Test phase B.
		if (phaseB==0)
		{
//			LED3PORT ^= (1 << LED3PIN);
			rotaryEncoderState = -1;			// CW.
		}
		else if (phaseB==1)
		{
//			LED2PORT ^= (1 << LED2PIN);
			rotaryEncoderState = 1;		// CCW.
		}
	}
	else rotaryEncoderState = 0;
	phaseAOld = phaseA;
		
	// Send return value. *****************************************************
	return rotaryEncoderState;	
}
