#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Admin.py : Administration module for Pythagore bot
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

from PythagoreModule import PythagoreModule
from twisted.internet import reactor
import sys

class Admin(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.exports['loadmodule'] = "loadModule"
        self.exports['unloadmodule'] = "unloadModule"
        self.exports['die'] = "die"

    def loadModule(self, channel, nick, msg):
        if nick in self.config["admins"]:
            self.bot.registerModule(msg)

    def unloadModule(self, channel, nick, msg):
        if nick in self.config["admins"]:
            self.bot.unregisterModule(msg)

    def die(self, channel, nick, msg):
        if nick in self.config["admins"]:
            reactor.stop()

