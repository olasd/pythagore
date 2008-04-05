#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Quotes.py : Quotes module for Pythagore bot
#
# Copyright (C) 2008 Nicolas Maître <nox@teepi.net>
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
# | id | nick | channel | time | quote |

from PythagoreModuleMySQL import PythagoreModuleMySQL
from random import randint
import sys, MySQLdb

class Quotes(PythagoreModuleMySQL):
    def __init__(self, pythagore):
        PythagoreModuleMySQL.__init__(self, pythagore)
        self.exports['addquote'] = "addQuote"
        self.exports['remquote'], self.exports['delquote'] = "removeQuote","removeQuote"
		self.exports['randquote'] = "randomQuote"
		self.table = self.mysqlConfig['tables']['Quotes']
	
	def searchdbByID(self, id):
		query = "SELECT id from %s where id=%s"
		if self.executeQuery(query):
			line = self.cur.fetchone()
			if line:
				return line
		return 0

	def verifyNick(self, nick, row):
		if nick == row[1] or nick in self.config['admins']:
			return 1
		return 0

    def addQuote(self, channel, nick, msg):
		"""!addquote <quote>
		Ajoute <quote> à la base de données"""
		t = time.time()
		now = time.localtime(t)
		# to be continued

    def removeQuote(self, channel, nick, msg):
		"""!remquote <id>
		Supprime de la base de données la citation n° <id>."""
		words = msg.split()
		if len(words) < 1:
			error(channel, "Erreur ! Pas assez de paramètres")
		elif len(words) == 1:
			id = int(words[0])
			row =  self.searchdbByID(id)
			if row:
				if self.verifyNick(nick, row):
					query = "ALTER TABLE %s DROP INDEX %s" % (self.table,id)
					if self.executeQuery(query):
						self.dbConn.commit()
				else:
					error(channel, 
						"Erreur ! Vous n'avez pas le droit d'effacer 
						cette citation"
						)
			else:
				error(channel,
						"Erreur ! La citation n°%s n'existe pas dans
						la base de données" % id
					)
		else:
			error(channel, "Erreur ! Trop de paramètres")
	
	def randomQuote(self, channel, nick, msg):
		"""!randomquote [<channel>]
		Affiche une citation au hasard, uniquement dans celles de <channel>
		si ce dernier est précisé."""
		
		searchWithChan = 0
		words = msg.split()
		if len(words) > 1:
			err(channel, "Erreur ! Trop de paramètres")
		else:
			if len(words) == 1:
				chan = words[0]
				if chan[0] == "#":
					searchWithChan = 1
					query = "SELECT * from %s WHERE channel='%s'" % (self.table,chan)
			else:
				query = "SELECT * from %s" % self.table
			if self.executeQuery(query):
				if self.cur.fetchall():
					randomrow = self.cur[randint(0,len(self.cur))]
					say(channel, "Citation n°%s : %s" % (randomrow[0],randomrow[4]))
				else:
					if searchWithChan:
						say(channel, "Pas de citation pour le channel %s" % chan)
					else:
						say(channel, "Pas de citation dans la base de données")

