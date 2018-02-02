# monkeyprint
A simple tool for pre-processing 3d models and controlling 3d DLP printers.

## What is *monkeyprint* for?
*monkeyprint* came into existence as an open source, will-natively-run-on-linux alternative to [*Creation Workshop*](http://www.envisionlabs.net/home.html).

Thanks to the latest efforts it also runs on Windows although it has not been thoroughly tested yet...

####*monkeyprint* allows you to:

* load one or multiple stl files
* define the position, scale or rotation in the printers build volume
* generate supports with some simple parameters
* hollow the model and create fill structures
* slice the model with a specific layer height
* control a print job on your DLP printer via serial port using G-Code commands

In order for *monkeyprint* to work you need a 3d DLP printer that can receive G-Code commands via serial port and has a projector that is connected to your PC.

## Installation

#### Dependencies
*monkeyprint* is programmed in Python 2.7 and uses the following libraries:

* `PyQt4` for the GUI
* `VTK` for stl processing and slicing
* `openCV` for slice image handling
* `numpy` for slice image handling
* `pyserial` and `zmq` for communication




#### Linux installation

First, install the dependencies.
On Debian-based distros like Ubuntu, you can install the relevant packages using the following command:

`sudo apt-get install git-core python-qt4 libvtk5.8 libopencv-core2.4 python2.7 python-vtk python-numpy python-opencv python-imaging python-serial python-zmq`

Once the dependencies are installed, simply download *monkeyprint* using git:

`git clone git://github.com/robotsinthesun/monkeyprint.git`

This will create a monkeyprint folder in your current location. You can then start *monkeyprint* by running `python monkeyprint.py` from within that folder.

#### Windows installation

Windows users simply download the latest release [here](https://github.com/robotsinthesun/monkeyprint/releases). It's an exe that contains Python and all the necessary libraries. No need to install anything. Yep.


#### Hardware
*monkeyprint* controls your printer using G-Code, so if your printer connects via serial or usb and understands G-Code, you're good to go. Alternatively, you can define custom string commands if your board uses some other language.


## Basic setup

Before starting to use *monkeyprint* with your printer, it is necessary to adjust some of the settings to fit your machine.

Start *monkeyprint*, click *Options* in the top menu and select *Settings*. A dialog will come up.

#### Main settings
In the first tab, make sure to correctly set

* your printers build volume (the size of the area illuminated by your projector and the draw of your Z-axis),
* the serial connection to your printer's controller board. On Linux, this will most likely be `/dev/ttyACM0` or `/dev/ttyUSB0` if you're connecting via USB or `/dev/ttyS0` if using an old-school Sub-D serial connection while on Windows it will be something like `COM0` or `COM1`. The baud rate depends on the board you use and should be in the manual. On most boards it will be `57600` or `115200`.

Adjust the *Max. preview slices* if you wish. In the slicer preview, you will be presented an evently spaced number of preview slices as a subsample of all the slices. The default of 300 should be enough as the slider does not allow for finer control anyways.

Tick the *Multi body slicing* option if your model contains intersecting objects within the same stl file.

#### Projector settings
In the second tab the projector settings will be set up. These are

* your projectors resolution in pixels. This should be self-explaining...
* your projectors "position", i.e. the location of it's top left corner in relation to the whole desktop. For *monkeyprint* to work, your projector should be connected via *HDMI* and should be set to *extend* the desktop. So, if you move your mouse beyond one of the sides of your main screen, it should appear on the projector. If the projector is to the right of your main screen and the latter has a resolution of 1024 x 768 pixels, your projectors position will most likely be `1024, 0`
* an optional serial connection to your projector. Some projectors support the old Sub-D serial connector. If you get yourself a USB-to-serial adapter you will be able to connect that to your PC and power your projector on and off automatically before and after prints. The usual parameters for this connection are set as defaults, simply adjust the serial port setting to the one of your USB-to-serial adapter and it should work.

#### Print process settings
Here, you are able to construct your print process from individual modules. There are two basic types of module: internal modules and G-Code modules. While the internal modules run a distinct function like doing the exposure or simply waiting for a user-defined interval, G-Code modules send a command to your printer via serial connection.

There are three sections during a print process:

* The start section can be used to do all the tasks that bring your printer into its ready-to-print state e.g. powering up the projector, homing the build platform etc.
* The print loop section runs the commands necessary to print a slice, e.g. exposing, moving the build platform, tilting etc. for each of the slices.
* The stop section can be used to do stuff after the print has finished, e.g. moving the build platform into top position, shutting down the projector etc.

The controls below the print process list allow for adding new modules, moving the selected module up or down and deleting a selected module (except for the *Start loop* and *End loop* modules).

* To add a new module, select one from the dropdown and click the *Add* button. The new module will be inserted below the currently selected one.
* The other buttons are pretty much self-explaining I guess...
* To change the name or value of a module, simply double click the name or value in the list and enter a new one. Note: there is no checking for valid G-Code commands, so make sure they make sense and are accepted by your printer.

Here is a list of the available modules:

* *Expose*: exposes the VAT for the exposure time set in the main gui.
* *Wait*: waits for the given interval
* *Projector on / off*: Starts / shuts down your projector using the commands and serial connection specified in the *Projector settings*
* *Start / end loop*: use this to separate start, print loop and stop section
* *Custom G-Code*: sends the given command string to your printer via the serial connection specified in the main settings

## Usage

The *monkeyprint* gui is made to walk you through the pre-processing steps up to starting the print.
The model and it's position is shown in the 3d view on the left while the tabs on the right will guide you through the necessary settings.

First, load a model file by clicking the "Load model" button. Set it's scaling, position and rotation.
The model will automatically fitted to the build volume if the scaling is too large.

Proceed to the "Slicing" tab. Here you can set the overhang angle and define the geometry of the support pillars. You can also define the thickness of the bottom plate.
You can also play with the "Maximum support height" option to eliminate unwanted supports.

In the "Slicing" tab you can set the layer height and walk through the model by using the slider.
The "Print hollow" and "Use fill structures" should be self explaining. Printing hollow reduces the force on the coating of the VAT and helps to elongate the coatings life.

The "Print" tab finally let's you start the print.
Set the exposure values and hit "Print!". Complete the safety check list and there you go: your print is running!
Cancel the print by pressing "Stop". It won't stop immediately but complete the current slice and run the Stop sequence commands.

Note that you can't close the program while a print is running.
