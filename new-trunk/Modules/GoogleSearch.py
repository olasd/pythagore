#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# GoogleSearch.py : Google Search class for Pythagore bot
#
# Copyright (C) 2007 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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

import re
from urllib import urlopen, quote, unquote

from PythagoreModule import PythagoreModule

class GoogleSearch(PythagoreModule):
    
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.pattern = re.compile(r'"GsearchResultClass":"GwebSearch","unescapedUrl":"(?P<unescapedUrl>.*?)","url":"(?P<url>.*?)","visibleUrl":"(?P<visibleUrl>.*?)","cacheUrl":"(?P<cacheUrl>.*?)","title":"(?P<title>.*?)","titleNoFormatting":"(?P<titleNoFormatting>.*?)","content":"(?P<content>.*?)"}')
        self.exports = { 'google': 'googlequery' }

    def google(self, query='testing'):
        url = 'http://google.com/uds/GwebSearch?callback=GwebSearch.RawCompletion&context=linux&lstkp=0&rsz=large&hl=' + self.config["lang"] + '&sig' + self.config["API_KEY"] + '&q=' + quote(query) + '&key=internal&v=1.0&nocache=7'
        fh = urlopen(url)
        result_string = " ".join(fh.readlines())
        
        # construct response [dict]
        results = []
        
        for m in re.finditer(self.pattern, result_string):
            results.append(m.groupdict())
        return results

    def googlequery(self, channel, nick, msg):
        if msg is None:
            self.bot.error(
                    channel,
                    _("Too few parameters."),
                    )
            return

        result = self.google(self.bot.strip_formatting(msg))
        if len(result) == 0:
            self.bot.say(
                    channel,
                    _("No results for query [%(query)s]") % {'query': msg}
                    )
        else:
            self.bot.say(
                    channel,
                    _("Google results for [%(query)s]:") % {'query': msg}
                    )
            for i in range(min(3,len(result))):
                resultat = "[" + str(i+1) + "] %s (%s)" % (unquote(result[i]['url']), unquote(result[i]['titleNoFormatting']))
                self.bot.say(
                    channel,
                    resultat
                )

