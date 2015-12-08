#ifndef PRINTERFUNCTIONS_H
#define PRINTERFUNCTIONS_H

#include <avr/io.h>
#include <avr/wdt.h>	// Watchdog timer configuration functions.
#include <avr/power.h>	// Clock prescaler configuration functions.
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <string.h>
#include <stdio.h>
#include <util/delay.h>
#include "../hardware.h"

// *****************************************************************************
// Init function. **************************************************************
// *****************************************************************************
void printerInit(void);


// *****************************************************************************


// *****************************************************************************
// Tilt functions. *************************************************************
// *****************************************************************************

// Variables. ******************************************************************
uint8_t tiltSpeed;
uint16_t tiltAngle;
volatile uint16_t tiltTimerCompareValue;
volatile uint16_t tiltCounter;
volatile uint16_t tiltCounterMax;
volatile uint8_t tiltingFlag;
uint16_t tiltAngleSteps;
//int16_t tiltTimerCompareValue;

// Turn with given angle and speed. ********************************************
uint8_t tiltStepperRunning(void);
void tiltSetAngle(uint16_t);
void tiltSetAngleMax(uint16_t);
void enableTiltStepper(void);
void disableTiltStepper(void);
void tiltStepperSetForward ( void );
void tiltStepperSetBackward ( void );
uint8_t tiltStepperGetDirection(void);
void tilt(uint8_t tiltAngle, uint8_t tiltSpeed);
void controlTilt(void);
void tiltDisableStepper(void);
void stopTiltStepper(void);
void tiltSetSpeed(uint8_t input);



// *****************************************************************************
// Build platform functions. ***************************************************
// *****************************************************************************

// Variables. ******************************************************************
#define BUILDPLATFORM_STEPS_PER_STANDARD_LAYER 20			// Number of steps per standard layer. (20 steps for 0.01 mm).
#define BUILDPLATFORM_MAX_STANDARD_LAYERS 50				// Maximum number of standard layers per actual layer. 50 --> 0.5 mm.
#define BUILDPLATFORM_SPEED_MAX 4
#define BUILDPLATFORM_SPEED_MIN 1
uint8_t buildPlatformSpeed;						// Stepper speed from 1--4.
volatile uint8_t buildPlatformCount;					// Step counter.
uint8_t buildPlatformLayer;					// Layer height in multiples of standard layer.
uint8_t buildPlatformBaseLayer;
volatile uint16_t buildPlatformPosition;				// Current position in standard layers.
volatile uint16_t buildPlatformTargetPosition;			// Target position in standard layers.
volatile uint8_t buildPlatformHomingFlag;
volatile uint8_t stopFlag;
volatile int16_t buildTimerCompareValue;
void buildPlatformControl(void);

// Build platform functions. ***************************************************
void buildPlatformAdjustSpeed (uint8_t input);
void buildPlatformSetSpeed (uint8_t input);
void buildPlatformSetResolution (uint16_t input);
void buildPlatformSetMinMove (uint16_t input);
//void buildPlatformSetLayerHeight (uint8_t numberOfBaseLayers);		// Set the number of base layers per layer.
//uint8_t buildPlatformGetLayerHeight (void);				// Get the number of base layers per layer.
void buildPlatformAdjustLayerHeight (uint8_t input);			// Increase or decrease the number of standard layers per layer.
void buildPlatformSetLayerHeight (uint8_t input);
void buildPlatformAdjustBaseLayerHeight (uint8_t input);		// Increase or decrease the number of base layers per layer.
void buildPlatformSetBaseLayerHeight (uint8_t input);
void buildPlatformHome (void);						// Move build platform to lowest position using end switch.
void buildPlatformTop (void);						// Move build platform to top position using end switch.
void buildPlatformMove (uint16_t);					// Move by specific number of steps.
//void buildPlatformSetTarget(int16_t input);				// Set build platform target position.
void buildPlatformComparePosition(uint8_t buildPlatformSpeed);		// Compare current and target position, start stepper if mismatch.
void buildDisableStepper(void);						// Disable stepper.

void buildPlatformLayerUp(void);
void buildPlatformBaseLayerUp(void);



// *****************************************************************************
// Beamer functions. ***********************************************************
// *****************************************************************************

// Beamer variables. ***********************************************************
#define BEAMER_STEPS_PER_STANDARD_LAYER 20			// Number of steps per standard layer. (200 steps for 0.01 mm).
#define BEAMER_MAX_STANDARD_LAYERS 1000				// Maximum number of standard layers per actual layer. 50 --> 0.5 mm.
#define BEAMER_SPEED_MAX 4
#define BEAMER_SPEED_MIN 1
uint8_t beamerSpeed;						// Stepper speed from 1--4
volatile uint8_t beamerCount;					// Step counter.
uint8_t beamerLayer;					// Layer height in multiples of standard layer.
volatile uint16_t beamerPosition;				// Current position in standard layers.
volatile uint16_t beamerTargetPosition;					// Target position in standard layers.
volatile uint8_t beamerHomingFlag;
volatile uint8_t stopFlag;
volatile int16_t beamerTimerCompareValue;
volatile int16_t beamerTimerTargetCompareValue;
uint16_t beamerHiResPosition;
uint16_t beamerLoResPosition;

// Beamer functions. ***********************************************************
uint8_t beamerGetSpeed (void);
void beamerAdjustSpeed (uint8_t input);
void beamerAdjustPosition (uint8_t input);
void beamerHome (void);
void beamerBottom (void);
void beamerSetHiResPosition (void);
void beamerSetLoResPosition (void);
void beamerMoveHiResPosition (void);
void beamerMoveLoResPosition (void);
void beamerDisableStepper(void);
void beamerControl(void);

// *****************************************************************************
// Other functions. ************************************************************
// *****************************************************************************
void disableSteppers(void);
uint8_t printerReady(void);

uint16_t numberOfSlices;
void printerSetNumberOfSlices(uint16_t);
void printerSetSlice(uint16_t);
uint16_t printerGetNumberOfSlices(void);
uint16_t printerGetSlice(void);

uint8_t printerGetState(void);
void printerSetState(uint8_t);
#endif // PRINTERFUNCTIONS_H
