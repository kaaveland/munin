"""
Loadable.Loadable subclass
"""

# This file is part of Munin.

# Munin is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Munin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Munin; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# This work is Copyright (C)2006 by Andreas Jacobsen 
# Individual portions may be copyright by individual contributors, and
# are included in this collective work with permission of the copyright 
# owners.

# This module doesn't have anything alliance specific as far as I can tell.
# qebab, 24/6/08.

class exile(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,1)
        self.commandre=re.compile(r"^"+self.__class__.__name__+"(.*)")
        self.paramre=re.compile(r"^(.*)")
        self.usage=self.__class__.__name__ + ""
	self.helptext=None

    def execute(self,nick,username,host,target,prefix,command,user,access):
        m=self.commandre.search(command)
        if not m:
            return 0

        if access < self.level:
            self.client.reply(prefix,nick,target,"You do not have enough access to use this command")
            return 0

        m=self.paramre.search(m.group(1))
        if not m:
            self.client.reply(prefix,nick,target,"Usage: %s" % (self.usage,))
            return 0

        # assign param variables 
	

	
        # do stuff here
	query = "SELECT planets,count(*) AS count FROM " 
	query+= " (SELECT  x AS x,y AS y,count(*) AS planets from planet_dump"
	query+= " WHERE tick = (SELECT max_tick()) AND x < 200"
	query+= " GROUP BY x,y ORDER BY count(*) DESC) AS foo"
	query+= " GROUP BY planets ORDER BY planets ASC"

	reply=""
	self.cursor.execute(query)
	if self.cursor.rowcount<1:
	    reply="There is no spoon"
	else:
	    res=self.cursor.dictfetchall()
	    gals=0
	    bracket=0
	    max_planets=0
	    
	    for r in res:
		gals+=r['count']
	    bracket=int(gals*.2)
	    for r in res:
		bracket-=r['count']
		if bracket < 0:
		    break
		max_planets=r['planets']
		
	    reply="Total galaxies: %s Maximum planets to guarantee a galaxy is in the exile bracket: %s" % (gals,max_planets)

	self.client.reply(prefix,nick,target,reply)

        return 1