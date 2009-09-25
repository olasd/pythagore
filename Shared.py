#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Shared.py : shared utility classes and functions
#
# Copyright © 2008 Guillaume Seguin <guillaume@segu.in>
# Copyright © 2008, 2009 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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
"""Shared.py: shared utilities"""

import sqlalchemy as sa

class NoCaseDict(dict):
    """A case-insensitive dictionnary, for use on IRC"""
    def __getitem__(self, key):
        if isinstance(key, basestring):
            key = key.lower()
        return super(NoCaseDict, self).__getitem__(key)
    def __setitem__(self, key, value):
        if isinstance(key, basestring):
            key = key.lower()
        return super(NoCaseDict, self).__setitem__(key, value)
    def __delitem__(self, key):
        if isinstance(key, basestring):
            key = key.lower()
        return super(NoCaseDict, self).__delitem__(key)
    def __contains__(self, key):
        if isinstance(key, basestring):
            key = key.lower()
        return super(NoCaseDict, self).__contains__(key)

class SASession(object):
    """Context Manager for clean SQLAlchemy session handling."""

    def __init__(self, pythagore):
        self.sess = pythagore.sessionmaker()
    def __enter__(self):
        return self.sess
    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            self.sess.commit()
            self.sess.close()
        else:
            if isinstance(exc_type, sa.exceptions.SQLAlchemyError):
                self.sess.rollback()
                self.sess.close()
                
    

def to_unicode(txt, should_be="UTF-8", may_be=("ISO8859-15",)):
    """Convert the txt object to a unicode object"""
    if hasattr(txt, "__unicode__"):
        return unicode(txt)
    if isinstance(txt, unicode):
        return txt
    else:
        try:
            # We suppose the text is in the "should_be" encoding
            return txt.decode(should_be)
        except UnicodeDecodeError:
            # else we try all encodings in "may_be"
            for encoding in may_be:
                try:
                    return txt.decode(encoding)
                except UnicodeDecodeError:
                    continue
            else:
                # We don't know what to do, so we go for a failproof solution
                print ("%r <- decoding failed with encodings "
                       "%s and %s") % txt, should_be, ','.join(may_be)
                return repr(txt).decode()
