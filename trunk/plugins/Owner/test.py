###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import supybot.conf as conf
import supybot.plugin as plugin

class OwnerTestCase(PluginTestCase):
    # Defaults, but hey, I'm cool.
    plugins = ('Owner', 'Config', 'Misc', 'Admin')
    def testHelpLog(self):
        self.assertHelp('help log')

    def testSrcAmbiguity(self):
        self.assertError('capability add foo bar')

    def testIrcquote(self):
        self.assertResponse('ircquote PRIVMSG %s :foo' % self.irc.nick, 'foo')

    def testFlush(self):
        self.assertNotError('flush')

    def testUpkeep(self):
        self.assertNotError('upkeep')

    def testLoad(self):
        self.assertError('load Owner')
        self.assertError('load owner')
        self.assertNotError('load Channel')
        self.assertNotError('list Owner')

    def testReload(self):
        self.assertError('reload Channel')
        self.assertNotError('load Channel')
        self.assertNotError('reload Channel')
        self.assertNotError('reload Channel')

    def testUnload(self):
        self.assertError('unload Foobar')
        self.assertNotError('load Channel')
        self.assertNotError('unload Channel')
        self.assertError('unload Channel')
        self.assertNotError('load Channel')
        self.assertNotError('unload CHANNEL')

    def testDisable(self):
        self.assertError('disable enable')
        self.assertError('disable identify')

    def testEnable(self):
        self.assertError('enable enable')

    def testEnableIsCaseInsensitive(self):
        self.assertNotError('disable Foo')
        self.assertNotError('enable foo')

    def testRename(self):
        self.assertError('rename Admin ignore IGNORE')
        self.assertError('rename Admin ignore ig-nore')
        self.assertNotError('rename Admin "capability remove" rmcap')
        self.assertNotRegexp('list Admin', 'capability remove')
        self.assertRegexp('list Admin', 'rmcap')
        self.assertNotError('reload Admin')
        self.assertNotRegexp('list Admin', 'capability remove')
        self.assertRegexp('list Admin', 'rmcap')
        self.assertNotError('unrename Admin')
        self.assertRegexp('list Admin', 'capability remove')
        self.assertNotRegexp('list Admin', 'rmcap')

    def testDefaultPluginErrorsWhenCommandNotInPlugin(self):
        self.assertError('defaultplugin foobar owner')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
