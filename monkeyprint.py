#!/usr/bin/python
# -*- coding: latin-1 -*-

#	Copyright (c) 2015 Paul Bomke
#	Distributed under the GNU GPL v2.
#
#	This file is part of monkeyprint.
#
#	monkeyprint is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	monkeyprint is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You have received a copy of the GNU General Public License
#    along with monkeyprint.  If not, see <http://www.gnu.org/licenses/>.
import sys, getopt # Needed to parse command line arguments.

import monkeyprintModelHandling
import monkeyprintSettings
import monkeyprintGui
import monkeyprintGuiHelper



	
def main(argv):

	if __name__ == "__main__":
		# Test if this file is executed as the main application contrary to being executed as a model from inside another file.
		# Check command line arguments to see if this is a standalone or gui instance.
		# -h: print usage instructions.
		# -f: specify mkp file to open on startup.
		# -p, --print: run print process without gui. You have to pass the file name of an mkp file to print.
		try:
			opts, args = getopt.getopt(argv,"hf:p:",["file=", "print="])
		except getopt.GetoptError:
			usage()
			sys.exit(2)

		# Act according to commandline options.
		if len(opts) != 0:
			for opt, arg in opts:
				if (opt=="-h"):
					# Display help.
					usage()
					sys.exit(2)
				elif (opt in ("-f", "--file")):
					# Run Gui with project file.
					runGui(arg)
				elif (opt in ("-p", "--print")):
					# Run non gui with project file and start print.
					runNoGui(arg)
		else:
			runGui()
	

def runGui(filename=None):

		# Create a debug console text buffer.
		console = monkeyprintGuiHelper.consoleText()

		# Create settings dictionary object for machine and program settings.
		programSettings = monkeyprintSettings.programSettings(console)

		# Create version message.
		console.addLine("You are using Monkeyprint " + str(programSettings['versionMajor'].value) + "." + str(programSettings['versionMinor'].value) + "." + str(programSettings['revision'].value))

		# Update settings from file.	
		programSettings.readFile()

		# Create model collection object.
		# This object contains model data and settings data for each model.
		# Pass program settings.
		modelCollection = monkeyprintModelHandling.modelCollection(programSettings, console)

		# Create gui.
		gui = monkeyprintGui.gui(modelCollection, programSettings, console, filename)

		# Start the gui main loop.
		gui.main()



def runNoGui(filename=None):
	print "Starting without Gui."
	print ("Project file: " + str(filename))
	
	# Create settings dictionary object for machine and program settings.
	programSettings = monkeyprintSettings.programSettings()
	
	# Update settings from file.	
	programSettings.readFile()
	
	
	# Create model collection object.
	# This object contains model data and settings data for each model.
	# Pass program settings.
	modelCollection = monkeyprintModelHandling.modelCollection(programSettings)
	
	# Load project file.
	# TODO: test if file is mkp.
	modelCollection.loadProject(filename)
	

def usage():
	print "\nCommand line option not recognized.\n"
	print "Usage: monkeyprint.py <options>\n"

	print "<no option>:                     Start GUI."
	print "-h:                              Show this help text."
	print "-f / --file <filename.mkp>:      Start GUI and load project file."
	print "-p / --print <filename.mkp>:     Start without GUI and run a print job."


main(sys.argv[1:])
