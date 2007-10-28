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

import supybot

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Plugin(callbacks.Plugin):
    """This plugin exists to help users manage their plugins.  Use 'plugin
    list' to list the loaded plugins; use 'plugin help' to get this sort of
    help from other plugins; use the 'plugin' command itself to determine what
    plugin a command exists in."""
    def help(self, irc, msg, args, cb):
        """<plugin>

        Returns a useful description of how to use <plugin>, if the plugin has
        one.
        """
        doc = cb.getPluginHelp()
        if doc:
            irc.reply(utils.str.normalizeWhitespace(doc))
        else:
            irc.reply('That plugin is loaded, but has no plugin help.')
    help = wrap(help, ['plugin'])

    def list(self, irc, msg, args):
        """takes no arguments

        Returns a list of the currently loaded plugins.
        """
        L = [cb.name() for cb in irc.callbacks]
        L.sort()
        irc.reply(format('%L', L))
    list = wrap(list)

    def plugin(self, irc, msg, args, command):
        """<command>

        Returns the plugin(s) that <command> is in.
        """
        (maxL, cbs) = irc.findCallbacksForArgs(command)
        L = []
        if maxL == command:
            for cb in cbs:
                L.append(cb.name())
        command = callbacks.formatCommand(command)
        if L:
            if irc.nested:
                irc.reply(format('%L', L))
            else:
                if len(L) > 1:
                    plugin = 'plugins'
                else:
                    plugin = 'plugin'
                irc.reply(format('The %q command is available in the %L %s.',
                                 command, L, plugin))
        else:
            irc.error(format('There is no command %q.', command))
    plugin = wrap(plugin, [many('something')])

    def author(self, irc, msg, args, cb):
        """<plugin>

        Returns the author of <plugin>.  This is the person you should talk to
        if you have ideas, suggestions, or other comments about a given plugin.
        """
        if cb is None:
            irc.error('That plugin does not seem to be loaded.')
            return
        module = cb.classModule
        if hasattr(module, '__author__') and module.__author__:
            irc.reply(str(module.__author__))
        else:
            irc.reply('That plugin doesn\'t have an author that claims it.')
    author = wrap(author, [('plugin')])

    def contributors(self, irc, msg, args, cb, nick):
        """<plugin> [<nick>]

        Replies with a list of people who made contributions to a given plugin.
        If <nick> is specified, that person's specific contributions will
        be listed.  Note: The <nick> is the part inside of the parentheses
        in the people listing.
        """
        def getShortName(authorInfo):
            """
            Take an Authors object, and return only the name and nick values
            in the format 'First Last (nick)'.
            """
            return '%(name)s (%(nick)s)' % authorInfo.__dict__
        def buildContributorsString(longList):
            """
            Take a list of long names and turn it into :
            shortname[, shortname and shortname].
            """
            L = [getShortName(n) for n in longList]
            return format('%L', L)
        def sortAuthors():
            """
            Sort the list of 'long names' based on the number of contributions
            associated with each.
            """
            L = module.__contributors__.items()
            def negativeSecondElement(x):
                return -len(x[1])
            utils.sortBy(negativeSecondElement, L)
            return [t[0] for t in L]
        def buildPeopleString(module):
            """
            Build the list of author + contributors (if any) for the requested
            plugin.
            """
            head = 'The %s plugin' % cb.name()
            author = 'has not been claimed by an author'
            conjunction = 'and'
            contrib = 'has no contributors listed.'
            hasAuthor = False
            hasContribs = False
            if hasattr(module, '__author__'):
                if module.__author__ != supybot.authors.unknown:
                    author = 'was written by %s' % \
                        utils.web.mungeEmail(str(module.__author__))
                    hasAuthor = True
            if hasattr(module, '__contributors__'):
                contribs = sortAuthors()
                if hasAuthor:
                    try:
                        contribs.remove(module.__author__)
                    except ValueError:
                        pass
                if contribs:
                    contrib = format('%s %h contributed to it.',
                                     buildContributorsString(contribs),
                                     len(contribs))
                    hasContribs = True
                elif hasAuthor:
                    contrib = 'has no additional contributors listed.'
            if hasContribs and not hasAuthor:
                conjunction = 'but'
            return ' '.join([head, author, conjunction, contrib])
        def buildPersonString(module):
            """
            Build the list of contributions (if any) for the requested person
            for the requested plugin
            """
            isAuthor = False
            authorInfo = None
            moduleContribs = module.__contributors__.keys()
            lnick = nick.lower()
            for contrib in moduleContribs:
                if contrib.nick.lower() == lnick:
                    authorInfo = contrib
                    break
            authorInfo = authorInfo or getattr(supybot.authors, nick, None)
            if not authorInfo:
                return 'The nick specified (%s) is not a registered ' \
                       'contributor.' % nick
            fullName = utils.web.mungeEmail(str(authorInfo))
            contributions = []
            if hasattr(module, '__contributors__'):
                if authorInfo not in module.__contributors__:
                    return 'The %s plugin does not have \'%s\' listed as a ' \
                           'contributor.' % (cb.name(), nick)
                contributions = module.__contributors__[authorInfo]
            isAuthor = getattr(module, '__author__', False) == authorInfo
            (nonCommands, commands) = utils.iter.partition(lambda s: ' ' in s,
                                                           contributions)
            results = []
            if commands:
                s = 'command'
                if len(commands) > 1:
                    s = utils.str.pluralize(s)
                results.append(format('the %L %s', commands, s))
            if nonCommands:
                results.append(format('the %L', nonCommands))
            if results and isAuthor:
                return format(
                        '%s wrote the %s plugin and also contributed %L.',
                        (fullName, cb.name(), results))
            elif results and not isAuthor:
                return format('%s contributed %L to the %s plugin.',
                              fullName, results, cb.name())
            elif isAuthor and not results:
                return '%s wrote the %s plugin' % (fullName, cb.name())
            # XXX Does this ever actually get reached?
            else:
                return '%s has no listed contributions for the %s plugin.' % \
                    (fullName, cb.name())
        # First we need to check and see if the requested plugin is loaded
        module = cb.classModule
        if not nick:
            irc.reply(buildPeopleString(module))
        else:
            nick = ircutils.toLower(nick)
            irc.reply(buildPersonString(module))
    contributors = wrap(contributors, ['plugin', additional('nick')])

Class = Plugin

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
