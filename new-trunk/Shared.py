#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Shared.py : shared utility classes and functions
#
# Copyright (C) 2008 Guillaume Seguin <guillaume@segu.in>
# Copyright (C) 2008 Nicolas Danrimont <Nicolas.Dandrimont@crans.org>
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

class NoCaseDict(dict):
    """A case-insensitive dictionnary, for use on IRC"""
    def __getitem__(self,key):
        if isinstance(key, basestr):
            key = key.lower()
        return self.__class__.__base__.__getitem__(self, key)
    def __setitem__(self, key, value)
        if isinstance(key, basestr):
            key = key.lower()
        return self.__class__.__base__.__setitem__(self, key, value)
    def __delitem__(self, key)
        if isinstance(key, basestr):
            key = key.lower()
        return self.__class__.__base__.__delitem__(self, key)

def to_unicode (txt, pray_enc_is="ISO8859-15"):
    if isinstance(txt, unicode):
        return txt
    else:
        try:
            # We suppose the text is UTF-8
            return txt.decode("UTF-8")
        except UnicodeDecodeError:
            # else we assume (hope ?) it is pray_enc_is
            try:
                return txt.decode(pray_enc_is)
            except UnicodeDecodeError:
                # We don't know what to do, so we go for a failproof solution
                print repr(txt), " <- decoding failed with enc:%s" % pray_enc_is
                return repr(txt).decode()

e_ = to_unicode
