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
#include "lib/lcd.h"
#include "lib/button.h"
#include "lib/rotaryEncoder.h"
#include "lib/menu.h"
#include "lib/printerFunctions.h"
//#include "lib/gCodeInterpreter.h"


// *****************************************************************************
// Variable declarations. ******************************************************
// *****************************************************************************

// Lcd and menu stuff. *********************************************************
uint8_t menuButton = 0;
int8_t menuMove = 0;



// Stepper idle timer. *********************************************************
uint8_t stepperIdleCount = 0;



// Menu idle timer. ************************************************************
uint8_t menuIdleCount = 0;



// Main loop timer stuff. ******************************************************
volatile uint8_t timerFlag = 0;
volatile uint16_t timerCount = 0;
volatile uint16_t timerMilliSeconds = 100;	// ms


char* testChar;
char testBuffer[30];
uint8_t bytesWaiting;
uint8_t charIndex;
uint8_t sendErrorCode;
char* firstString;
char* secondString;
int16_t stringValue;

uint8_t pingFlag = 0;
//uint8_t printingFlag;
//uint16_t numberOfSlices;
//uint16_t currentSlice;


// *****************************************************************************
// Here we go! *****************************************************************
// *****************************************************************************
int main(void)
{	

	// Initialise port configurations, timers, etc. ***************************
	setupHardware();


	// Show splash screen. ****************************************************
//	lcd_clrscr();
	ledYellowOn();
	ledGreenOff();
	int startup;
	for (startup=0; startup<5; startup++)
	{
		ledYellowToggle();
		ledGreenToggle();
		_delay_ms(100);
	}
	ledYellowOff();
	ledGreenOff();
	
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
		
		charIndex = 0;		
//		lcd_gotoxy(0,0);
		while(bytesWaitingUSB())
		{	
//			lcd_clrscr();
			testBuffer[charIndex] = receiveCharUSB();
			charIndex++;
		}
		testBuffer[charIndex]='\0';	// Append end of string character, clear the string if nothing was received (charIndex=0).
//		if(strlen(testBuffer)>2)
//		{
//			lcd_putu(strlen(testBuffer));
//			lcd_gotoxy(0,3);
//			lcd_puts(testBuffer);
//		}
		
		// Look for commands. ******************************************
		// strcmp returns and int wich is:
		//	0 in case of match
		//	<0 if str1 is lexicographically smaller than str2 (str1 will appear before str2 in a dictionary)
		//	>0 if str1 is lexicographically larger than str2 
		if (!(strcmp(testBuffer, "ping")))
		{
			pingFlag = 1;
		}
		if (!(strcmp(testBuffer, "tilt")))
		{
			tilt(tiltAngle,tiltSpeed);
			_delay_ms(10);
			sendStringUSB("tilt\n");	// Important: don't forget newline character.
		}
		else if (!(strcmp(testBuffer, "buildHome")))
		{
			buildPlatformHome();
			_delay_ms(10);
			sendStringUSB("buildHome\n");	// Important: don't forget newline character.
		}
		else if (!(strcmp(testBuffer, "buildTop")))
		{
			buildPlatformTop();
			sendStringUSB("buildTop\n");	// Important: don't forget newline character.
		}
		else if (!(strcmp(testBuffer, "buildBaseUp")))
		{
			buildPlatformBaseLayerUp();
			sendStringUSB("buildBaseUp\n");
		}
		else if (!(strcmp(testBuffer, "buildUp")))
		{
			buildPlatformLayerUp();
			sendStringUSB("buildUp\n");	// Important: don't forget newline character.
			//lcd_gotoxy(0,3);
			//lcd_puts("check");
		}
		else if (!(strcmp(testBuffer, "triggerCam")))
		{
	/*		triggerCamera();
			sendStringUSB("triggerCam\n");	// Important: don't forget newline character.
			//lcd_gotoxy(0,3);
			//lcd_puts("check");
	*/	}
		else if (!(strcmp(testBuffer, "beamerHome")))
		{
//			beamerHome();
		}
		else if (!(strcmp(testBuffer, "beamerTop")))
		{
//			beamerBottom();
		}
		// Look for commands that change values.
		else if (strlen(testBuffer)>0)
		{
			// Retrieve first string and second string separated by space.
			// Does not work if first + second string is longer than 16 chars.
			firstString = strtok(testBuffer, " ");
			secondString = strtok(NULL, " ");	// WHY DOES THIS WORK?

			if (!(strcmp(firstString, "buildLayer")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				buildPlatformSetLayerHeight(stringValue);
				sendStringUSB("buildLayer\n");
			}
			else if (!(strcmp(firstString, "buildBaseLayer")))
			{
				// Convert value to integer.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				buildPlatformSetBaseLayerHeight(stringValue);
				sendStringUSB("buildBaseLayer\n");
			}
			else if (!(strcmp(firstString, "tiltSpeed")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				tiltSetSpeed(stringValue);
				sendStringUSB("tiltSpeed\n");
			}
			else if (!(strcmp(firstString, "tiltAngle")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				tiltSetAngle(stringValue);
				sendStringUSB("tiltAngle\n");
			}
			else if (!(strcmp(firstString, "tiltRes")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				tiltSetAngleMax(stringValue);
				sendStringUSB("tiltRes\n");
			}
			else if (!(strcmp(firstString, "buildSpeed")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				buildPlatformSetSpeed(stringValue);
				sendStringUSB("buildSpeed\n");
			}
			else if (!(strcmp(firstString, "buildRes")))
			{
				// Retrieve value and convert to int.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				buildPlatformSetResolution(stringValue);
				sendStringUSB("buildRes\n");
			}
			else if (!(strcmp(firstString, "buildMinMove")))
			{
				// Retrieve value and convert to int.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				buildPlatformSetMinMove(stringValue);
				sendStringUSB("buildMinMove\n");
			}
			else if (!(strcmp(firstString, "buildMove")))
			{
				// Retrieve value and convert to int.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				buildPlatformMove(stringValue);
				sendStringUSB("buildMove\n");
			}
			else if (!(strcmp(firstString, "printingFlag")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				// 0 is idle, 1 is printing.
				if (stringValue==0 || stringValue==1)
				{
					printerSetState(stringValue);
//					menuGoInfoScreen();
				}
				sendStringUSB("printingFlag\n");
			}
			else if (!(strcmp(firstString, "slice")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				printerSetSlice(stringValue);
//				menuChanged()
				sendStringUSB("slice\n");;

			}
			else if (!(strcmp(firstString, "nSlices")))
			{
				// Retrieve layer value.
				stringValue = atoi(secondString);
				// Adjust value according to input.
				printerSetNumberOfSlices(stringValue);
//				lcd_gotoxy(0,3);
//				lcd_puti(stringValue);
				sendStringUSB("nSlices\n");
			}
		}


		
		
		
		

		
		
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


			// Disable steppers if idle for more than 10 seconds.
			if ( !( (TCCR1B & (1 << CS10)) || (TCCR3B & (1 << CS30)) || (TCCR4B & (1 << CS43 | 1 << CS40)) ) )
			{
				if (++stepperIdleCount == 100)
				{
					stepperIdleCount = 0;
//					disableSteppers();	// Dont do this to avoid loosing steps. Do this on purpose only and not during prints.
//					tiltDisableStepper();	// That's OK, loosing steps in tilt is not that much of a problem.
				}
			}
			
			
			// Jump back to home screen if idle for more than 20 seconds.
//			if (++menuIdleCount == 200)
//			{
//				menuIdleCount = 0;
//				menuGoInfoScreen();
//			}
			
			// Send pingback.
			if(pingFlag)
			{
				_delay_ms(100);
				sendStringUSB("ping\n");	// Important: don't forget newline character.
				pingFlag = 0;
			}
			
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
ISR (TIMER4_COMPA_vect)
{
	// Toggle output pin.
//	TILTCLOCKPORT ^= (1 << TILTCLOCKPIN);
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
	buildPlatformDisableStepper();
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
