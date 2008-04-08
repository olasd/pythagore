#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# PythagoreModuleMySQL.py : MySQL-based module class for Pythagore 
#
# You should subclass this if you have to connect to a MySQL database
# in a module class for Pythagore
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

from PythagoreModule import PythagoreModule
import yaml
import os, MySQLdb

class PythagoreModuleMySQL(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.loadMySQLConfig()
        self.connectToDB()
        self.cur = self.dbConn.cursor()

    def loadMySQLConfig(self):
        configfile = file("Config" + os.sep + "MySQL.yml", 'r')
        self.mysqlConfig = yaml.safe_load(configfile)
        configfile.close()

    def connectToDB(self):
        try:
            self.dbConn = MySQLdb.connect(
                    db = self.mysqlConfig["dbname"],
                    user = self.mysqlConfig["user"],
                    passwd = self.mysqlConfig["passwd"],
                    host = self.mysqlConfig["host"],
                    port = self.mysqlConfig["port"],
                    )
        except Exception, err:
            print "Connection error to MySQL database : %s" % err

    def executeQuery(self, query, *args):
        print "query : `%s` with args `%s`" % (query, repr(args))
        try:
            self.cur.execute(query, args)
        except Exception, err:
            print "Invalid query : `%s` with args `%s` \nError : %s" % (query, repr(args), err)
            return 0
        else:
            return 1


