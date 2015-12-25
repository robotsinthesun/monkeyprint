#
#             LUFA Library
#     Copyright (C) Dean Camera, 2013.
#
#  dean [at] fourwalledcubicle [dot] com
#           www.lufa-lib.org
#
# --------------------------------------
#         LUFA Project Makefile.
# --------------------------------------

# Run "make help" for target help.
# atmega32u4, atxmega32a4u, atxmega128a4u
MCU          = atmega32u4
# AVR8 for atmegas, XMEGA for atxmegas
ARCH         = AVR8
BOARD        = NONE
F_CPU        = 16000000
F_USB        = $(F_CPU)
OPTIMIZATION = s
TARGET       = main
SRC          = $(TARGET).c hardware.c $(LIBS)/uart.c $(LIBS)/uartSerial.c $(LIBS)/printerCommands.c $(LIBS)/lcd.c $(LIBS)/printerFunctions.c $(LIBS)/menu.c $(LIBS)/button.c $(LIBS)/rotaryEncoder.c $(LIBS)/virtualSerial.c $(LIBS)/Descriptors.c $(LUFA_SRC_USB) $(LUFA_SRC_USBCLASS)
LIBS	     = ./lib
LUFA_PATH    = $(LIBS)/lufa-master/LUFA
CC_FLAGS     = -DUSE_LUFA_CONFIG_HEADER -IConfig/
LD_FLAGS     =

# Default target
all:

# Include LUFA build script makefiles
include $(LUFA_PATH)/Build/lufa_core.mk
include $(LUFA_PATH)/Build/lufa_sources.mk
include $(LUFA_PATH)/Build/lufa_build.mk
include $(LUFA_PATH)/Build/lufa_cppcheck.mk
include $(LUFA_PATH)/Build/lufa_doxygen.mk
include $(LUFA_PATH)/Build/lufa_dfu.mk
include $(LUFA_PATH)/Build/lufa_hid.mk
include $(LUFA_PATH)/Build/lufa_avrdude.mk
include $(LUFA_PATH)/Build/lufa_atprogram.mk

#******************************************************************************#
#************************** Programs and commands. ****************************#
#******************************************************************************#
AVRDUDE = avrdude

#******************************************************************************#
#******* Programming support using avrdude. Settings and variables. ***********#
#******************************************************************************#
# Second options are for AVR109 bootloader.

# Programming hardware.
#AVRDUDE_PROGRAMMER = avrisp2
AVRDUDE_PROGRAMMER = avr109 -D
# Note: D option prevents erase in order to save bootloader from being overwritten.

# Programmer port.
#AVRDUDE_PORT = usb
AVRDUDE_PORT = /dev/ttyACM0

# Programming target.
AVRDUDE_WRITE_FLASH = -U flash:w:$(TARGET).hex
#AVRDUDE_WRITE_EEPROM = -U eeprom:w:$(TARGET).eep

# Increase verbosity level.
#AVRDUDE_VERBOSE = -v -v

AVRDUDE_FLAGS = -p $(MCU) -P $(AVRDUDE_PORT) -c $(AVRDUDE_PROGRAMMER)
AVRDUDE_FLAGS += $(AVRDUDE_VERBOSE)

# Program the device.  
program:	$(TARGET).hex $(TARGET).eep
#	python bootloaderKick.py $(AVRDUDE_PORT)
#	sleep 2
	$(AVRDUDE) $(AVRDUDE_FLAGS) $(AVRDUDE_WRITE_FLASH) $(AVRDUDE_WRITE_EEPROM)
