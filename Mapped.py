#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Mapped.py : Pythagore Bot common mapped objects
#
# Copyright © 2009 Nicolas Dandrimont <nicolas@dandrimont.eu>
# Copyright © 2008 Nicolas Maître <nox@teepi.net>
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

class Channel(object):
    """An object representing a channel, to be mapped via SQLAlchemy"""

    def __init__(self, name, modules=[], encoding="ISO8859-15", public=True, enabled=True):
        self.name = name
        self.enabledmodules = modules
        self.encoding = encoding
        self.publicquotes = public
        self.usermodes = {}
        self.enabled = enabled
        self.feeds = []
    def __str__(self):
        return self.name.encode("utf-8")
    def __unicode__(self):
        return self.name

class Module(object):
    """An object representing a module, to be mapped via SQLAlchemy"""

    def __init__(self, name):
        self.name = name

class Quote(object):
    """An object representing a quote, to be mapped via SQLAlchemy"""

    def __init__(self, author, content, channel):
        self.author = author
        self.content = content
        self.cid = channel

class Feed(object):
    """An object representing a RSS feed, to be mapped via SQLAlchemy"""

    def __init__(self, name, url):
        self.name = name
        self.url = url
