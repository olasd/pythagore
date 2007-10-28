###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

from supybot.test import *

import supybot.ircdb as ircdb

class ChannelDBTestCase(ChannelPluginTestCase):
    plugins = ('Seen', 'User')
    def setUp(self):
        ChannelPluginTestCase.setUp(self)
        self.prefix = 'foo!bar@baz'
        self.nick = 'foo'
        self.wildcardTest = ['f*', '*oo', '*foo*', 'f*o*o']
        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                         'register foo bar',
                                         prefix=self.prefix))
        _ = self.irc.takeMsg()
        chancap = ircdb.makeChannelCapability(self.channel, 'op')
        ircdb.users.getUser(self.nick).addCapability(chancap)

    def testNoKeyErrorEscapeFromSeen(self):
        self.assertRegexp('seen asldfkjasdlfkj', '^I have not seen')
        self.assertNotRegexp('seen asldfkjasdlfkj', 'KeyError')

    def testAny(self):
        self.assertRegexp('seen any', 'test has joined')
        self.irc.feedMsg(ircmsgs.mode(self.channel, args=('+o', self.nick),
                                      prefix=self.prefix))
        self.assertRegexp('seen any %s' % self.nick,
                          '^%s was last seen' % self.nick)

    def testSeen(self):
        self.assertNotError('seen last')
        self.assertNotError('list')
        self.assertNotError('seen %s' % self.nick)
        m = self.assertNotError('seen %s' % self.nick.upper())
        self.failUnless(self.nick.upper() in m.args[1])
        self.assertRegexp('seen user %s' % self.nick,
                          '^%s was last seen' % self.nick)
        for wildcard in self.wildcardTest:
            self.assertRegexp('seen %s' % wildcard,
                              '^%s was last seen' % self.nick)
        self.assertRegexp('seen bar*', '^I haven\'t seen anyone matching')

    def testSeenNoUser(self):
        self.assertNotRegexp('seen user alsdkfjalsdfkj', 'KeyError')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

