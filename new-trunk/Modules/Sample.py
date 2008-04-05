#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Filename.py : module for Pythagore bot
#
# Copyright (C) 2008 Author <Author@example.org>
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
# from PythagoreModuleMySQL import PythagoreModuleMySQL
import sys

class Filename(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.exports['firstmethod'] = "firstMethod"
        self.exports['secondmethod'] = "secondMethod"

    # all methods receive the same parameters : channel, nick, msg
    def firstMethod(self, channel, nick, msg):
        #code here

    def secondMethod(self, channel, nick, msg):
        #here too

