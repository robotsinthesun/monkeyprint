# monkeyprint
A simple tool for pre-processing 3d models and controlling 3d DLP printers.

## What is *monkeyprint* for?
*monkeyprint* came into existance as an open source, will-natively-run-on-linux alternative to [*Creation Workshop*](http://www.envisionlabs.net/home.html).
When a friend built a 3d DLP printer which I was doing the software for, we noticed that there was no nice and simple programm to pre-process a 3d model and control the print job on linux.
Until now...

*monkeyprint* allows you to:
* load an stl file
* define the position, scale or rotation in the printers build volume
* generate supports according to some simple parameters
* hollow out the model and create fill structures
* slice the model with a specific layer height
* control a print job on your DLP printer via serial port

In order for *monkeyprint* to work you need a 3d DLP printer that can receive commands via serial port and whos projector is connected to your PC.

## Dependencies
monkeyprint is programmed in python and uses VTK to visualise and slice 3d models so make sure you have both of them installed. Tested with python 2.7.3 and VTK 5.8.0. There may be issues with VTK versions >= 6 because of syntax changes.

## Usage
Simply run monkeyprint via terminal by changing to the monkeyprint directory and typing ./monkeyprint.python

The *monkeyprint* gui is set up to walk you through the pre-processing steps up to committing the print.
The model and it's position is shown in the 3d view on the left while the tabs on the right will guide you through the necessary settings.

First, load a model file by clicking the "Load model" button. Set it's scaling, position and rotation.
The model will automatically fitted to the build volume if the scaling is too large.

Proceed to the "Slicing" tab. Here you can set the overhang angle and define the geometry of the support pillars. You can also define the thickness of the bottom plate.
You can also play with the "Maximum support height" option to eliminate unwanted supports.

In the "Slicing" tab you can set the layer height and walk through the model by using the slider.
The "Print hollow" and "Use fill structures" should be self explaining. Printing hollow reduces the force on the coating of the VAT and helps to elongate the coatings life.

The "Print" tab finally let's you start the print.
Set the exposure values and hit "Print!". Complete the safety check list and there you go: print is running!
Cancel the print by pressing "Cancel". It won't stop immediately but complete the current slice and move the build platform to the top.

Note that you can't close the program while a print is running.

## Future improvements
* clean up spagetthi code and rebuild gui
* add debug option
* fix issues with VTK versions >= 6
* improve model rotation -> make model rotate around world axes
* implement setup dialog instead of manually having to change settings file
* multiple object print
* implement a customisable print process
