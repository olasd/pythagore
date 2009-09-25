#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Admin.py : Administration module for Pythagore bot
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

from __future__ import with_statement

import sys, time

from PythagoreModule import PythagoreModule
from twisted.internet import reactor
import sqlalchemy as sa
import sqlalchemy.orm as sao

from Mapped import Channel, Module
from Shared import SASession

class Admin(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.exports['loadmodule'] = "loadModule"
        self.exports['unloadmodule'] = "unloadModule"
        self.exports['die'] = "die"
        self.exports['addchannel'] = "addChannel"
        self.exports['enablechannel'] = "enableChannel"
        self.exports['enable'] = "enableModule"
        self.exports['disable'] = "disableModule"

    def loadModule(self, channel, nick, msg):
        if nick in self.config["admins"]:
            self.bot.modules.register(msg)

    def unloadModule(self, channel, nick, msg):
        if nick in self.config["admins"]:
            self.bot.modules.unregister(msg)

    def die(self, channel, nick, msg):
        if nick in self.config["admins"]:
            reactor.stop()

    def addChannel(self, channel, nick, msg):
        """Adds the channel to the bot database. The channel's encoding is given by a second argument."""
        if nick in self.config["admins"]:
            args = msg.split()

            # We create a new channel whose name is the first argument
            newchannel = Channel(args[0].encode('UTF-8'))
            try:
                newchannel.encoding = args[1]
            except IndexError:
                # No encoding was given, we keep the default.
                pass

            # We enable the Admin and Logger modules for this channel
            with SASession(self.bot) as sess:
                sess.add(newchannel)
                newchannel.modules = sess.query(Module).filter(sa.or_(Module.name=="Admin",
                                                                      Module.name=="Logger")).all()
                
            self.joinChannel(newchannel)

    def enableChannel(self, channel, nick, msg):
        """Enable the channel in the bot's database. Loads all necessary modules."""
        if nick in self.config["admins"]:
            args = msg.split()

            try:
                with SASession(self.bot) as sess:
                    newchannel = sess.query(Channel).filter(Channel.name==args[0].encode('UTF-8')).one()
                    if not newchannel.enabled:
                        newchannel.enabled = True
                        newchannel.modules = list(set(newchannel.modules) |
                                                  set(sess.query(Module).filter(sa.or_(Module.name=="Admin",
                                                                                   Module.name=="Logger")).all()))
            except sao.exc.NoResultFound:
                self.bot.say(channel, _("%(channel)s not found!") % {"channel": args[0]})
            else:
                self.joinChannel(args[0])
            

    def joinChannel(self, newchannel):
        """This makes the bot join a channel"""
        if not isinstance(newchannel, Channel):
            with SASession(self.bot) as sess:
                newchannel = sess.query(Channel).filter(Channel.name==newchannel).one()

                # Now we're all set, we can join this channel
                print _("[%(timestamp)s] joining %(channel)s") % {'timestamp': time.time() ,'channel': newchannel.name}
                self.bot.join(newchannel.name)

    def enableModule(self, channel, nick, msg):
        """Enables the given module in the channel."""
        if self.bot.isOp(channel, nick):
            try:
                modulename = msg.split()[0]
            except AttributeError:
                self.bot.error(channel, _("Too few parameters."))
            else:
                chan, sess = self.bot.channels(channel, True)
                try:
                    module = sess.query(Module).filter(Module.name == modulename).one()
                except sa.exceptions.SQLAlchemyError:
                    self.bot.error(channel, _("No such module %(module)s") % {'module': modulename})
                    sess.rollback()
                    sess.close()
                else:
                    if module not in chan.modules:
                        self.bot.say(channel, _("Enabling module %(module)s") % {'module': modulename})
                        chan.modules.append(module)
                        sess.commit()
                    if modulename not in self.bot.modules:
                        self.bot.modules.register(modulename)
                sess.close()
        else:
            print "badabrotch"

    def disableModule(self, channel, nick, msg):
        """Disables the given module in the channel."""
        if self.bot.isOp(channel, nick):
            try:
                modulename = msg.split()[0]
            except AttributeError:
                self.bot.error(channel, _("Too few parameters."))
            else:
                chan, sess = self.bot.channels(channel, True)
                try:
                    if modulename in self.bot.modules.protected:
                        raise DisableProtectedModule
                    module = sess.query(Module).filter(Module.name==modulename).one()
                except (sa.exceptions.SQLAlchemyError, DisableProtectedModule):
                    self.bot.error(channel, _("No such module %(module)s") % {'module': modulename})
                    sess.rollback()
                    sess.close()
                else:
                    if module in chan.modules:
                        self.bot.say(channel, _("Disabling module %(module)s") % {'module': modulename})
                        chan.modules.remove(module)
                        sess.commit()
                sess.close()

class DisableProtectedModule(Exception):
    """Exception raised when someone tries to disable a protected module"""
    pass
