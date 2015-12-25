// Configuration of Megaxxxu4 or XMegaxxxa4u USB interfaces as a virtual serial port using the awesome LUFA library by Dean Camera.
// Provides functions for sending and receiving bytes and strings.
// IMPORTANT NOTE: Function manageUSB() has to be called at least every 30 ms to keep the USB connection going!

#ifndef _VIRTUALSERIAL_H_
#define _VIRTUALSERIAL_H_

// Include LUFA stuff.
#include "Descriptors.h"

#include <LUFA/Drivers/USB/USB.h>
#include <LUFA/Platform/Platform.h>

// Function prototypes sending and receiving.
uint8_t sendStringUSB(char* dataString);
void sendByteAsStringUSB(uint16_t dataByte);
void sendByteUSB(uint8_t dataByte);
uint16_t bytesWaitingUSB(void);
uint16_t receiveByteUSB(void);
char receiveCharUSB(void);
char* receiveStringUSB(char* inputString, uint8_t stringSize);

// Function prototype for managing the USB interface.
void manageUSB(uint8_t receiving);

// Function prototypes USB status signals.
void EVENT_USB_Device_Connect(void);
void EVENT_USB_Device_Disconnect(void);
void EVENT_USB_Device_ConfigurationChanged(void);
void EVENT_USB_Device_ControlRequest(void);

#endif
