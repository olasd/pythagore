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
from random import randint
from time import time
import sys, MySQLdb, getopt

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

    def searchQuoteByQID(self, id, extra_clauses=''):
        """Récupère une quote par son identifiant. 
        La chaîne extra_clauses sert à restreindre la recherche dans le WHERE"""
		# Query sur qtable
        if extra_clauses:
            query = "SELECT * from %(table)s where qid=%(id) and %(where)s" % {'table': self.qtable, 'id': id, 'where': extra_clauses}
        else:
            query = "SELECT * from %(table)s where qid=%(id)s" % {'table': self.qtable, 'id': id}
        if self.executeQuery(query):
            line = self.cur.fetchone()
            if line and not line[5]:
                return line
        return 0

    def verifyNick(self, nick, row):
        if nick == row[2] or nick in self.config['admins']:
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
                query = "INSERT into %(table)s (content,author,cid,timestamp,deleted) VALUES('%(content)s','%(author)s',%(cid)s,%(now)s,%(del)s)" % {'table':self.qtable,'content':msg, 'author':nick, 'cid':cid,'now':now,'del':0}
                if self.executeQuery(query):
                    self.dbConn.commit()
                    # et on cherche le qid pour afficher une référence ds la confirmation
                    query = "SELECT COUNT(*) from %s" % self.qtable
                    if self.executeQuery(query):
                        qid = self.cur.fetchone()[0]
                        self.bot.say(channel, "Citation ajoutée (n°%s)" % qid)
        else:
            self.bot.error(channel, "Erreur ! Citation trop courte")

    def removeQuote(self, channel, nick, msg):
        """!delquote <id>
        Supprime de la base de données la citation n° <id>."""
        if msg:
            words = msg.split()
            if len(words) == 1:
                try:
                    id = int(words[0])
                except ValueError:
                    self.bot.error(channel, "Erreur ! L'identifiant doit être un chiffre.")
                    return
                row = self.searchQuoteByQID(id)
                if row:
                    # on vérifie que nick a le droit de l'enlever
                    if self.verifyNick(nick, row):
                        query = "UPDATE %(table)s set deleted=TRUE where qid=%(id)s" % {'table': self.qtable, 'id': id}
                        if self.executeQuery(query):
                            self.dbConn.commit()
                            self.bot.say(channel, "Citation n°%s effacée de la base" % id)
                    else:
                        self.bot.error(channel, 
                            "Erreur ! Vous n'avez pas le droit d'effacer cette citation"
                            )
                else:
                    self.bot.error(channel,
                        "Erreur ! La citation n'%s n'existe pas dans la base de données" % id
                        )
            else:
                self.bot.error(channel, "Erreur ! Trop de paramètres")
        else:
            self.bot.error(channel, "Erreur ! Pas assez de paramètres")

    def isPublicChannel(self, channel, byCID=False):
        "Vérifie que channel est public"
        if byCID:
            query = "SELECT * from %(table)s WHERE cid='%(cid)s'" % {'table':self.ctable, 'cid': channel}
        else:
            query = "SELECT * from %(table)s WHERE name='%(chan)s'" % {'table':self.ctable, 'chan':channel}
        if self.executeQuery(query):
            row = self.cur.fetchone()
            if row:
                return row[2]
        return

    def isDeleted(self, qid):
        "Vérifie si la quote est 'deleted'"
        query = "SELECT * from %(table)s where qid=%(qid)s" % {'table':self.qtable, 'qid':qid}
        if self.executeQuery(query):
            row = self.cur.fetchone()
            if row:
                return row[5]
        return

    def getQuote(self, channel, nick, msg):
        """!quote <numéro> 
        Afficher la citation n°<numéro>"""
        if msg:
            words = msg.split()
            try:
                id = int(words[0])
            except ValueError:
                self.bot.error(channel, "Erreur ! L'identifiant doit être un chiffre.")
                return
            if len(words) == 1:
                row = self.searchQuoteByQID(msg)
                if row:
                    cid = row[3]
                    if self.isPublicChannel(cid,byCID=True) or (channel == self.getChanNameByCID(cid)):
                        self.bot.say(channel, "Citation n°%s : %s" % (row[0],row[1]))
                else:
                    self.bot.say(channel, "Pas de citation n°%s" % words[0])
            else:
                self.bot.error(channel, "Erreur ! Trop de paramètres")
        else:
			self.randomQuote(channel, nick, msg)

    def findGoodRandom(self, channel, allrows, chan=''):
        """Cherche dans la db une quote qui rrespond aux restrictions
        (quote pas deleted, pas privée (sauf si channel courant)""" 
        found = 0
        i = 1
        while not found:
            randomrow = allrows[randint(1,len(allrows)-1)]
            cid = randomrow[3] 
            found = ((self.isPublicChannel(cid,True) or self.getChanNameByCID(cid) == channel)) and not self.isDeleted(randomrow[0])
            i = i+1
            # on considère que si il y a 50 essais infructeux
            # il n'existe pas de citation qui rencontre les critères
            if i > 50:
                self.bot.say(channel, "Pas de citation trouvée")
                return
        message = "Citation de %s au hasard (n°%s) : %s" % (chan,randomrow[0],randomrow[1])
        self.bot.say(channel, message)

    def randomQuote(self, channel, nick, msg):
        """!randomquote [-all | -channel=#chan | -c=#salon]
        Affiche une citation au hasard, uniquement dans celles de <channel>
        si ce dernier est précisé."""
        # FIXME foirage au niveau des arguments (aucune prise en compte)
        try:
            chan = self.getArgsFromCmd(msg)
        except getopt.GetoptError:
            self.bot.error(channel, "Erreur ! Arguments incorrects")
            return
        # Si le chan est précisé, on vérifie d'abord qu'on peut diffuser la quote
        if chan:
            if chan != "all":
                if not self.isPublicChannel(chan) and channel != chan:
                    self.bot.say(channel, "Vous n'avez pas le droit de consulter les citations de ce channel")
                    return
            # Si --all
            else:
                query = "SELECT * from %s" % self.qtable
                if self.executeQuery(query):
                    allrows = self.cur.fetchall()
                    if allrows:
                        self.findGoodRandom(channel,allrows)
                        return
        # Si chan pas précisé, on utilise le chan courant
        else:
            chan = channel
		# on cherche toutes les citations pour le chan (précisé ou courant)
        query = "SELECT * from %s WHERE cid='%s'" % (self.qtable, self.getCIDByName(chan))
        if self.executeQuery(query):
			# Si citations trouvées, on en affiche une au hasard
            allrows = self.cur.fetchall()
            if allrows:
                self.findGoodRandom(channel,allrows,chan=chan)
            else:
                self.bot.say(channel, "Pas de citation pour le channel %s" % chan)

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
                self.bot.error(channel, "Erreur ! L'identifiant doit être un chiffre.")
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
        query = "SELECT * from %(table)s WHERE name='%(chan)s'" % {'table':self.ctable, 'chan':channel_name}
        if self.executeQuery(query):
            row = self.cur.fetchone()
            if row:
                return row[0]
        return

    def getChanNameByCID(self, id):
        "Renvoie le nom du chan de cid <id>"
        query = "SELECT * from %(table)s WHERE cid='%(cid)s'" % {'table':self.ctable, 'cid': id}
        if self.executeQuery(query):
            row = self.cur.fetchone()
            if row:
                return row[1]

    def getArgsFromCmd(self, cmdline):
        """Retourne 0 si aucun channel n'est précisé dans cmdline,
        Retourne le channel sinon"""
        opts, args = getopt.getopt(cmdline, "ac:", ["all", "channel="])
        chan = 0
        for opt, arg in opts:
            if opt in ("-a", "-all"):
                chan = "all"
            elif opt in ("-c", "--channel"):
                chan = arg
                if chan[0] != "#":
                    chan = "#"+chan
        return chan

