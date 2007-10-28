###
# Copyright (c) 2004, Daniel DiPaolo
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

class QuoteGrabsTestCase(ChannelPluginTestCase):
    plugins = ('QuoteGrabs',)
    def testQuoteGrab(self):
        testPrefix = 'foo!bar@baz'
        self.assertError('grab foo')
        # Test join/part/notice (shouldn't grab)
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=testPrefix))
        self.assertError('grab foo')
        self.irc.feedMsg(ircmsgs.part(self.channel, prefix=testPrefix))
        self.assertError('grab foo')
        # Test privmsgs
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                         prefix=testPrefix))
        self.assertNotError('grab foo')
        self.assertResponse('quote foo', '<foo> something')
        # Test actions
        self.irc.feedMsg(ircmsgs.action(self.channel, 'moos',
                                        prefix=testPrefix))
        self.assertNotError('grab foo')
        self.assertResponse('quote foo', '* foo moos')

    def testList(self):
        testPrefix = 'foo!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                         prefix=testPrefix))
        self.assertNotError('grab foo')
        self.assertResponse('quotegrabs list foo', '#1: test')
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'a' * 80,
                                         prefix=testPrefix))
        self.assertNotError('grab foo')
        self.assertResponse('quotegrabs list foo',
                            '#2: %s... and #1: test' %\
                            ('a'*43)) # 50 - length of "#2: ..."

    def testDuplicateGrabs(self):
        testPrefix = 'foo!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                         prefix=testPrefix))
        self.assertNotError('grab foo')
        self.assertNotError('grab foo') # note:NOTanerror,stillwon'tdupe
        self.assertResponse('quotegrabs list foo', '#1: test')

    def testCaseInsensitivity(self):
        testPrefix = 'foo!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                         prefix=testPrefix))
        self.assertNotError('grab FOO')
        self.assertNotError('quote foo')
        self.assertNotError('quote FoO')
        self.assertNotError('quote Foo')
        self.assertNotError('quotegrabs list FOO')
        self.assertNotError('quotegrabs list fOo')

    def testRandom(self):
        testPrefix = 'foo!bar@baz'
        self.assertError('random')
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                         prefix=testPrefix))
        self.assertError('random')  # still none in the db
        self.assertNotError('grab foo')
        self.assertResponse('random', '<foo> test')
        self.assertResponse('random foo', '<foo> test')
        self.assertResponse('random FOO', '<foo> test')

    def testGet(self):
        testPrefix= 'foo!bar@baz'
        self.assertError('quotegrabs get asdf')
        self.assertError('quotegrabs get 1')
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                         prefix=testPrefix))
        self.assertNotError('grab foo')
        self.assertNotError('quotegrabs get 1')

    def testSearch(self):
        testPrefix= 'foo!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                         prefix=testPrefix))
        self.assertError('quotegrabs search test')  # still none in db
        self.assertNotError('grab foo')
        self.assertNotError('quotegrabs search test')


class QuoteGrabsNonChannelTestCase(QuoteGrabsTestCase):
    config = { 'databases.plugins.channelSpecific' : False }


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
