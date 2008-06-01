#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Admin.py : Administration module for Pythagore bot
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

import sys, time

from PythagoreModule import PythagoreModule
from twisted.internet import reactor
import sqlalchemy as sa

from Mapped import Channel,Module

class Admin(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.exports['loadmodule'] = "loadModule"
        self.exports['unloadmodule'] = "unloadModule"
        self.exports['die'] = "die"
        self.exports['addchannel'] = "addChannel"
        self.exports['enable'] = "enableModule"
        self.exports['disable'] = "disableModule"

    def loadModule(self, channel, nick, msg):
        if nick in self.config["admins"]:
            self.bot.registerModule(msg)

    def unloadModule(self, channel, nick, msg):
        if nick in self.config["admins"]:
            self.bot.unregisterModule(msg)

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
            newchannel.modules = self.bot.session.query(Module).filter(sa.or_(Module.name=="Admin",Module.name=="Logger")).all()

            self.bot.session.save(newchannel)
            self.bot.session.commit()
            
            # Now we're all set, we can join this channel after appending it to the bot's channel list
            self.bot.channels[newchannel.name] = newchannel
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
                try:
                    module = self.bot.session.query(Module).filter(Module.name==modulename).one()
                except sa.exceptions.InvalidRequestError:
                    self.bot.error(channel, _("No such module %(module)s") % {'module': modulename})
                else:
                    if module not in self.bot.channels[channel].modules:
                        self.bot.say(channel, _("Enabling module %(module)s") % {'module': modulename})
                        self.bot.channels[channel].modules.append(module)
                        self.bot.session.commit()
                    if modulename not in self.bot.modules:
                        self.bot.registerModule(modulename)

    def disableModule(self, channel, nick, msg):
        """Disables the given module in the channel."""
        if self.bot.isOp(channel, nick):
            try:
                modulename = msg.split()[0]
            except AttributeError:
                self.bot.error(channel, _("Too few parameters."))
            else:
                try:
                    if modulename in self.bot.protectedmodules:
                        raise DisableProtectedModule
                    module = self.bot.session.query(Module).filter(Module.name==modulename).one()
                except (sa.exceptions.InvalidRequestError, DisableProtectedModule):
                    self.bot.error(channel, _("No such module %(module)s") % {'module': modulename})
                else:
                    if module in self.bot.channels[channel].modules:
                        self.bot.say(channel, _("Disabling module %(module)s") % {'module': modulename})
                        self.bot.channels[channel].modules.remove(module)
                        self.bot.session.commit()

class DisableProtectedModule(Exception):
    """Exception raised when someone tries to disable a protected module"""
    pass
