#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Quotes.py : Quotes module for Pythagore bot
#
# Copyright (C) 2008 Nicolas Maître <nox@teepi.net>
# Copyright (C) 2008 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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
#
# Structure de la table :
# | qid | content | author | cid | timestamp | deleted |

from PythagoreModuleMySQL import PythagoreModuleMySQL
import random
from time import time
import sys, MySQLdb

class Quotes(PythagoreModuleMySQL):
    def __init__(self, pythagore):
        PythagoreModuleMySQL.__init__(self, pythagore)
        # export commands (keywords)
        self.exports['addquote'] = "addQuote"
        self.exports['delquote'] = "removeQuote"
        self.exports['lastquote'] = "lastQuote"
        self.exports['quoteinfo'] = "quoteInfo"
        self.exports['quotestatus'] = "quoteStatus"
        self.exports['quoteon'] = "enableChan"
        self.exports['quoteoff'] = "disableChan"
        self.exports['quote'] = "getQuote"
        self.exports['randquote'] = "randomQuote"
        self.exports['findquote'] = "searchQuote"
        self.qtable = self.mysqlConfig['tables']['Quotes']
        self.ctable = self.mysqlConfig['tables']['Channels']
        try:
            self.config['minWordsInQuotes']
        except:
            self.config['minWordsInQuotes'] = 1

    def searchQuoteByQID(self, id):
        """Récupère une quote par son identifiant. 
        La chaîne extra_clauses sert à restreindre la recherche dans le WHERE"""
        # Query sur qtable
        if self.executeQuery("""SELECT * from %s where qid=%%s""" % self.qtable, id):
            line = self.cur.fetchone()
            print line
            if line and not line[5]:
                return line
        return 0

    def verifyNick(self, nick, query_nick):
        if nick == query_nick or nick in self.config['admins']:
            return 1
        return 0

    def addQuote(self, channel, nick, msg):
        """!addquote <quote>
        Ajoute <quote> à la base de données"""
        if msg:
            words=msg.split()
        else:
            self.bot.error(channel, "Erreur ! Précisez la citation à ajouter")
            return
        # s'il y a assez de mots dans la quote
        if len(words) >= int(self.config['minWordsInQuotes']):
            now = time()
            # on cherche le cid du channel
            cid = self.getCIDByName(channel)
            if cid:
                # pour remplir le rang de la quote
                if self.executeQuery(
                        """INSERT INTO `%(qtable)s` (content,author,cid) VALUES (%%s,%%s,%%s)"""
                        % {'qtable': self.qtable},
                        msg, nick, cid):
                    self.dbConn.commit()
                    # et on cherche le qid pour afficher une référence ds la confirmation
                    if self.executeQuery("""SELECT qid FROM `%s` WHERE cid = %%s ORDER BY qid DESC LIMIT 1""" % self.qtable, cid):
                        qid = self.cur.fetchone()[0]
                        self.bot.say(channel, "Citation n°\002%s\002 ajoutée !" % qid)
        else:
            self.bot.error(channel, "Citation trop courte.")

    def removeQuote(self, channel, nick, msg):
        """!delquote <id>
        Supprime de la base de données la citation n° <id>."""
        if msg:
            words = msg.split()
            if len(words) == 1:
                try:
                    id = int(words[0])
                except ValueError:
                    self.bot.error(channel, "L'identifiant doit être un chiffre.")
                    return
                row = self.searchQuoteByQID(id)
                if row:
                    # on vérifie que nick a le droit de l'enlever
                    if self.verifyNick(nick, row[2]):
                        if self.executeQuery("""UPDATE `%s` SET deleted=TRUE WHERE qid=%%s""" % self.qtable, id):
                            self.dbConn.commit()
                            self.bot.say(channel, "Citation n°\002%s\002 effacée" % id)
                    else:
                        self.bot.say(channel, 
                            "Vous n'avez pas le droit d'effacer cette citation !"
                            )
                else:
                    self.bot.say(channel,
                        "La citation n°\002%s\002 n'existe pas !" % id
                        )
            else:
                self.bot.error(channel, "Trop de paramètres.")
        else:
            self.bot.error(channel, "Pas assez de paramètres.")

    def isPublicChannel(self, channel):
        "Vérifie que channel est public"
        if isinstance(channel, str):
            if channel[0] == '#':
                channel = channel[1:]
            query = """SELECT public_quotes from `%s` WHERE name=%%s"""
        else:
            query = """SELECT public_quotes from `%s` WHERE cid=%%s"""
        if self.executeQuery(query % self.ctable, channel):
            row = self.cur.fetchone()
            if row:
                return row[0]
        return

    def isDeleted(self, qid):
        "Vérifie si la quote est 'deleted'"
        if self.executeQuery("""SELECT deleted FROM `%s` WHERE qid=%%s""" % self.qtable, qid):
            row = self.cur.fetchone()
            if row:
                return row[0]
        return

    def getQuote(self, channel, nick, msg):
        """!quote <numéro> 
        Afficher la citation n°<numéro>"""
        if msg:
            words = msg.split()
            if len(words) == 1:
                try:
                    qid = int(words[0])
                except ValueError:
                    self.bot.error(channel, "L'identifiant doit être un nombre.")
                    return
                self.printQuoteToChan(channel, qid)
            else:
                self.bot.error(channel, "Trop de paramètres.")
        else:
            self.randomQuote(channel, nick, msg)

    def randomQuote(self, channel, nick, msg):
        """!randomquote [--all | --channel=#chan | -c=#salon]
        Affiche une citation au hasard, uniquement dans celles de <channel>
        si ce dernier est précisé."""
      
        all = False
        allrows = ()
        chan = channel
        if msg is not None:
            words = msg.split()
            print words
            if words[0] == "--all":
                all = True
            elif words[0].startswith("-c=") or words[0].startswith("--channel="):
                chan = words[0].split("=", 1)[1]
            else:
                self.bot.error(channel, "Arguments incorrects !")
                return
        
        # Si --all
        if all:
            if self.executeQuery("""SELECT qid FROM `%(qtable)s` LEFT JOIN `%(ctable)s` 
                    ON (`%(qtable)s`.cid = `%(ctable)s`.cid) 
                    WHERE `%(ctable)s`.public_quotes = 1 AND `%(qtable)s`.deleted = FALSE"""
                    % {'ctable': self.ctable, 'qtable' : self.qtable}
                    ):
                allrows = self.cur.fetchall()
        # Si chan pas précisé, on utilise le chan courant
        else:
            if channel != chan and not self.isPublicChannel(chan):
                self.bot.say(channel, "Pas de citation trouvée !")
                return
            
            if self.executeQuery("""SELECT qid FROM `%s` WHERE cid=%%s AND deleted=FALSE""" % self.qtable, self.getCIDByName(chan)):
                allrows = self.cur.fetchall()
        
        if allrows:
            self.printQuoteToChan(channel, allrows[random.randint(0,len(allrows)-1)][0])
        else:
            self.bot.say(channel, "Pas de citation trouvée !")

    def searchQuote(self, channel, nick, msg):
        """!findquote [-all | -channel=#salon | -c=#salon] <recherché> 
        Permet de lancer une recherche parmis les quotes contenant le texte <recherché>"""
        pass

    def lastQuote(self, channel, nick, msg):
        """!lastquote [-all]
        Affiche la dernière citation enregistrée sur le salon actuel.
        Si -all est ajouté c'est la dernière citation du réseau qui sera retournée."""
        pass

    def quoteInfo(self, channel, nick, msg):
        """!quoteinfo <numéro> 
        Affiche l'auteur d'une citation ainsi que le salon et la date où la citation a été enregistrée"""
        if msg:
            try:
                id = int(words[0])
            except ValueError:
                self.bot.error(channel, "L'identifiant doit être un nombre.")
                return
        pass

    def enableChan(self, channel, nick, msg):
        """!quoteon 
        Permet d'activer le gestionnaire de citations, seul un opérateur du canal (@) peut l'utiliser"""
        pass

    def disableChan(self, channel, nick, msg):
        """!quoteoff 
        Permet de désactiver le gestionnaire de citations, seul un opérateur du canal (@) peut l'utiliser"""
        pass

    def quoteStatus(self, channel, nick, msg):
        """!quotestatus 
        Indique si le gestionnaire de citations est actif ou non"""
        pass

    def getCIDByName(self, channel_name):
        """Récupère l'identifiant du salon dans la table channels par son nom"""
        
        if channel_name[0] == '#':
            cname = channel_name[1:]
        else:
            cname = channel_name

        if self.executeQuery("""SELECT cid FROM `%s` WHERE name=%%s""" % self.ctable, cname):
            row = self.cur.fetchone()
            if row:
                return int(row[0])
        return

    def getChanNameByCID(self, id):
        "Renvoie le nom du chan de cid <id>"
        
        if self.executeQuery("""SELECT name FROM `%s` WHERE cid=%s""" % self.ctable, id):
            row = self.cur.fetchone()
            if row:
                return row[0]

    def printQuoteToChan(self, channel, qid):
        """Affiche la quote d'identifiant qid dans le salon channel,
        si elle existe et s'il est autorisé à l'afficher."""
        
        if self.executeQuery("""SELECT cid,content FROM `%s` WHERE qid=%%s AND deleted=FALSE""" % self.qtable, qid):
            row = self.cur.fetchone()
            if row:
                print self.getCIDByName(channel), row[0]
                if self.getCIDByName(channel) == int(row[0]) or self.isPublicChannel(row[0]):
                    self.bot.say(
                        channel,
                        "[\002%s\002] %s" % (qid, row[1])
                        )
                    return
        
        self.bot.say(
            channel,
            "La citation n°\002%s\002 n'existe pas." % qid
            )

