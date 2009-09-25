#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Logger.py : Logger Classes
#
# Copyright (C) 2007, 2008 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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

import time, os

from PythagoreModule import PythagoreModule
from Shared import to_unicode

class ChannelLogger:
    def __init__(self, conf, channel):
        self.conf = conf
        self.channel = channel
        self.interval = 60 * 60 * 24 #one day
        date = time.strftime("%Y_%m_%d", time.localtime(time.time()))

        if(not os.path.lexists(conf['logdir'])):
            os.mkdir(self.conf['logdir'])

        assert(os.path.isdir(conf['logdir']))

        self.file = file("%s%s%s_%s.log" %
            (conf['logdir'], os.sep, channel, date), 'a+'
        )
        current_time = int(time.time())
        t = time.localtime(current_time)
        r = (60 * 24 * 24) - ((t[3] * 60 + t[4] ) * 60 + t[5])
        self.rollat = current_time + r

    def roll(self):
        self.file.close()
        date = time.strftime("%Y_%m_%d", time.localtime(time.time()))
        self.file = file("%s%s%s_%s.log" %
            (self.conf['logdir'], os.sep, self.channel, date), 'a+'
        )

    def log(self, message):
        current_time = time.time()
        if current_time >= self.rollat:
            self.roll()
        t = time.localtime(int(current_time))
        timestamp = time.strftime(_("[%H:%M:%S]"), time.localtime(time.time()))
        msg = _("%(timestamp)s %(message)s\n") % {'timestamp': timestamp, 'message': to_unicode(message)}
        self.file.write(msg.encode("UTF-8"))
        self.file.flush()

    def close(self):
        self.file.close()

class Logger(PythagoreModule):
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.conf = pythagore.conf
        self.chans = {}

    def __getitem__(self, key):
        key = key.lower()
        if key not in self.chans:
            return None
        return self.chans[key]

    def log(self, chan, message):
        """Write a message to the file."""
        chan = chan.lower()
        if chan not in self.chans:
            self.chans[chan] = ChannelLogger(
                self.conf, chan
            )
        self[chan].log(message)

    def logall(self, message):
        for chan in self.chans:
            self[chan].log(message)

    def close(self):
        for chan in self.chans:
            self[chan].close()

