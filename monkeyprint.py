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


import monkeyprintModelHandling
import monkeyprintSettings
import monkeyprintGui
import monkeyprintGuiHelper


# Test if this file is executed as the main application contrary to being executed as a model from inside another file.
if __name__ == "__main__":

	# Create a debug console text buffer.
	console = monkeyprintGui.consoleText()

	# Create settings dictionary object for machine and program settings.
	programSettings = monkeyprintSettings.programSettings(console)

	# Create version message.
	console.addLine("You are using Monkeyprint " + str(programSettings['versionMajor'].value) + "." + str(programSettings['versionMinor'].value) + "." + str(programSettings['revision'].value))

	# Update settings from file.	
	programSettings.readFile()

	# Create model collection object.
	# This object contains model data and settings data for each model.
	# Pass printer and program settings.
	modelCollection = monkeyprintModelHandling.modelCollection(programSettings, console)

	# Create gui.
	gui = monkeyprintGui.gui(modelCollection, programSettings, console)	

	# Start the gui main loop.
	gui.main()

