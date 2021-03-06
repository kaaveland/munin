#!/usr/bin/python

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

import time

import ConfigParser
import os
from psycopg2 import psycopg1 as psycopg
import re
import traceback
import urllib2

config = ConfigParser.ConfigParser()
if not config.read("muninrc"):
    # No config found.
    raise ValueError("Expected configuration file muninrc"
                     ", not found.")

DSN = "dbname=%s user=%s" % (config.get("Database", "dbname"),
                             config.get("Database", "user"))
if config.has_option('Database', 'password'):
    DSN += ' password=%s' % config.get('Database', 'password')
if config.has_option('Database', 'host'):
    DSN += ' host=%s' % config.get('Database', 'host')

t_start=time.time()
t1=t_start

ofile=file("pid.hugin", "w")
ofile.write("%s" % (os.getpid(),))
ofile.close()

while True:
    try:
        conn=psycopg.connect(DSN)
        cursor=conn.cursor()

        cursor.execute("SELECT max_tick()")
        last_tick=int(cursor.fetchone()[0])
        if not last_tick:
            last_tick = -1

        try:
            planets = urllib2.urlopen(config.get("Url", "planetlist"))
        except Exception, e:
            print "Failed gathering planet listing."
            print e.__str__()
            time.sleep(300)
            continue
        try:
            galaxies = urllib2.urlopen(config.get("Url", "galaxylist"))
        except Exception, e:
            print "Failed gathering galaxy listing."
            print e.__str__()
            time.sleep(300)
            continue
        try:
            alliances = urllib2.urlopen(config.get("Url", "alliancelist"))
        except Exception, e:
            print "Failed gathering alliance listing."
            print e.__str__()
            time.sleep(300)
            continue

        planets.readline();planets.readline();planets.readline();
        tick=planets.readline()
        m=re.search(r"tick:\s+(\d+)",tick,re.I)
        if not m:
            print "Invalid tick: '%s'" % (tick,)
            time.sleep(120)
            continue
        planet_tick=int(m.group(1))
        print "Planet dump for tick %s" % (planet_tick,)
        planets.readline();planets.readline();planets.readline();

        galaxies.readline();galaxies.readline();galaxies.readline();
        tick=galaxies.readline()
        m=re.search(r"tick:\s+(\d+)",tick,re.I)
        if not m:
            print "Invalid tick: '%s'" % (tick,)
            time.sleep(120)
            continue
        galaxy_tick=int(m.group(1))
        print "Galaxy dump for tick %s" % (galaxy_tick,)
        galaxies.readline();galaxies.readline();galaxies.readline();

        alliances.readline();alliances.readline();alliances.readline();
        ptick=alliances.readline()
        m=re.search(r"tick:\s+(\d+)",tick,re.I)
        if not m:
            print "Invalid tick: '%s'" % (tick,)
            time.sleep(120)
            continue
        alliance_tick=int(m.group(1))
        print "Alliance dump for tick %s" % (alliance_tick,)
        alliances.readline();alliances.readline();alliances.readline();

        if not (planet_tick == galaxy_tick  == alliance_tick):
            print "Varying ticks found, sleeping"
            print "Planet: %s, Galaxy: %s, Alliance: %s" % (planet_tick,galaxy_tick,alliance_tick)
            time.sleep(30)
            continue
        if not planet_tick > last_tick:
            print "Stale ticks found, sleeping"
            time.sleep(60)
            continue

        t2=time.time()-t1
        print "Loaded dumps from webserver in %.3f seconds" % (t2,)
        t1=time.time()

        ptmp='ptmp'
        gtmp='gtmp'
        atmp='atmp'

        query="""
        CREATE TEMP TABLE %s (
         x smallint,
         y smallint,
         z smallint,
         planetname varchar(22) NOT NULL,
         rulername varchar(22) NOT NULL,
         race char(3) CHECK (race in (NULL,'Ter','Cat','Xan','Zik','Etd')),
         size integer NOT NULL,
         score integer NOT NULL,
         value integer NOT NULL,
         xp integer NOT NULL
         )
        """ % (ptmp,)
        cursor.execute(query)
        cursor.copy_from(planets,ptmp,"\t")

        query="""
        CREATE TEMP TABLE %s (
         x smallint,
         y smallint,
         name varchar(66) NOT NULL,
         size int NOT NULL,
         score bigint NOT NULL,
         value bigint NOT NULL,
         xp integer NOT NULL
        )
        """ % (gtmp,)
        cursor.execute(query)
        cursor.copy_from(galaxies,gtmp,"\t")

        query="""
        CREATE TEMP TABLE %s (
         score_rank smallint NOT NULL,
         name varchar(22) NOT NULL,
         size int NOT NULL,
         members smallint NOT NULL,
         score bigint NOT NULL
        )
        """ % (atmp,)
        cursor.execute(query)
        cursor.copy_from(alliances,atmp,"\t")

        t2=time.time()-t1
        print "Copied dumps in %.3f seconds" % (t2,)
        t1=time.time()

        query="SELECT store_update(%s::smallint,%s::text,%s::text,%s::text)"
        cursor.execute(query,(planet_tick,ptmp,gtmp,atmp))

        try:

            query="SELECT store_planets(%s::smallint)"
            cursor.execute(query,(planet_tick,))
            t2=time.time()-t1
            print "Processed and inserted planet dumps in %.3f seconds" % (t2,)
            t1=time.time()


            #query="SELECT * FROM %s" % (ptmp,)
            #cursor.execute(query)
            #for result in cursor.dictfetchall():
            #    print result

            query="SELECT store_galaxies(%s::smallint)"
            cursor.execute(query,(galaxy_tick,))
            t2=time.time()-t1
            print "Processed and inserted galaxy dumps in %.3f seconds" % (t2,)
            t1=time.time()

            query="SELECT store_alliances(%s::smallint)"
            cursor.execute(query,(alliance_tick,))    
            t2=time.time()-t1
            print "Processed and inserted alliance dumps in %.3f seconds" % (t2,)
            t1=time.time()

        except psycopg.IntegrityError:
            raise Exception("IntegrityError on dump inserts. Tick number has already been validated above, so that means something else is not unique on PA's end that should be and PA team fucked up again. Go and whine in #support.")

        conn.commit()
        break
    except Exception, e:
        print "Something random went wrong, sleeping for 15 seconds to hope it improves"
        print e.__str__()
        traceback.print_exc()
        time.sleep(15)
        continue


t2=time.time()-t1
t1=time.time()-t_start
print "Commit in %.3f seconds" % (t2,)
print "Total time taken: %.3f seconds" % (t1,)

while True:
    try:
        conn=psycopg.connect(DSN)
        cursor=conn.cursor()

        cursor.execute("SELECT MIN(tick) FROM updates WHERE tick > 0")
        min_tick=int(cursor.fetchone()[0])
        if not min_tick:
            min_tick = -1

        query="DELETE FROM epenis_cache"
        cursor.execute(query)
        query="CREATE TEMP SEQUENCE activity_rank"
        cursor.execute(query)



        query="INSERT INTO epenis_cache (planet_id, epenis, epenis_rank) "
        query+=" SELECT *,nextval('activity_rank') AS activity_rank"
        query+=" FROM (SELECT t1.id, t1.score-t5.score AS activity"
        query+=" FROM planet_dump AS t1"
        query+=" INNER JOIN planet_dump AS t5"
        query+=" ON t1.id=t5.id"
        query+=" WHERE t1.tick = (select max(tick) from updates)"
        query+=" AND t5.tick = GREATEST(t1.tick - 72, %s)"
        query+=" ORDER BY activity DESC) AS t8;"
        cursor.execute(query,(min_tick,))


        conn.commit()
        break
    except Exception, e:
        print "Something random went wrong, sleeping for 15 seconds to hope it improves"
        print e.__str__()
        traceback.print_exc()
        time.sleep(15)
        continue

print "Generated epenis_cache"
