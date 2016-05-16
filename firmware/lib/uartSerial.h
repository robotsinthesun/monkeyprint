#ifndef UARTSERIAL_H
#define UARTSERIAL_H

// Functions.
void sendStringUART (char* string);
void sendByteAsStringUART(uint16_t dataByte);
//char* receiveStringUART ( char* inputString, uint8_t stringSize );
void receiveStringUART ( char* inputString, uint8_t stringSize );

#endif
