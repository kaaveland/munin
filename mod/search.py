"""
Loadable.Loadable subclass
"""

class search(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,100)
        self.paramre=re.compile(r"^\s+(\S+)")
        self.usage=self.__class__.__name__ + " <alliance|nick>" 
        
    def execute(self,nick,username,host,target,prefix,command,user,access):
        m=self.commandre.search(command)
        if not m:
            return 0
        
        m=self.paramre.search(m.group(1))
        if not m:
            self.client.reply(prefix,nick,target,"Usage: %s" % (self.usage,))
            return 0
        
        # assign param variables
        params=m.group(1)

        if access < self.level:
            self.client.reply(prefix,nick,target,"You do not have enough access to use this command")
            return 0
        
        # do stuff here
        args=('%'+params+'%','%'+params+'%')
        query="SELECT t1.x AS x,t1.y AS y,t1.z AS z,t1.size AS size,t1.score AS score,t1.value AS value,t1.race AS race,t2.alliance AS alliance,t2.nick AS nick,t2.reportchan AS reportchan,t2.comment AS comment"
        query+=" FROM planet_dump AS t1 INNER JOIN planet_canon AS t3 ON t1.id=t3.id"
        query+=" INNER JOIN intel AS t2 ON t3.id=t2.pid"
        query+=" WHERE t1.tick=(SELECT MAX(tick) FROM updates) AND (t2.alliance ILIKE %s OR t2.nick ILIKE %s)"
        self.cursor.execute(query,args)

        i=0
        planets=self.cursor.dictfetchall()
        if not len(planets):
            reply="No planets in intel matching nick or alliance: %s"%(params,)
            self.client.reply(prefix,nick,target,reply)
            return 1
        for p in planets:
            reply="%s:%s:%s (%s)" % (p['x'],p['y'],p['z'],p['race'])
            reply+=" Score: %s Value: %s Size: %s" % (p['score'],p['value'],p['size'])
            if p['nick']:
                reply+=" Nick: %s" % (p['nick'],)
            if p['alliance']:
                reply+=" Alliance: %s" % (p['alliance'],)
            if p['reportchan']:
                reply+=" Reportchan: %s" % (p['reportchan'],)
            if p['comment']:
                reply+=" Comment: %s" % (p['comment'],)
            i+=1
            if i>4 and len(planets)>4:
                reply+=" (Too many results to list, please refine your search)"
                self.client.reply(prefix,nick,target,reply)
                break
            self.client.reply(prefix,nick,target,reply)

                                
        
        return 1
                                                                                                                                            
    def split_opts(self,params):
        param_dict={}
        active_opt=None
        for s in params.split('='):
            if active_opt:
                m=self.optionsre[active_opt].search(s)
                if m:
                    param_dict[active_opt]=m.group(1)
            last_act=active_opt
            for key in self.optionsre.keys():
                if s.endswith(" "+key):
                    active_opt=key
            if active_opt == last_act:
                active_opt=None
        return param_dict
