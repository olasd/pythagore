#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# PythagoreModule.py : Module class for Pythagore bot
#
# Copyright (C) 2007 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
#
# This file is part of Pythagore.
#
# Pythagore is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License, version 2, as 
# published by the Free Software Foundation.
#
# Pythagore is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# of FITNESS FOR ANY PARTICULAR PURPOSE. See the GNU General Public
# License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with Pythagore; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import os

class PythagoreModule:
    """This is the class all Pythagore's Modules should subclass
    In fact it is quite empty..."""

    def __init__(self, pythagore):
        """Initialization takes a pythagore argument which is the current bot
        instance"""
        self.exports = {}
        self.bot = pythagore
        self.loadConfig()
		self.module = self.__class__.__name__

    def loadConfig(self):
        """Configuration initialization. Override this if you do not want 
        plaintext config"""
        try:
            import yaml
        except:
            self.config = {}
            return

        name = self.module
        try:
            configfile = file("Config" + os.sep + name + ".yml", 'r')
            self.config = yaml.safe_load(configfile)
            configfile.close()
        except:
            print "Config file for %s not open !" % name
            self.config = {}
            return

    def storeConfig(self):
        """Configuration file save. Should be more or less failproof"""
        try:
            import yaml
        except:
            return

        name = self.__class__.__name__
        try:
            newconfigfile = file("Config" + os.sep + name + ".new.yml", 'w')
            yaml.dump(self.config, newconfigfile, default_flow_style=False)
            os.rename("Config" + os.sep + name + ".new.yml","Config" + os.sep + name + ".yml")
        except:
            return
