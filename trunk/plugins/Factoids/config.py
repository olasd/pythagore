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

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Factoids', True)


Factoids = conf.registerPlugin('Factoids')
conf.registerChannelValue(Factoids, 'learnSeparator',
    registry.String('as', """Determines what separator must be used in the
    learn command.  Defaults to 'as' -- learn <key> as <value>.  Users might
    feel more comfortable with 'is' or something else, so it's
    configurable."""))
conf.registerChannelValue(Factoids, 'showFactoidIfOnlyOneMatch',
    registry.Boolean(True, """Determines whether the bot will reply with the
    single matching factoid if only one factoid matches when using the search
    command."""))
conf.registerChannelValue(Factoids, 'replyWhenInvalidCommand',
    registry.Boolean(True,  """Determines whether the bot will reply to invalid
    commands by searching for a factoid; basically making the whatis
    unnecessary when you want all factoids for a given key."""))
conf.registerChannelValue(Factoids, 'factoidPrefix',
    registry.StringWithSpaceOnRight('could be ', """Determines the string that
    factoids will be introduced by."""))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
