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

# This file has no alliance specific stuff as far as I can tell.
# qebab, 22/06/08

class au(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,50)
        self.commandre=re.compile(r"^"+self.__class__.__name__+"(.*)")
        self.paramre=re.compile(r"^\s+(.*)")
        self.idre=re.compile(r"(\d{1,9})")
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
        params=m.group(1)
        m=self.planet_coordre.search(params)
        
        reply=""
        if m:
            x=m.group(1)
            y=m.group(2)
            z=m.group(3)
            
            p=loadable.planet(x=x,y=y,z=z)
            if not p.load_most_recent(self.conn,self.client,self.cursor):
                self.client.reply(prefix,nick,target,"No planet matching '%s:%s:%s' found"%(x,y,z))
                return 1

            query="SELECT t1.tick,t1.nick,t1.scantype,t1.rand_id,t3.name,t2.amount"
            query+=" FROM scan AS t1"
            query+=" INNER JOIN au AS t2 ON t1.id=t2.scan_id"
            query+=" INNER JOIN ship AS t3 ON t2.ship_id=t3.id"
            query+=" WHERE t1.pid=%s AND t1.id=(SELECT id FROM scan WHERE pid=t1.pid AND scantype='au' ORDER BY tick DESC LIMIT 1)"
            self.cursor.execute(query,(p.id,))

            if self.cursor.rowcount < 1:
                reply+="No advanced unit scans available on %s:%s:%s" % (p.x,p.y,p.z)
            else:
                
                reply+="Newest advanced unit scan on %s:%s:%s" % (p.x,p.y,p.z)
                
                prev=[]
                for s in self.cursor.dictfetchall():
                    prev.append("%s %s" % (s['name'],s['amount']))
                    tick=s['tick']
                    rand_id=s['rand_id']
                    
                reply+=" (id: %s, pt: %s) " % (rand_id,tick)
                reply+=string.join(prev,' | ')
        else:
            m=self.idre.search(params)
            if not m:
                self.client.reply(prefix,nick,target,"Usage: %s" % (self.usage,))
                return 0
            
            rand_id=m.group(1)

            query="SELECT x,y,z,t1.tick,t1.nick,t1.scantype,t1.rand_id,t3.name,t2.amount"
            query+=" FROM scan AS t1"
            query+=" INNER JOIN au AS t2 ON t1.id=t2.scan_id"
            query+=" INNER JOIN ship AS t3 ON t2.ship_id=t3.id"
            query+=" INNER JOIN planet_dump AS t4 ON t1.pid=t4.id"
            query+=" WHERE t4.tick=(SELECT max_tick()) AND t1.rand_id=%s"
            self.cursor.execute(query,(rand_id,))

            if self.cursor.rowcount < 1:
                reply+="No planet scans matching ID %s" % (rand_id,)
            else:
                reply+="Newest advanced unit scan on "

                prev=[]
                for s in self.cursor.dictfetchall():
                    prev.append("%s %s" % (s['name'],s['amount']))
                    tick=s['tick']
                    x=s['x']
                    y=s['y']
                    z=s['z']

                reply+="%s:%s:%s (id: %s, pt: %s) " % (x,y,z,rand_id,tick)
                reply+=string.join(prev,' | ')
        self.client.reply(prefix,nick,target,reply)
        return 1
                    
                    
                    
                