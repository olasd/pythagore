#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Uptime.py : Simple Uptime module for Pythagore bot
#
# Copyright © 2007-2009 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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
from time import time

class Uptime(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.exports['uptime'] = 'uptime'
        self.creat_t = time()

    def uptime(self, channel, nick, msg):
        self.bot.say(
            channel,
            _("I've been on %(networkname)s for %(numseconds)s seconds !") % {'networkname': 'teepi', 'numseconds': (time() - self.creat_t)}
        )

