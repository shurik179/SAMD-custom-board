# Custom SAMD board tool   
This directory contains tools to help users create bootloaders and 
arduino hardware packages for custom-made SAMD boards. All you need to
do is filling your board info in a plain text config file (just one!), 
create variant.h and variant.cpp files describign the pins for Arduino IDE, 
and then run a script, which will do (almost) everything else for you - build the 
bootloader, create a board support package following all the  
[Arduino platform specifications](https://arduino.github.io/arduino-cli/0.35/platform-specification/),
even create an index.json file.

Note: the script will not flash the bootloader to the board for you 
- you need to do it separately, e.g. using Microchip Studio 
(formerly Atmel Studio), or Adafruit's DAP library.

Requirements: the following must be installed on your system

* GNU Make 
* Python 3
* Arduinoe IDE, version 1.8 or later
* Adafruit support package for SAMD boards

Detailed instructions will be provided later. 

Currently, the following variants are supported:
* SAMD21:  SAMD21E17A, SAMD21E18A, SAMD21G18A,
* SAMD51/SAME51: SAMD51G19A, SAMD51J19A, SAMD51J20A,SAMD51P20A, SAME51J19A
* Untested: SAME54N20A, SAME54P20A

Deatailed instructions are posted in hackaday: https://hackaday.io/project/193590-arduino-support-for-custom-samd-board

 
