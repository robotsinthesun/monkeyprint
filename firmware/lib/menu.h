#ifndef MENU_H
#define MENU_H

// *****************************************************************************
// Function definitions. *******************************************************
// *****************************************************************************
// Evaluate inputs from one button and one rotary encoder.
// If button==1, enter menu or execute function.
// If rotaryEncoder==1 || rotaryEncoder==-1, scroll menu or adjust value.
void menuEvaluateInput(uint8_t button, int8_t rotaryEncoder);
void menuDraw(void);
void menuValueSet(uint16_t input, uint8_t index);
void menuValuesInit (void);
void menuChanged(void);
void menuGoInfoScreen(void);

// Variables.
//char menuValueStrings[][5];

#endif // MENU_H
