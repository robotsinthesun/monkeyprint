#include <avr/io.h>
#include <avr/wdt.h>	// Watchdog timer configuration functions.
#include <avr/power.h>	// Clock prescaler configuration functions.
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <string.h>
#include <stdio.h>
#include <util/delay.h>
		
#include "hardware.h"
		
#include "lib/virtualSerial.h"
#include "lib/uartSerial.h"
#include "lib/lcd.h"
#include "lib/button.h"
#include "lib/rotaryEncoder.h"
#include "lib/menu.h"
#include "lib/printerFunctions.h"
#include "lib/printerCommands.h"


// *****************************************************************************
// Variable declarations. ******************************************************
// *****************************************************************************

// Misc.
uint8_t foo = 0;

// Lcd and menu stuff. *********************************************************
uint8_t menuButton = 0;
int8_t menuMove = 0;



// Stepper idle timer. *********************************************************
uint16_t stepperIdleCount = 0;



// Menu idle timer. ************************************************************
uint8_t menuIdleCount = 0;



// Main loop timer stuff. ******************************************************
volatile uint8_t timerFlag = 0;
volatile uint16_t timerCount = 0;
volatile uint16_t timerMilliSeconds = 100;	// ms


// *****************************************************************************
// Here we go! *****************************************************************
// *****************************************************************************
int main(void)
{	

	LED1DDR |= (1 << LED1PIN);
	LED1PORT |= (1 << LED1PIN);	//OFF


	// Initialise port configurations, timers, etc. ***************************
	setupHardware();


	
//	lcd_gotoxy(6,1);
//	lcd_puts("Bob says");
//	lcd_gotoxy(7,2);
//	lcd_puts("Hello!");
//	_delay_ms(2000);
//	LEDPORT &= ~(1 << LEDPIN);
//	lcd_clrscr();

//	menuChanged();

	// Enable interrupts. *****************************************************
	sei();

	
	// Initialise printer. ****************************************************
	printerInit();


	// Show splash screen. ****************************************************
	ledYellowOn();
	ledGreenOff();
	for (uint8_t startup=0; startup<8; startup++)
	{
		ledYellowToggle();
		ledGreenToggle();
		_delay_ms(100);
	}
	ledYellowOff();
	ledGreenOff();



	// ************************************************************************
	// Main loop. *************************************************************
	// ************************************************************************
	while(1)
	{
		//**************************************************************
		//************ Receive printer control commands. ***************
		//**************************************************************
		
		// Receive and analyse incoming data. ******************
		// Use echo -n "command" > /dev/ttyACM0	to send commands. -n option is important to suppress newline char at end of string.
		processCommandInput();
				
		//**************************************************************
		//************* Update menu. ***********************************
		//**************************************************************

//		// Check inputs. ***********************************************
//		menuButton = buttonCheck();
//		menuMove = rotaryEncoderCheck();
		// Reset menu idle counter on button press or encoder action.
//		if (menuButton || menuMove)
//		{
//			menuIdleCount = 0;
//		}
				
		
		// Evaluate inputs and update menu accordingly. ****************
//		menuEvaluateInput(menuButton, menuMove);
		
		// Draw menu. **************************************************
//		menuDraw();



		//**************************************************************
		//************* Initialise stepper motion. *********************
		//**************************************************************

		// Check for difference between current and set build platform position.
		// Start stepper if difference detected.
		buildPlatformComparePosition(buildPlatformSpeed);
//		beamerComparePosition(beamerSpeed);

		
		// Do things in intervals of timerMilliSeconds. ****************
		if (timerFlag)
		{	
			// Reset timer flag.
			timerFlag = 0;
			
			// Update LCD if stepper is running.
			if (TCCR3B & (1 << CS30) || TCCR1B & (1 << CS10))
			{
//				menuChanged();
			}

			// Disable steppers if idle for more than 100 seconds or print has ended.
			if ( !( (TCCR1B & (1 << CS10)) || (TCCR3B & (1 << CS30)) || (TCCR4B & (1 << CS43 | 1 << CS40)) ) )
			{
				if (++stepperIdleCount == 1000 && !(printerGetState()))
				{
					stepperIdleCount = 0;
					disableSteppers();	// Dont do this to avoid loosing steps. Do this on purpose only and not during prints.
//					tiltDisableStepper();	// That's OK, loosing steps in tilt is not that much of a problem.
				}
			}
			
			
			// Jump back to home screen if idle for more than 20 seconds.
//			if (++menuIdleCount == 200)
//			{
//				menuIdleCount = 0;
//				menuGoInfoScreen();
//			}
			
			
			// Send data. **************************************************
			// Operation finished?
			if(printerReady())
			{
				_delay_ms(100);
				sendStringUSB("done\n");	// Important: don't forget newline character.
			}

		} // timerFlag.
		

		// Take care of usb connection. **************************************
		manageUSB(1);	// Paramter 1 if receiving function was used before, otherwise 0.




	} // Main while loop.

	return 0;
}


	
	


// *****************************************************************************
// Compare interrupt subroutine. Runs every 10e-4 seconds. *********************
// *****************************************************************************

// Main loop CTC timer. ********************************************************
ISR (TIMER0_COMPA_vect)
{
	// If timerCycles reached (e.g. 10 for one millisecond)
	// set flag for main loop and reset counter.
	if(timerCount == timerMilliSeconds*10)
	{
		timerFlag = 1;
		timerCount = 0;
	}
	else
	{
		timerCount++;
	}	
}



// Build platform stepper CTC timer. ***************************************************
ISR (TIMER1_COMPA_vect)
{
	// Count on rising edge only.
	if (BUILDCLOCKPOLL & (1 << BUILDCLOCKPIN))// && BUILDENABLEPORT & (1 << BUILDENABLEPIN))
	{

//		if (!buildPlatformHomingFlag)
//		{
			// Count steps, compare current to target position etc.
			buildPlatformControl();
//		}
	}
}



// Tilt stepper CTC timer. *******************************************
ISR (TIMER3_COMPA_vect)
{
	// Count on rising edge only.
	if (TILTCLOCKPOLL & (1 << TILTCLOCKPIN))
	{
		// Control tilt.
		tiltControl();
	}
}



// Tilt stepper CTC timer. *****************************************************
// Compare match interrupt.
ISR (TIMER4_COMPD_vect)
{
	// Reset servo signal pin on compare match.
	SERVOPORT &= ~(1 << SERVOPIN);
}
// Timer overflow interrupt.
ISR (TIMER4_OVF_vect)
{
	// Skip a couple of timer cycles and then set servo pin high.
	servoControl();
}



// Limit switch build platform top. ********************************************
ISR (INT1_vect)
{
	ledYellowOff();
	// Disable build platform clock timer.
	buildPlatformDisableStepper();
//	TCCR1B &= ~(1 << CS10);		// Deactivate timer by disabling clock source.
	// Lock position.
	buildPlatformTargetPosition = buildPlatformPosition;
//	menuValueSet(buildPlatformTargetPosition,20);			// TO DO: put this into set function for buildPlatformTargetPosition!
//	menuChanged();
}

// Limit switch build platform bottom. *****************************************
ISR (INT0_vect)
{

	ledGreenOff();
	// Disable build platform clock timer.
	buildPlatformStopStepper();
//	TCCR1B &= ~(1 << CS10);		// Deactivate timer by disabling clock source.
	// Reset flags and position.
	buildPlatformHomingFlag = 0;
	buildPlatformPosition = 0;
//	sendByteAsStringUSB(buildPlatformPosition);
//	menuChanged();
	// GO UP A BIT AND THEN DOWN AT LOWEST SPEED TO INCREASE HOMING PRECISION!
}

// Limit switch tilt.
ISR (INT6_vect)
{
	ledGreenOff();
	if (tiltStepperRunning() && !(tiltStepperGetDirection()))
	{
		stopTiltStepper();
		// Set forward direction for next run.
		tiltStepperSetForward();
	}
}	

// Catch any unexpected interrupts and flash LED.
ISR (BADISR_vect)
{
	while(1)
	{
		ledYellowToggle();
		ledGreenToggle();
		_delay_ms(50);
	}
}

//********************************** EOF *************************************//
