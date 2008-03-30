"""
Loadable.Loadable subclass
"""

class quitter(loadable.loadable):
    def __init__(self,client,conn,cursor):
        loadable.loadable.__init__(self,client,conn,cursor,1)
        self.commandre=re.compile(r"^"+self.__class__.__name__+"(.*)")
        self.paramre=re.compile(r"^\s+(\S+)")
        self.usage=self.__class__.__name__ + " <nick>"
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
        quit=m.group(1)

        
        # do stuff here
        query="SELECT pnick, quit FROM user_list WHERE pnick ILIKE %s"
        self.cursor.execute(query,('%'+quit+'%',))

        reply=""

        if self.cursor.rowcount == 0:
            reply="'%s' doesn't match any users" % (quit,)
        else:
            r=self.cursor.dictfetchone()
            pnick=r['pnick']
            count=r['quit']
            query="UPDATE user_list SET quit = quit + 1 WHERE pnick = %s"
            self.cursor.execute(query,(pnick,))
            reply="That whining loser %s has now quit %d times." % (pnick,count+1)
        self.client.reply(prefix,nick,target,reply)
        

        return 1
    
                                                                                                                                                          
