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

class spam(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,100)
        self.paramre=re.compile(r"^\s+(\S+)")
        self.usage=self.__class__.__name__ + " <alliance>"
        
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
        params=m.group(1)

        
        # do stuff here
        args=('%'+params+'%',)
        query="SELECT t1.x AS x,t1.y AS y,t1.z AS z,t1.size AS size,t1.score AS score,t1.value AS value,t1.race AS race,t2.alliance AS alliance,t2.nick AS nick,t2.reportchan AS reportchan,t2.comment AS comment"
        query+=" FROM planet_dump AS t1 INNER JOIN planet_canon AS t3 ON t1.id=t3.id"
        query+=" INNER JOIN intel AS t2 ON t3.id=t2.pid"
        query+=" WHERE t1.tick=(SELECT MAX(tick) FROM updates) AND (t2.alliance ILIKE %s) ORDER BY x,y,z"
        self.cursor.execute(query,args)

        i=0
        planets=self.cursor.dictfetchall()
        if not len(planets):
            reply="No planets in intel matching alliance: %s"%(params,)
            self.client.reply(prefix,nick,target,reply)
            return 1

        printable=map(lambda d: "%s:%s:%s" % (d['x'],d['y'],d['z']),planets)
        print printable
        reply="Spam on alliance %s - " %(planets[0]['alliance'])
        while printable:
            batch=printable[:10]
            printable=printable[10:]
            reply+=str.join(' | ',batch)
            self.client.reply(prefix,nick,target,reply)
            reply=""

        return 1
