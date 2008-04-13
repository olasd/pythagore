#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# ShortURL.py : URL shorting module for Pythagore bot
#
# Copyright (C) 2008 Nicolas Maître <nox@teepi.net>
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
import sys, urllib

class ShortURL(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.exports['short'] = "shorturl"

    def tiny(self, longurl):
        url = "http://tinyurl.com/api-create.php?url=%s" % longurl
        print url
        reader = urllib.urlopen(url)
        tinyurl = reader.read()
        reader.close()
        if not tinyurl:
            return longurl
        return tinyurl

    def shorturl(self, channel, nick, msg):
        if msg is not None:
            if len(msg.split()) == 1:
                if "http://" == msg[:7]:
                    self.bot.say(channel, "[\002URL\002] "+self.tiny(msg))
                    return
        self.bot.error(channel, "!short doit être suivi d'une URL à réduire.")
