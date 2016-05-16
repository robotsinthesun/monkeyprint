#include <string.h>
#include <stdlib.h>
#include <util/delay.h>

#include "lib/printerCommands.h"
#include "lib/uartSerial.h"		// Load custom serial functions.
#include "lib/virtualSerial.h"	// Load USB virtual serial functions.
#include "lib/printerFunctions.h"	// Load printer functions.


char inputString[30];
char* firstString;
char* secondString;
int16_t stringValue;
uint8_t uartFlag = 0;


// *****************************************************************************
// Function: Analyse an incoming string and parse it for printer commands. *****
// *****************************************************************************

// TODO: find out why a command cannot be longer than 16 characters (at least via USB).
// Maybe the USB virtual serial input buffer is set to 16 byte?
void processCommandInput( void )
{

	_delay_ms(100);
	
	// Receive a string from USB virtual serial.
	// This will write the received string to the input variable "inputString".
	receiveStringUSB(inputString, 30);
	

	// Receive a string from UART serial.
	// This will write the received string to the input variable "inputString".
	// Do this only in case inputString is empty.
	if (strlen(inputString)<1)
	{
		receiveStringUART(inputString, 30);
		//sendStringUART(inputString);
		//uint8_t stringLength = strlen(inputString);
		//sendByteAsStringUSB(stringLength);
		uartFlag = 1;
	}
	else
	{
		uartFlag = 0;
		//sendStringUART(strlen(inputString));
	}


	// Look for commands. ******************************************
	// strcmp returns and int wich is:
	//	0 in case of match
	//	<0 if str1 is lexicographically smaller than str2 (str1 will appear before str2 in a dictionary)
	//	>0 if str1 is lexicographically larger than str2 
	if (!(strcmp(inputString, "foo")))
	{
		if (!uartFlag)	sendStringUSB("bar\n");
		else	sendStringUART("bar\n");
		//pingFlag = 1;
	}
	if (!(strcmp(inputString, "ping")))
	{
		if (!uartFlag)	sendStringUSB("ping\n");
		else	sendStringUART("ping\n");
		
		//pingFlag = 1;
	}
	if (!(strcmp(inputString, "tilt")))
	{
		tilt(tiltAngle,tiltSpeed);
		_delay_ms(10);
		sendStringUSB("tilt\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "buildHome")))
	{
		buildPlatformHome();
		_delay_ms(10);
		sendStringUSB("buildHome\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "buildTop")))
	{
		buildPlatformTop();
		sendStringUSB("buildTop\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "buildBaseUp")))
	{
		buildPlatformBaseLayerUp();
		sendStringUSB("buildBaseUp\n");
	}
	else if (!(strcmp(inputString, "buildUp")))
	{
		buildPlatformLayerUp();
		sendStringUSB("buildUp\n");	// Important: don't forget newline character.
		//lcd_gotoxy(0,3);
		//lcd_puts("check");
	}
	else if (!(strcmp(inputString, "shutterOpen")))
	{
		shutterOpen();
		sendStringUSB("shutterOpen\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "shutterClose")))
	{
		shutterClose();
		sendStringUSB("shutterClose\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "shutterEnable")))
	{
		shutterEnable();
		sendStringUSB("shutterEnable\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "shutterDisable")))
	{
		shutterDisable();
		sendStringUSB("shutterDisable\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "triggerCam")))
	{
		triggerCamera();
		sendStringUSB("triggerCam\n");	// Important: don't forget newline character.
	}
	else if (!(strcmp(inputString, "beamerHome")))
	{
//			beamerHome();
	}
	else if (!(strcmp(inputString, "beamerTop")))
	{
//			beamerBottom();
	}
	// Look for commands that change values.
	else if (strlen(inputString)>0)
	{
		// Retrieve first string and second string separated by space.
		// Does not work if first + second string is longer than 16 chars.
		firstString = strtok(inputString, " ");
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
		else if (!(strcmp(firstString, "shttrOpnPs")))
		{
			// Retrieve layer value.
			stringValue = atoi(secondString);
			// Adjust value according to input.
			shutterSetOpenPos(stringValue);
//				lcd_gotoxy(0,3);
//				lcd_puti(stringValue);
			sendStringUSB("shttrOpnPs\n");
		}
		else if (!(strcmp(firstString, "shttrClsPs")))
		{
			// Retrieve layer value.
			stringValue = atoi(secondString);
			// Adjust value according to input.
			shutterSetClosePos(stringValue);
//				lcd_gotoxy(0,3);
//				lcd_puti(stringValue);
			sendStringUSB("shttrClsPs\n");
		}
	}
}
