#include <avr/io.h>
#include <string.h>
#include <stdio.h>
#include "lib/uart.h"
#include "lib/uartSerial.h"
#include "lib/virtualSerial.h"

// Send a string via UART serial.
void sendStringUART (char* string)
{
	uart1_puts(string);
	// TODO: check out the type error warning...
}

// Get a string from the ring buffer.
// If bytes are in the buffer, the receive function will run as long
// as the buffer is not empty.
void receiveStringUART ( char* inputString, uint8_t stringSize )
{
	// Received character and error bitmask.
	unsigned int inputChar;
	
	// Get a character from the ring buffer.
	// Do this in a loop as long as new data is in the buffer.
	for(uint8_t charIndex = 0; charIndex<stringSize-1; charIndex++)
	{
		// Get byte from the buffer.
		// uart_getc returns the data byte and an error code.
		inputChar = uart1_getc();

		// Evaluate the error code to see if any data was passed.
		// If no data was passed...
		if ( inputChar & UART_NO_DATA )
		{
			//... append end of string character.
			// This will also clear the input string if nothing was received.
			inputString[charIndex] = '\0';
			// Exit the loop.
			break;
		}
		// Evaluate error codes.
		// In case of frame error...
		else if ( inputChar & UART_FRAME_ERROR )
		{
			//... send back error message.
			uart1_puts_P("UART Frame Error: ");
		}
		// In case of overrun error...
		else if ( inputChar & UART_OVERRUN_ERROR )
		{
			//... send back error message.
			// Overrun, a character already present in the UART UDR register was 
			// not read by the interrupt handler before the next character arrived,
			// one or more received characters have been dropped
			uart1_puts_P("UART Overrun Error: ");
		}
		// In case of buffer overflow...
		else if ( inputChar & UART_BUFFER_OVERFLOW )
		{
			//... send back error message.
			uart1_puts_P("Buffer overflow error: "); 
			// We are not reading the receive buffer fast enough,
			// one or more received character have been dropped 
		}
		// Finally, assemble the character to a string.
		inputString[charIndex] = inputChar;
	}
	// Return the pointer to the received string.
//	return inputString;
}
