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

import re,traceback,loadable

class galstatus:
    def __init__(self, client,conn,cursor):
        self.client=client
        self.conn=conn
        self.cursor=cursor
        self.statusre=re.compile(r"(\d+):(\d+):(\d+)\*?\s+(\d+):(\d+):(\d+)\s+(.*?)\s+((Xan|Ter|Cat|Zik|Etd)\s+)?(\d+)\s+(Return|Attack|Defend)\s+(\d+)")

    def parse(self,message,nick,pnick,target):
        try:
            self.unsafe_method(message,nick,pnick,target)
        except Exception, e:
            print "Exception in galstatus: "+e.__str__()
            self.client.privmsg('jesterina',"Exception in galstatus: "+e.__str__())
            traceback.print_exc()

    def report_incoming(self,target,message,reporter,source):
        i=loadable.intel(pid=target.id)
        if not i.load_from_db(self.conn,self.client,self.cursor):
            print "planet %s:%s:%s not in intel"%(target.x,target.y,target.z)
            return
        
        if i.alliance and i.alliance.lower() == 'ascendancy' and source != i.reportchan and not (i.relay and i.reportchan != "#ascendancy"):
            reply="%s reports: " % (reporter,)
            if i.nick:
                reply+=i.nick + " -> "
            reply+=message
            self.client.privmsg("#ascendancy",reply)
            return
        
        if i.relay and i.reportchan and source != i.reportchan:
            reply="%s reports: " % (reporter,)
            if i.nick:
                reply+=i.nick + " -> "
            reply+=message
            self.client.privmsg(i.reportchan,reply)
        else:
            print "planet not set to relay (%s) or report (%s) or report is source (%s)"%(i.relay,i.reportchan,source)

    def unsafe_method(self,message,nick,pnick,source):
        message=message.replace("\x02","")
        m=self.statusre.search(message)
        if not m:

            return
        print m.groups()

        target_x=m.group(1)
        target_y=m.group(2)
        target_z=m.group(3)        

        owner_x=m.group(4)
        owner_y=m.group(5)
        owner_z=m.group(6)        



        fleetname=m.group(7)
        race=m.group(9)
        fleetsize=m.group(10)
        mission=m.group(11)
        eta=m.group(12)

        print "%s:%s:%s %s:%s:%s '%s' %s m:%s e:%s"%(owner_x,owner_y,owner_z,target_x,target_y,target_z,fleetname,fleetsize,mission,eta)

        target=loadable.planet(target_x,target_y,target_z)
        if not target.load_most_recent(self.conn, 0 ,self.cursor):
            return

        self.report_incoming(target,message,nick,source)

        owner=loadable.planet(owner_x,owner_y,owner_z)
        if not owner.load_most_recent(self.conn, 0 ,self.cursor):
            return
        self.cursor.execute("SELECT max_tick() AS max_tick")
        curtick=self.cursor.dictfetchone()['max_tick']

        query="INSERT INTO fleet(owner_id,target,fleet_size,fleet_name,landing_tick,mission) VALUES (%s,%s,%s,%s,%s,%s)"
        
        try:
            self.cursor.execute(query,(owner.id,target.id,fleetsize,fleetname,int(eta)+int(curtick),mission.lower()))
        except Exception,e:
            print "Exception in galstatus: "+e.__str__()
            traceback.print_exc()