"""
Loadable.Loadable subclass
"""

class tech(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,100)
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
                self.client.reply(prefix,nick,target,"No planet matching '%s' found"%(param,))
                return 1
            
            query="SELECT t2.id AS id,tick,nick,scantype,rand_id,travel,infrastructure,hulls,waves,core,covert_op,mining"
            query+=" FROM scan AS t1 INNER JOIN technology AS t2 ON t1.id=t2.scan_id"
            query+=" WHERE t1.pid=%s ORDER BY tick DESC"
            self.cursor.execute(query,(p.id,))
                
            if self.cursor.rowcount < 1:
                reply+="No surface scans available on %s:%s:%s" % (p.x,p.y,p.z)
            else:
                s=self.cursor.dictfetchone()
                reply+="Newest surface scan on %s:%s:%s (id: %s, pt: %s)" % (p.x,p.y,p.z,s['rand_id'],s['tick'])
                reply+=" Travel: %s, Infrajerome: %s, Hulls: %s, Waves: %s, Core: %s, Covop: %s, Mining: %s"%(s['travel'],self.infra(s['infrastructure']),self.hulls(s['hulls']),
                                                                                                              self.waves(s['waves']),s['core'],self.covop(s['covert_op']),
                                                                                                              self.mining(s['mining']))
                i=0
                reply+=" Older scans: "
                prev=[]
                for s in self.cursor.dictfetchall():
                    i+=1
                    if i > 4:
                        break
                    prev.append("(%s,pt%s)" % (s['rand_id'],s['tick']))
                reply+=string.join(prev,', ')

        else:
            m=self.idre.search(params)
            if not m:
                self.client.reply(prefix,nick,target,"Usage: %s" % (self.usage,))
                return 0

            rand_id=m.group(1)
            query="SELECT x,y,z,t2.id AS id,t1.tick AS tick,nick,scantype,rand_id,travel,infrastructure,hulls,waves,core,covert_op,mining"
            query+=" FROM scan AS t1 INNER JOIN technology AS t2 ON t1.id=t2.scan_id"
            query+=" INNER JOIN planet_dump AS t3 ON t1.pid=t3.id"
            query+=" WHERE t3.tick=(SELECT MAX(tick) FROM updates) AND t1.rand_id=%s ORDER BY tick DESC"
            self.cursor.execute(query,(rand_id,))
        
            if self.cursor.rowcount < 1:
                reply+="No surface scans matching ID %s" % (rand_id,)
            else:
                s=self.cursor.dictfetchone()
                reply+="Surface scan on %s:%s:%s (id: %s, pt: %s)" % (s['x'],s['y'],s['z'],s['rand_id'],s['tick'])
                reply+=" Travel: %s, Infrajerome: %s, Hulls: %s, Waves: %s, Core: %s, Covop: %s, Mining: %s"%(s['travel'],self.infra(s['infrastructure']),self.hulls(s['hulls']),
                                                                                                              self.waves(s['waves']),s['core'],self.covop(s['covert_op']),
                                                                                                              self.mining(s['mining']))
                
        self.client.reply(prefix,nick,target,reply)
        
        return 1

    def infra(self,level):
        if level==0:
            return "10 constructions"
        if level==1:
            return "20 constructions"
        if level==2:
            return "50 constructions"
        if level==3:
            return "100 constructions"        
        if level==4:
            return "150 constructions"                

    def hulls(self,level):
        if level==0:
            return "FI/CO"
        if level==1:
            return "FR/DE"
        if level==2:
            return "CR/BS"

    def waves(self,level):
        if level==0:
            return "Planet"
        if level==1:
            return "Surface"
        if level==2:
            return "Technology"
        if level==3:
            return "Unit"
        if level==4:
            return "News"
        if level==5:
            return "JGP"
        if level==6:
            return "Fleet"

    def covop(self,level):
        if level==0:
            return "Research Fuck"
        if level==1:
            return "Raise Stealth"
        if level==2:
            return "Blow up roids"
        if level==3:
            return "Blow up shits"
        if level==4:
            return "Blow up Amps/Dists"
        if level==5:
            return "Resource hacking (OMG!)"
        if level==6:
            return "Blow up Strucs"
        

    def mining(self,level):
        if level==0:
            return "Fucking newbie"
        if level==1:
            return "100 roids (scanner!)"
        if level==2:
            return "200 roids"
        if level==3:
            return "300 roids"
        if level==4:
            return "500 roids"
        if level==5:
            return "750 roids"
        if level==6:
            return "Millenium (cue ominous music)"
        if level==7:
            return "1250 rocks"
        if level==8:
            return "1500 rotz"
        if level==9:
            return "Jan 1. 1900"
        if level==10:
            return "2500 stones"
        if level==11:
            return "3000 roids"
        if level==12:
            return "3500 roids"
        if level==13:
            return "4500 roids"
        if level==14:
            return "5500 roids"
        if level==15:
            return "6500 roids"
        if level==16:
            return "top10 or dumb"

