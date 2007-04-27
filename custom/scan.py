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

import urllib2, re, os, sys, string, psycopg, loadable, threading, traceback

class scan(threading.Thread):
    def __init__(self, rand_id,client,conn,cursor,nick,pnick): # random scan ID, and client for debug ONLY
        self.rand_id=rand_id
        self.client=client
        self.conn=conn
        self.cursor=cursor
        self.nick=nick
        self.pnick=pnick
        
    def run(self):
        # database connection and cursor
        #    self.user="andreaja"
        #    self.dbname="patest"
        #    self.conn=psycopg.connect("user=%s dbname=%s" % (self.user,self.dbname))
        #    self.conn.serialize()
        #    self.conn.autocommit()
        #    self.c=self.conn.cursor()
        try:
            self.unsafe_method()
        except Exception, e:
            print "Exception in scan: "+e.__str__()
            #self.client.privmsg('jesterina',"Exception in scan: "+e.__str__())
            traceback.print_exc()
            


    def unsafe_method(self):
        page = urllib2.urlopen('http://game.planetarion.com/showscan.pl?scan_id=' + self.rand_id).read()

        m = re.search('>([^>]+) on (\d+)\:(\d+)\:(\d+) in tick (\d+)', page)
        if not m:
            print "Expired/non-matchinng scan (id: %s)" %(self.rand_id,)
            return
        
        scantype=self.name_to_type(m.group(1))
        x = m.group(2)
        y = m.group(3)
        z = m.group(4)
        tick = m.group(5)
        
        #check to see if we have already added this scan to the database
        p=loadable.planet(x, y, z)
        if p.load_most_recent(self.conn, 0 ,self.cursor): #really, this should never, ever fail.
            #quickly insert the scan incase someone else pastes it :o
            next_id=-1
            nxt_query= "SELECT nextval('scan_id_seq')"
            query = "INSERT INTO scan (id, tick, pid, nick, pnick, scantype, rand_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            try:
                self.cursor.execute(nxt_query)
                next_id=self.cursor.dictfetchone()['nextval']
                self.cursor.execute(query, (next_id, tick, p.id, self.nick, self.pnick, scantype, self.rand_id))
            except psycopg.IntegrityError, e:
                print "Scan %s may already exist" %(self.rand_id,)
                print e.__str__()
                #FIXME: enable the following line once done testing:
                return
            if next_id < 0:
                raise Exception("Scan id is %s"%(next_id,))
            #scantype VARCHAR(10) NOT NULL CHECK(scantype in ('planet','structure','technology','unit','news','jgp','fleet'))
            if scantype=='planet':
                self.parse_planet(next_id,page)
                
            elif scantype=='structure':
                self.parse_surface(next_id,page)
                
            elif scantype=='technology':
                self.parse_technology(next_id,page)
                
            elif scantype=='unit':
                self.parse_unit(next_id,page,'unit')

            elif scantype=='news':
                self.parse_news(next_id,page)
#                query="DELETE FROM scan WHERE id=%s"
#                self.cursor.execute(query,(next_id,))
            elif scantype=='jgp':
                self.parse_jumpgate(next_id,page)
            elif scantype=='au':
                self.parse_unit(next_id,page,'au')
        
    def name_to_type(self,name):
        if name=='Planet Scan':
            return "planet"
        elif name=='Surface Analysis Scan':
            return "structure"
        elif name=='Technology Analysis Scan':
            return "technology"
        elif name=='Unit Scan':
            return "unit"
        elif name=='News Scan':
            return "news"
        elif name=='Jumpgate Probe':
            return "jgp"
        elif name=="Advanced Unit Scan":
            return "au"

        print "Name: "+name
        
    def parse_news(self, scan_id,page):
        m = re.search('on (\d+)\:(\d+)\:(\d+) in tick (\d+)', page)
        x = m.group(1)
        y = m.group(2)
        z = m.group(3)
        tick = m.group(4)

        p=loadable.planet(x, y, z)
        if not p.load_most_recent(self.conn, 0 ,self.cursor): #really, this should never, ever fail.
            return
    #incoming fleets
    #<td class=left valign=top>Incoming</td><td valign=top>851</td><td class=left valign=top>We have detected an open jumpgate from Tertiary, located at 18:5:11. The fleet will approach our system in tick 855 and appears to have roughly 95 ships.</td>
        for m in re.finditer('<td class="left" valign="top">Incoming</td><td valign="top">(\d+)</td><td class="left" valign="top">We have detected an open jumpgate from ([^<]+), located at (\d+):(\d+):(\d+). The fleet will approach our system in tick (\d+) and appears to have roughly (\d+) ships.</td>', page):
            newstick = m.group(1)
            fleetname = m.group(2)
            originx = m.group(3)
            originy = m.group(4)
            originz = m.group(5)
            arrivaltick = m.group(6)
            numships = m.group(7)

            owner=loadable.planet(originx,originy,originz)
            if not owner.load_most_recent(self.conn, 0 ,self.cursor):
                continue
            query="INSERT INTO fleet (scan_id,owner,target,fleet_size,fleet_name,launch_tick,landing_tick,mission) VALUES (%s,%s,%s,%s,%s,%s,%s,'unknown')"
            try:
                self.cursor.execute(query,(scan_id,owner.id,p.id,numships,fleetname,newstick,arrivaltick))
            except Exception, e:
                print "Exception in news: "+e.__str__()
                traceback.print_exc()
                continue
            
            print 'Incoming: ' + newstick + ':' + fleetname + '-' + originx + ':' + originy + ':' + originz + '-' + arrivaltick + '|' + numships

    #launched attacking fleets
    #<td class=left valign=top>Launch</td><td valign=top>848</td><td class=left valign=top>The Disposable Heroes fleet has been launched, heading for 15:9:8, on a mission to Attack. Arrival tick: 857</td>
        for m in re.finditer('<td class="left" valign="top">Launch</td><td valign="top">(\d+)</td><td class="left" valign="top">The ([^,]+) fleet has been launched, heading for (\d+):(\d+):(\d+), on a mission to Attack. Arrival tick: (\d+)</td>', page):
            newstick = m.group(1)
            fleetname = m.group(2)
            originx = m.group(3)
            originy = m.group(4)
            originz = m.group(5)
            arrivaltick = m.group(6)

            target=loadable.planet(originx,originy,originz)
            if not target.load_most_recent(self.conn, 0 ,self.cursor):
                continue
            query="INSERT INTO fleet (scan_id,owner,target,fleet_name,launch_tick,landing_tick,mission) VALUES (%s,%s,%s,%s,%s,%s,'attack')"
            
            try:
                self.cursor.execute(query,(scan_id,p.id,target.id,fleetname,newstick,arrivaltick))
            except Exception, e:
                print "Exception in news: "+e.__str__()
                traceback.print_exc()
                continue            

            print 'Attack:' + newstick + ':' + fleetname + ':' + originx + ':' + originy + ':' + originz + ':' + arrivaltick

    #launched defending fleets
    #<td class=left valign=top>Launch</td><td valign=top>847</td><td class=left valign=top>The Ship Collection fleet has been launched, heading for 2:9:14, on a mission to Defend. Arrival tick: 853</td>
        for m in re.finditer('<td class="left" valign="top">Launch</td><td valign="top">(\d+)</td><td class="left" valign="top">The ([^<]+) fleet has been launched, heading for (\d+):(\d+):(\d+), on a mission to Defend. Arrival tick: (\d+)</td>', page):
            newstick = m.group(1)
            fleetname = m.group(2)
            originx = m.group(3)
            originy = m.group(4)
            originz = m.group(5)
            arrivaltick = m.group(6)

            target=loadable.planet(originx,originy,originz)
            if not target.load_most_recent(self.conn, 0 ,self.cursor):
                continue
            query="INSERT INTO fleet (scan_id,owner,target,fleet_name,launch_tick,landing_tick,mission) VALUES (%s,%s,%s,%s,%s,%s,'defend')"
            
            try:
                self.cursor.execute(query,(scan_id,p.id,target.id,fleetname,newstick,arrivaltick))
            except Exception, e:
                print "Exception in news: "+e.__str__()
                traceback.print_exc()
                continue            

            print 'Defend:' + newstick + ':' + fleetname + ':' + originx + ':' + originy + ':' + originz + ':' + arrivaltick


    #tech report
    #<td class=left valign=top>Tech</td><td valign=top>838</td><td class=left valign=top>Our scientists report that Portable EMP emitters has been finished. Please drop by the Research area and choose the next area of interest.</td>
        for m in re.finditer('<td class="left" valign="top">Tech</td><td valign="top">(\d+)</td><td class="left" valign="top">Our scientists report that ([^<]+) has been finished. Please drop by the Research area and choose the next area of interest.</td>', page):
            newstick = m.group(1)
            research = m.group(2)

            print 'Tech:' + newstick + ':' + research

    #failed security report
    #<td class=left valign=top>Security</td><td valign=top>873</td><td class=left valign=top>A covert operation was attempted by Ikaris (2:5:5), but our agents were able to stop them from doing any harm.</td>
        for m in re.finditer('<td class="left" valign="top">Security</td><td valign="top">(\d+)</td><td class="left" valign="top">A covert operation was attempted by ([^<]+) \\((\d+):(\d+):(\d+)\\), but our agents were able to stop them from doing any harm.</td>', page):
            newstick = m.group(1)
            ruler = m.group(2)
            originx = m.group(3)
            originy = m.group(4)
            originz = m.group(5)

            covopper=loadable.planet(originx,originy,originz)
            if not covopper.load_most_recent(self.conn, 0 ,self.cursor):
                continue
            
            query="INSERT INTO covop (scan_id,covopper,target) VALUES (%s,%s,%s)"
            
            try:
                self.cursor.execute(query,(scan_id,covopper.id,p.id))
            except Exception, e:
                print "Exception in unit: "+e.__str__()
                traceback.print_exc()
                continue            
            
            print 'Security:' + newstick + ':' + ruler + ':' + originx + ':' + originy + ':' + originz

    #fleet report
    #<tr bgcolor=#2d2d2d><td class=left valign=top>Fleet</td><td valign=top>881</td><td class=left valign=top><table width=500><tr><th class=left colspan=3>Report of Losses from the Disposable Heroes fighting at 13:10:3</th></tr>
    #<tr><th class=left width=33%>Ship</th><th class=left width=33%>Arrived</th><th class=left width=33%>Lost</th></tr>
    #
    #<tr><td class=left>Syren</td><td class=left>15</td><td class=left>13</td></tr>
    #<tr><td class=left>Behemoth</td><td class=left>13</td><td class=left>13</td></tr>
    #<tr><td class=left>Roach</td><td class=left>6</td><td class=left>6</td></tr>
    #<tr><td class=left>Thief</td><td class=left>1400</td><td class=left>1400</td></tr>
    #<tr><td class=left>Clipper</td><td class=left>300</td><td class=left>181</td></tr>
    #
    #<tr><td class=left>Buccaneer</td><td class=left>220</td><td class=left>102</td></tr>
    #<tr><td class=left>Rogue</td><td class=left>105</td><td class=left>105</td></tr>
    #<tr><td class=left>Marauder</td><td class=left>110</td><td class=left>110</td></tr>
    #<tr><td class=left>Ironclad</td><td class=left>225</td><td class=left>90</td></tr>
    #</table>
    #
    #<table width=500><tr><th class=left colspan=3>Report of Ships Stolen by the Disposable Heroes fighting at 13:10:3</th></tr>
    #<tr><th class=left width=50%>Ship</th><th class=left width=50%>Stolen</th></tr>
    #<tr><td class=left>Roach</td><td class=left>5</td></tr>
    #<tr><td class=left>Hornet</td><td class=left>1</td></tr>
    #<tr><td class=left>Wraith</td><td class=left>36</td></tr>
    #</table>
    #<table width=500><tr><th class=left>Asteroids Captured</th><th class=left>Metal : 37</th><th class=left>Crystal : 36</th><th class=left>Eonium : 34</th></tr></table>
    #
    #</td></tr>

        print 'News: '+x+':'+y+':'+z

    def parse_planet(self, scan_id, page):
        m = re.search('on (\d+)\:(\d+)\:(\d+) in tick (\d+)', page)
        x = m.group(1)
        y = m.group(2)
        z = m.group(3)
        tick = m.group(4)
        
        m = re.search('<tr><td class="left">Asteroids</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td></tr><tr><td class="left">Resources</td><td>(\d+)</td><td>(\d+)</td><td>(\d+)</td></tr><tr><th>Score</th><td>(\d+)</td><th>Value</th><td>(\d+)</td></tr>', page)
        roid_m = m.group(1)
        roid_c = m.group(2)
        roid_e = m.group(3)
        res_m = m.group(4)
        res_c = m.group(5)
        res_e = m.group(6)
        score = m.group(7)
        value = m.group(8)

        query="INSERT INTO planet (scan_id,roid_metal,roid_crystal,roid_eonium,res_metal,res_crystal,res_eonium)"
        query+=" VALUES (%s,%s,%s,%s,%s,%s,%s)"

        self.cursor.execute(query,(scan_id,roid_m,roid_c,roid_e,res_m,res_c,res_e))
        
        print 'Planet: '+x+':'+y+':'+z

    def parse_surface(self, scan_id, page):
        m = re.search('on (\d*)\:(\d*)\:(\d*) in tick (\d*)</th></tr><tr><td class="left">Light Factory</td><td>(\d*)</td></tr><tr><td class="left">Medium Factory</td><td>(\d*)</td></tr><tr><td class="left">Heavy Factory</td><td>(\d*)</td></tr><tr><td class="left">Wave Amplifier</td><td>(\d*)</td></tr><tr><td class="left">Wave Distorter</td><td>(\d*)</td></tr><tr><td class="left">Metal Refinery</td><td>(\d*)</td></tr><tr><td class="left">Crystal Refinery</td><td>(\d*)</td></tr><tr><td class="left">Eonium Refinery</td><td>(\d*)</td></tr><tr><td class="left">Research Laboratory</td><td>(\d*)</td></tr><tr><td class="left">Finance Centre</td><td>(\d*)</td></tr><tr><td class="left">Security Centre</td><td>(\d*)</td></tr>', page)
        x = m.group(1)
        y = m.group(2)
        z = m.group(3)
        tick = m.group(4)
        lightfactory = m.group(5)
        medfactory = m.group(6)
        heavyfactory = m.group(7)
        waveamp = m.group(8)
        wavedist = m.group(9)
        metalref = m.group(10)
        crystalref = m.group(11)
        eref = m.group(12)
        reslab = m.group(13)
        finance = m.group(14)
        security = m.group(15)

        query="INSERT INTO structure (scan_id,light_factory,medium_factory,heavy_factory,wave_amplifier,wave_distorter,metal_refinery,crystal_refinery,eonium_refinery,research_lab,finance_centre,security_centre)"
        query+=" VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        self.cursor.execute(query,(scan_id,lightfactory,medfactory,heavyfactory,waveamp,wavedist,metalref,crystalref,eref,reslab,finance,security))        
        
        print 'Surface: '+x+':'+y+':'+z

    def parse_technology(self,scan_id, page):
        m = re.search('on (\d*)\:(\d*)\:(\d*) in tick (\d*)</th></tr><tr><th class="left">Space Travel</th><td>(\d*)</td></tr>\\n<tr><th class="left">Infrastructure</th><td>(\d*)</td></tr>\\n<tr><th class="left">Hulls</th><td>(\d*)</td></tr>\\n<tr><th class="left">Waves</th><td>(\d*)</td></tr>\\n<tr><th class="left">Core Extraction</th><td>(\d*)</td></tr>\\n<tr><th class="left">Covert Ops</th><td>(\d*)</td></tr>\\n<tr><th class="left">Asteroid Mining</th><td>(\d*)</td></tr>', page)
        x = m.group(1)
        y = m.group(2)
        z = m.group(3)
        tick = m.group(4)
        travel = m.group(5)
        inf = m.group(6)
        hulls = m.group(7)
        waves = m.group(8)
        core = m.group(9)
        covop = m.group(10)
        mining = m.group(11)

        query="INSERT INTO technology (scan_id,travel,infrastructure,hulls,waves,core,covert_op,mining)"
        query+=" VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        self.cursor.execute(query,(scan_id,travel,inf,hulls,waves,core,covop,mining))

        print 'Technology: '+x+':'+y+':'+z

    def parse_unit(self, scan_id, page, table):
        m = re.search('on (\d*)\:(\d*)\:(\d*) in tick (\d*)', page)
        x = m.group(1)
        y = m.group(2)
        z = m.group(3)
        tick = m.group(4)

        for m in re.finditer('(\w+\s?\w*)</td><td>(\d+)</td>', page):
            print m.groups()
            shipname=m.group(1)
            amount=m.group(2)
            query="INSERT INTO %s"%(table,)
            query+=" (scan_id,ship_id,amount) VALUES (%s,(SELECT id FROM ship WHERE name=%s),%s)"
            try:
                self.cursor.execute(query,(scan_id,shipname,amount))
            except Exception, e:
                print "Exception in unit: "+e.__str__()
                traceback.print_exc()
                continue
                                        
        print 'Unit: '+x+':'+y+':'+z

    def parse_jumpgate(self, scan_id,page):
        m = re.search('on (\d+)\:(\d+)\:(\d+) in tick (\d+)', page)
        x = m.group(1)
        y = m.group(2)
        z = m.group(3)
        tick = m.group(4)
        # <td class=left>Origin</td><td class=left>Mission</td><td>Fleet</td><td>ETA</td><td>Fleetsize</td>
        # <td class=left>13:10:5</td><td class=left>Attack</td><td>Gamma</td><td>5</td><td>265</td>

        p=loadable.planet(x, y, z)
        if not p.load_most_recent(self.conn, 0 ,self.cursor): #really, this should never, ever fail, but exiles might bork it
            return

        #                     <td class="left">15:7:11            </td><td class="left">Defend </td><td>Ad infinitum</td><td>9</td><td>0</td>
        #<tr><td class="left">10:4:9</td><td class="left">Return</td><td>They look thirsty</td><td>5</td><td>3000</td></tr>
        for m in re.finditer('<td class="left">(\d+)\:(\d+)\:(\d+)</td><td class="left">([^<]+)</td><td>([^<]+)</td><td>(\d+)</td><td>(\d+)</td>', page):
            originx = m.group(1)
            originy = m.group(2)
            originz = m.group(3)
            mission = m.group(4)
            fleet = m.group(5)
            eta = m.group(6)
            fleetsize = m.group(7)
            
            attacker=loadable.planet(originx,originy,originz)
            if not attacker.load_most_recent(self.conn, 0 ,self.cursor):
                print "Can't find attacker in db: %s:%s:%s"%(originx,originy,originz) 
                continue
            query="INSERT INTO fleet (scan_id,owner,target,fleet_size,fleet_name,landing_tick,mission) VALUES (%s,%s,%s,%s,%s,%s,%s)"

            try:
                self.cursor.execute(query,(scan_id,attacker.id,p.id,fleetsize,fleet,int(tick)+int(eta),mission.lower()))
            except psycopg.IntegrityError, e:
                print "Exception in jgp: "+e.__str__()
                traceback.print_exc()
                print "Trying to update instead"
                query="UPDATE fleet SET scan_id=%s WHERE owner=%s AND target=%s AND fleet_size=%s AND fleet_name=%s AND landing_tick=%s AND mission=%s"
                try:
                    self.cursor.execute(query,(scan_id,attacker.id,p.id,fleetsize,fleet,int(tick)+int(eta),mission.lower()))
                except:
                    
                    print "Exception in jgp: "+e.__str__()
                    traceback.print_exc()
                    continue
            except Exception, e:
                print "Exception in jgp: "+e.__str__()
                traceback.print_exc()
                continue
                                                                                                            
            
        
        print 'Jumpgate: '+x+':'+y+':'+z
