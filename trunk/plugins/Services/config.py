###
# Copyright (c) 2005, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import supybot.conf as conf
import supybot.ircutils as ircutils
import supybot.registry as registry

def registerNick(nick, password=''):
    p = conf.supybot.plugins.Services.Nickserv.get('password')
    v = p.register(nick, registry.String(password, '', private=True))
    if password:
        v.setValue(password)

def configure(advanced):
    from supybot.questions import expect, anything, something, yn, getpass
    conf.registerPlugin('Services', True)
    nick = something('What is your registered nick?')
    password = something('What is your password for that nick?')
    chanserv = something('What is your ChanServ named?', default='ChanServ')
    nickserv = something('What is your NickServ named?', default='NickServ')
    conf.supybot.plugins.Services.nicks.setValue([nick])
    conf.supybot.plugins.Services.NickServ.setValue(nickserv)
    registerNick(nick, password)
    conf.supybot.plugins.Services.ChanServ.setValue(chanserv)

class ValidNickOrEmptyString(registry.String):
    def setValue(self, v):
        if v and not ircutils.isNick(v):
            raise registry.InvalidRegistryValue, \
                  'Value must be a valid nick or the empty string.'
        registry.String.setValue(self, v)

class ValidNickSet(conf.ValidNicks):
    List = ircutils.IrcSet

Services = conf.registerPlugin('Services')
conf.registerGlobalValue(Services, 'nicks',
    ValidNickSet([], """Determines what nicks the bot will use with
    services."""))

class Networks(registry.SpaceSeparatedSetOfStrings):
    List = ircutils.IrcSet

conf.registerGlobalValue(Services, 'disabledNetworks',
    Networks(['QuakeNet'], """Determines what networks this plugin will be
    disabled on."""))

conf.registerGlobalValue(Services, 'noJoinsUntilIdentified',
    registry.Boolean(False, """Determines whether the bot will not join any
    channels until it is identified.  This may be useful, for instances, if
    you have a vhost that isn't set until you're identified, or if you're
    joining +r channels that won't allow you to join unless you identify."""))
conf.registerGlobalValue(Services, 'ghostDelay',
    registry.PositiveInteger(60, """Determines how many seconds the bot will
    wait between successive GHOST attempts."""))
conf.registerGlobalValue(Services, 'NickServ',
    ValidNickOrEmptyString('', """Determines what nick the 'NickServ' service
    has."""))
conf.registerGroup(Services.NickServ, 'password',
    registry.String('', """Determines what password the bot will use with
    NickServ.""", private=True))
conf.registerGlobalValue(Services, 'ChanServ',
    ValidNickOrEmptyString('', """Determines what nick the 'ChanServ' service
    has."""))
conf.registerChannelValue(Services.ChanServ, 'password',
    registry.String('', """Determines what password the bot will use with
    ChanServ.""", private=True))
conf.registerChannelValue(Services.ChanServ, 'op',
    registry.Boolean(False, """Determines whether the bot will request to get
    opped by the ChanServ when it joins the channel."""))
conf.registerChannelValue(Services.ChanServ, 'halfop',
    registry.Boolean(False, """Determines whether the bot will request to get
    half-opped by the ChanServ when it joins the channel."""))
conf.registerChannelValue(Services.ChanServ, 'voice',
    registry.Boolean(False, """Determines whether the bot will request to get
    voiced by the ChanServ when it joins the channel."""))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
