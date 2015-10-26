#include <avr/io.h>
#include <stdio.h>
#include <stdint.h>
#include <util/delay.h>
		
#include "button.h"

// *****************************************************************************
// Declare variables. **********************************************************
// *****************************************************************************

uint16_t buttonCount = 0;
uint16_t buttonDelay[2] = {50, 350};	// First for button press delay, second for button held delay. Times 20, see line 39.
uint8_t buttonPressedFlag = 0;
uint8_t buttonAction = 0;


// *****************************************************************************
// Function: Initialise button pin.
// *****************************************************************************
void buttonInit(void)
{
	BUTTONDDR &= ~(1 << BUTTONPIN);	// Configure as input.
	BUTTONPORT |= (1 << BUTTONPIN);	// Activate pull-up.
}

// *****************************************************************************
// Function: check button press. 
// Should be called every main loop.
// Returns 0 if button not pressed or debounce not reached.
// Returns 1 if button is pressed and debounce reached.
// Returns 1 in larger intervals if button is held.
// *****************************************************************************
uint8_t buttonCheck(void)		
{
	// Check button press (active low).
	if (!(BUTTONPOLL & (1 << BUTTONPIN)))		
	{			
		if ((buttonCount++ /20) > buttonDelay[buttonPressedFlag])	// Compare button down time to debounce time or button hold time.
														// Divide by 20 to work around 16 bit comparison.
		{	
			// Debounce or hold time reached.
			buttonCount = 0;							// Reset counter.
			buttonPressedFlag = 1;						// Set button pressed flag to go into button hold mode.
			buttonAction = 1;	
		}
		else
		{
			// Debounce or hold time not reached.
			buttonAction = 0;
		}
	}
	else
	{
		// Button not pressed.
		buttonCount = 0;
		buttonPressedFlag = 0;
		buttonAction = 0;
	}
	
	return buttonAction;
}
