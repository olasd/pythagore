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
        self.name = self.__class__.__name__

    def loadConfig(self):
        """Configuration initialization. Override this if you do not want 
        plaintext config"""
        try:
            import yaml
        except:
            self.config = {}
            return
        
        name = self.__class__.__name__
        try:
            configfile = file("Config" + os.sep + name + ".yml", 'r')
            self.config = yaml.safe_load(configfile)
            configfile.close()
        except:
            print _("Config file for %(module)s not open !") % {'module': name}
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

class PythagoreModuleContainer:
    """This is the class that contains all Pythagore's modules. It emulates
    a dict so that an access to it returns a callback"""
    
    def __init__(self):
        self.modules = {}
        self.moduleinstances = {}

    def register(self, modname):
        """This registers a module"""
        if modname in self.modules:
            self.modules[modname] = reload(self.modules[modname])
            self.unregisterModule(modname)
        else:
            self.modules[modname] = __import__("Modules/%s" % modname)
        
        self.moduleinstances[modname] = getattr(
            self.modules[modname],
            modname,
        )(self);
        
        for i in self.moduleinstances[modname].exports:
            self.keywords[i] = getattr(
                    self.moduleinstances[modname],
                    self.moduleinstances[modname].exports[i]
                    )


