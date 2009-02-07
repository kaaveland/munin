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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA 
 
# This work is Copyright (C)2006 by Andreas Jacobsen  
# Individual portions may be copyright by individual contributors, and

# are included in this collective work with permission of the copyright  
# owners. 



class prop(loadable.loadable):
    """ 
    foo 
    """ 
    def __init__(self,conn,cursor):
        loadable.loadable.__init__(self,conn,cursor,100)
        self.commandre=re.compile(r"^"+self.__class__.__name__+"(.*)")
        self.paramre=re.compile(r"^\s+(invite|kick|list|show|vote|expire|cancel|recent|search)(.*)")
        self.invite_kickre=re.compile(r"^\s+(\S+)(\s+(\S.*))")
        self.votere=re.compile(r"^\s+(\d+)\s+(yes|no|abstain)(\s+(\d+))?")
        self.usage=self.__class__.__name__ + " [<invite|kick> <pnick> <comment>] | [list] | [vote <number> <yes|no|abstain> [carebears]] | [expire <number>] | [show <number>] | [cancel <number>] | [recent] | [search <pnick>]"
        self.MIN_WAIT=7
	self.helptext=["A proposition is a vote to do something. For now, you can raise propositions to invite or kick someone. Once raised the proposition will stand until you expire it.  Make sure you give everyone time to have their say.",
                       "Votes for and against a proposition are made using carebears. You must have at least 1 carebear to vote. You can bid as many carebears as you want, and if you lose, you'll be compensated this many carebears for being outvoted. If you win, you'll get some back, but I'll take enough to compensate the losers."]

    def execute(self,nick,username,host,target,prefix,command,user,access,irc_msg):
        m=self.commandre.search(command)
        if not m:
            return 0

        if access < self.level:
            irc_msg.reply("You do not have enough access to use this command")
            return 0

        u=self.load_user(user,prefix,nick,target)
        if not u: return 0
        
        m=self.paramre.search(m.group(1))
        if not m:
            irc_msg.reply("Usage: %s" % (self.usage,))
            return 0
        
        # assign param variables 
        prop_type=m.group(1)

        if prop_type.lower() == 'invite':
            m=self.match_or_usage(prefix,nick,target,self.invite_kickre,m.group(2))
            if not m: return 1
            if self.command_not_used_in_home(prefix,nick,target,self.__class__.__name__ + " invite"): return 1
            
            person=m.group(1)
            comment=m.group(3)
            self.process_invite_proposal(prefix,nick,target,u,person,comment)
            
        elif prop_type.lower() == 'kick':
            m=self.match_or_usage(prefix,nick,target,self.invite_kickre,m.group(2))
            if not m: return 1
            if self.command_not_used_in_home(prefix,nick,target,self.__class__.__name__ + " kick"): return 1
            
            person=m.group(1)
            comment=m.group(3)
            self.process_kick_proposal(prefix,nick,target,u,person,comment)
            
        elif prop_type.lower() == 'list':
            self.process_list_all_proposals(prefix,nick,target,u)

        elif prop_type.lower() == 'show':
            m=self.match_or_usage(prefix,nick,target,re.compile(r"^\s*(\d+)"),m.group(2))
            if not m: return 1
            prop_id=int(m.group(1))
            self.process_show_proposal(prefix,nick,target,u,prop_id)
        elif prop_type.lower() == 'vote':
            m=self.match_or_usage(prefix,nick,target,self.votere,m.group(2))
            if not m: return 1

            prop_id=int(m.group(1))
            vote=m.group(2)
            carebears=m.group(3)
            if carebears: carebears=int(carebears)
            self.process_vote_proposal(prefix,nick,target,u,prop_id,vote,carebears)
        elif prop_type.lower() == 'expire':
            m=self.match_or_usage(prefix,nick,target,re.compile(r"\s*(\d+)"),m.group(2))
            if not m: return 1
            if self.command_not_used_in_home(prefix,nick,target,self.__class__.__name__ + " expire"): return 1
            
            prop_id=int(m.group(1))
            self.process_expire_proposal(prefix,nick,target,u,prop_id)

        elif prop_type.lower() == 'cancel':
            m=self.match_or_usage(prefix,nick,target,re.compile(r"\s*(\d+)"),m.group(2))
            if not m: return 1
            if self.command_not_used_in_home(prefix, nick, target, self.__class__.__name__ + " cancel"): return 1

            prop_id=int(m.group(1))
            self.process_cancel_proposal(prefix, nick, target, u, prop_id)
        elif prop_type.lower() == 'recent':
            self.process_recent_proposal(prefix,nick,target,u)
            pass

        elif prop_type.lower() == 'search':
            m=self.match_or_usage(prefix,nick,target,re.compile(r"\s*(\S+)"),m.group(2))
            if not m: return 1
            self.process_search_proposal(prefix,nick,target,u,m.group(1))
        return 1
    
    def process_invite_proposal(self,prefix,nick,target,user,person,comment):
        if self.is_member(person):
            irc_msg.reply("Stupid %s, that wanker %s is already a member."%(user.pnick,person))
            return 1
        if self.is_already_proposed_invite(person):
            irc_msg.reply("Silly %s, there's already a proposal to invite %s."%(user.pnick,person))
            return 1
        last_comp=self.was_recently_proposed('invite',person)
        prop_id=self.create_invite_proposal(user,person,comment,last_comp)
        reply="%s created a new proposition (nr. %d) to invite %s." %(user.pnick,prop_id,person)
        reply+=" When people have been given a fair shot at voting you can call a count using !prop expire %d."%(prop_id,)
        if last_comp > 0:
            reply+=" Due to previous failures I'm voting no with %d %s on this vote."%(last_comp,self.pluralize(last_comp,'carebear'))
        irc_msg.reply(reply)

    def process_kick_proposal(self,prefix,nick,target,user,person,comment):
        p=self.load_user_from_pnick(person)
        if person.lower() == "munin".lower():
            irc_msg.reply("I'll peck your eyes out, cunt.")
            return 1
        if not p:
            irc_msg.reply("Stupid %s, you can't kick %s, they're not a member."%(user.pnick,person))
            return 1
        if self.is_already_proposed_kick(p.id):
            irc_msg.reply("Silly %s, there's already a proposition to kick %s."%(user.pnick,p.pnick))
            return 1
        last_comp=self.was_recently_proposed('kick',p.id)
        prop_id=self.create_kick_proposal(user,p,comment,last_comp)
        reply="%s created a new proposition (nr. %d) to kick %s."%(user.pnick,prop_id,p.pnick)
        reply+=" When people have had a fair shot at voting you can call a count using !prop expire %d."%(prop_id,)
        if last_comp > 0:
            reply+=" Due to previous failures I'm voting no with %d %s on this vote."%(last_comp,self.pluralize(last_comp,'carebear'))
        irc_msg.reply( reply)

    def process_list_all_proposals(self,prefix,nick,target,user):
        query="SELECT t1.id AS id, t1.person AS person, 'invite' AS prop_type FROM invite_proposal AS t1 WHERE t1.active UNION ("
        query+=" SELECT t2.id AS id, t3.pnick AS person, 'kick' AS prop_type FROM kick_proposal AS t2"
        query+=" INNER JOIN user_list AS t3 ON t2.person_id=t3.id WHERE t2.active)"
        self.cursor.execute(query,())
        a=[]
        for r in self.cursor.dictfetchall():
            a.append("%d: %s %s"%(r['id'],r['prop_type'],r['person']))
        reply="Propositions currently being voted on: %s"%(string.join(a, ", "),)
        irc_msg.reply(reply)

    def process_show_proposal(self,prefix,nick,target,u,prop_id):
        r=self.find_single_prop_by_id(prop_id)
        if not r:
            reply="No proposition number %d exists."%(prop_id,)
            irc_msg.reply(reply)
            return
        
        age=DateTime.Age(DateTime.now(),r['created']).days
        reply="proposition %d (%d %s old): %s %s. %s commented '%s'."%(r['id'],age,self.pluralize(age,"day"),
                                                                       r['prop_type'],r['person'],r['proposer'],
                                                                       r['comment_text'])
        if not bool(r['active']):
            reply+=" This prop expired %d days ago."%(DateTime.Age(DateTime.now(),r['closed']).days,)
        elif r['padding'] > 0:
            reply+=" Due to previous failures I'm voting no on this prop with %d %s"%(r['padding'],self.pluralize(r['padding'],'carebear'))
        if target[0] != "#" or prefix == irc_msg.client.NOTICE_PREFIX or prefix == irc_msg.client.PRIVATE_PREFIX:
            query="SELECT vote,carebears FROM prop_vote"
            query+=" WHERE prop_id=%d AND voter_id=%d"
            self.cursor.execute(query,(prop_id,u.id))
            s=self.cursor.dictfetchone()
            if s:
                reply+=" You are currently voting '%s'"%(s['vote'],)
                if s['vote'] != 'abstain':
                    reply+=" with %d carebears"%(s['carebears'],)
                reply+=" on this proposition." 
            else:
                reply+=" You are not currently voting on this proposition."
        irc_msg.reply(reply)
        if not bool(r['active']):
            reply=""
            (voters, yes, no) = self.get_voters_for_prop(prop_id)
            (winners,losers,winning_total,losing_total)=self.get_winners_and_losers(voters,yes,no)
            reply+="The prop"
            if yes > no:
                reply+=" passed by a vote of %d to %d"%(yes,no)
            else:
                reply+=" failed by a vote of %d to %d"%(no,yes)
            reply+=". The voters in favor were ("

            pretty_print=lambda x:"%s (%d)"%(x['pnick'],x['carebears'])
            reply+=string.join(map(pretty_print,voters['yes']),', ')
            reply+=") and against ("
            reply+=string.join(map(pretty_print,voters['no']),', ')
            if r['padding'] > 0:
                reply+=", Munin (%d)"%(r['padding'],)            
            reply+=")"
            irc_msg.reply(reply)
            pass


    def process_vote_proposal(self,prefix,nick,target,u,prop_id,vote,carebears):
        # todo ensure prop is active
        if not carebears:
            if vote == 'abstain':
                carebears=0
            else:
                carebears=1
        prop=self.find_single_prop_by_id(prop_id)
        if not prop:
            irc_msg.reply("No proposition number %d exists (idiot)."%(prop_id,))
            return

        if not bool(prop['active']):
            irc_msg.reply("You can't vote on prop %d, it's expired."%(prop_id,))
            return
        if prop['proposer'].lower() == u.pnick.lower():
            reply="Arbitrary Munin rule #167: No voting on your own props."
            irc_msg.reply(reply)
            return
        
        query="SELECT id,vote,carebears, prop_id FROM prop_vote"
        query+=" WHERE prop_id=%d AND voter_id=%d"
        self.cursor.execute(query,(prop_id,u.id))
        old_vote=self.cursor.dictfetchone()
        cost=0
        if old_vote:
            cost=carebears-old_vote['carebears']
        else:
            cost=carebears

        if cost > u.carebears:
            irc_msg.reply("You don't have enough carebears to cover that vote. Your vote would have required %d, but you only have %d carebears."%(cost,u.carebears))
            return

        query="UPDATE user_list SET carebears = carebears - %d WHERE id = %d"
        self.cursor.execute(query,(cost,u.id))
        if old_vote:
            query="DELETE FROM prop_vote WHERE id=%d AND voter_id=%d"
            self.cursor.execute(query,(old_vote['id'],u.id))

        query="INSERT INTO prop_vote (vote,carebears,prop_id,voter_id) VALUES (%s,%d,%d,%d)"
        self.cursor.execute(query,(vote,carebears,prop['id'],u.id))
        if old_vote:
            reply="Changed your vote on proposition %d from %s"%(prop['id'],old_vote['vote'])
            if old_vote['vote'] != 'abstain':
                reply+=" (%d)"%(old_vote['carebears'],)
            reply+=" to %s"%(vote,)
            if vote != 'abstain':
                reply+=" with %d carebears"%(carebears,)
            reply+="."
        else:
            reply="Set your vote on proposition %d as %s"%(prop['id'],vote)
            if vote != 'abstain':
                reply+=" with %d carebears"%(carebears,)
            reply+="."
        irc_msg.reply(reply)

    def process_expire_proposal(self,prefix,nick,target,u,prop_id):
        prop=self.find_single_prop_by_id(prop_id)
        if not prop:
            irc_msg.reply("No proposition number %d exists (idiot)."%(prop_id,))
            return
        if u.pnick.lower() != prop['proposer'].lower():
            irc_msg.reply("Only %s may expire proposition %d."%(prop['proposer'],prop['id']))
            return
        #tally votes for and against
        (voters, yes, no) = self.get_voters_for_prop(prop_id)
        if prop['padding']:
            no+=prop['padding']
        (winners,losers,winning_total,losing_total)=self.get_winners_and_losers(voters,yes,no)

        for l in losers:
            query="UPDATE user_list SET carebears = carebears + %d"
            query+=" WHERE id=%d"
            modifier=[prop['padding'],0][yes>no]
            total_mod=[0,prop['padding']][yes>no]
            r=((losing_total-modifier)*int(l['carebears']))/losing_total
            if yes>no and prop['padding']>0:
                r+=(prop['padding']*int(l['carebears']))/prop['padding']
            print "Paying out %d with %d carebears (orig %d) for w: %d and l: %d"%(l['voter_id'],l['carebears']+r,l['carebears'],winning_total,losing_total)
            self.add_return([voters['yes'],voters['no']][yes>no],l['voter_id'],l['carebears']+r)
            self.cursor.execute(query,(l['carebears']+r, l['voter_id']))

        for w in winners:
            query="UPDATE user_list SET carebears = carebears + %d"
            query+=" WHERE id=%d"
            modifier=[prop['padding'],0][yes>no]
            r=((winning_total-losing_total)*int(w['carebears']))/(winning_total-modifier)
            print "Reimbursing %d with %d carebears (orig %d) for w: %d and l: %d"%(w['voter_id'],r,w['carebears'],winning_total,losing_total)
            self.add_return([voters['no'],voters['yes']][yes>no],w['voter_id'],r)
            self.cursor.execute(query,(r, w['voter_id']))
        
        age=DateTime.Age(DateTime.now(),prop['created']).days
        reply="The proposition raised by %s %d %s ago to %s %s has"%(prop['proposer'],age,self.pluralize(age,"day"),prop['prop_type'],prop['person'])
        if yes > no:
            reply+=" passed"
        else:
            reply+=" failed"
        reply+=" with %d carebears for and %d against."%(yes,no)
        reply+=" In favor: "

        pretty_print=lambda x:"%s (%d->%d)"%(x['pnick'],x['carebears'],x['return'])
        reply+=string.join(map(pretty_print,voters['yes']),', ')
        reply+=" Against: "
        reply+=string.join(map(pretty_print,voters['no']),', ')
        if prop['padding'] > 0:
            reply+=", Munin (%d)"%(prop['padding'],)
        irc_msg.client.privmsg("#%s"%(self.config.get('Auth','home'),),reply)

        if prop['prop_type'] == 'kick' and yes > no:
            self.do_kick(prefix,nick,target,prop,yes,no)
        elif prop['prop_type'] == 'invite' and yes > no:
            self.do_invite(prefix,nick,target,prop)

        query="UPDATE %s_proposal SET active = FALSE, closed = NOW()" % (prop['prop_type'],)
        query+=", vote_result=%s,compensation=%d"
        query+=" WHERE id=%d"
        self.cursor.execute(query,(['no','yes'][yes>no],losing_total,prop['id']))

    def process_cancel_proposal(self, prefix, nick, target, u, prop_id):
        prop=self.find_single_prop_by_id(prop_id)
        if not prop:
            irc_msg.reply("No proposition number %d exists (idiot)."%(prop_id,))
            return
        if u.pnick.lower() != prop['proposer']:
            irc_msg.reply("Only %s may expire proposition %d."%(prop['proposer'],prop['id']))
            return

        (voters, yes, no)=self.get_voters_for_prop(prop_id)

        all_voters=[]
        all_voters.extend(voters['yes'])
        all_voters.extend(voters['no'])
        for v in all_voters:
            query="UPDATE user_list SET carebears = carebears + %d WHERE id=%d"
            self.cursor.execute(query,(v['carebears'],v['voter_id']))

        query="DELETE FROM prop_vote WHERE prop_id=%d"
        self.cursor.execute(query,(prop['id'],))

        query="DELETE FROM %s_proposal " %(prop['prop_type'],)
        query+=" WHERE id=%d"
        self.cursor.execute(query,(prop['id'],))

        reply="Cancelled proposal %d to %s %s. Reimbursing voters in favor (" %(prop['id'],prop['prop_type'],prop['person'])

        pretty_print=lambda x:"%s (%d)"%(x['pnick'],x['carebears'])
        reply+=string.join(map(pretty_print,voters['yes']),', ')
        reply+=") and against ("
        reply+=string.join(map(pretty_print,voters['no']),', ')
        reply+=")"
        irc_msg.client.privmsg("#%s"%(self.config.get('Auth','home'),),reply)
        pass

    def process_recent_proposal(self,prefix,nick,target,u):
        query="SELECT t1.id AS id, t1.person AS person, 'invite' AS prop_type, t1.vote_result AS vote_result FROM invite_proposal AS t1 WHERE NOT t1.active UNION ("
        query+=" SELECT t2.id AS id, t3.pnick AS person, 'kick' AS prop_type, t2.vote_result AS vote_result FROM kick_proposal AS t2"
        query+=" INNER JOIN user_list AS t3 ON t2.person_id=t3.id WHERE NOT t2.active) ORDER BY id DESC LIMIT 10"
        self.cursor.execute(query,())
        a=[]
        for r in self.cursor.dictfetchall():
            a.append("%d: %s %s %s"%(r['id'],r['prop_type'],r['person'],r['vote_result'][0].upper() if r['vote_result'] else ""))
        reply="Recently expired propositions: %s"%(string.join(a, ", "),)
        irc_msg.reply(reply)
        
        pass

    def process_search_proposal(self,prefix,nick,target,u,search):
        query="SELECT id, prop_type, person, vote_result FROM ("
        query+=" SELECT t1.id AS id, 'invite' AS prop_type, t1.person AS person, t1.vote_result AS vote_result"
        query+="  FROM invite_proposal AS t1 UNION ("
        query+=" SELECT t3.id AS id, 'kick' AS prop_type, t5.pnick AS person, t3.vote_result AS vote_result"
        query+="  FROM kick_proposal AS t3 INNER JOIN user_list AS t5 ON t3.person_id=t5.id)) "
        query+="AS t6 WHERE t6.person ILIKE %s ORDER BY id DESC LIMIT 10"
        self.cursor.execute(query,("%"+search+"%",))
        a=[]
        for r in self.cursor.dictfetchall():
            a.append("%d: %s %s %s"%(r['id'],r['prop_type'],r['person'],r['vote_result'][0].upper() if r['vote_result'] else "",))
        reply="Propositions matching '%s': %s"%(search,string.join(a, ", "),)
        irc_msg.reply(reply)
        
        pass

    def get_winners_and_losers(self,voters,yes,no):
        if yes > no:
            losers=voters['no']
            winners=voters['yes']
            winning_total=yes
            losing_total=no
        else:
            winners=voters['no']
            losers=voters['yes']
            winning_total=no
            losing_total=yes
        return (winners,losers,winning_total,losing_total)

    def get_voters_for_prop(self,prop_id):
        query="SELECT t1.vote AS vote,t1.carebears AS carebears"
        query+=", t1.prop_id AS prop_idd,t1.voter_id AS voter_id,t2.pnick AS pnick"
        query+=" FROM prop_vote AS t1"
        query+=" INNER JOIN user_list AS t2 ON t1.voter_id=t2.id"
        query+=" WHERE prop_id=%d"
        self.cursor.execute(query,(prop_id,))
        voters={}
        voters['yes']=[]
        voters['no']=[]
        voters['abstain']=[]
        yes=0;no=0
        
        for r in self.cursor.dictfetchall():
            if r['vote'] == 'yes':
                yes+=r['carebears']
                voters['yes'].append(r)
            elif r['vote'] == 'no':
                no+=r['carebears']
                voters['no'].append(r)
            elif r['vote'] == 'abstain':
                voters['abstain'].append(r)
        return (voters, yes, no)

    def do_kick(self,prefix,nick,target,prop,yes,no):
        idiot=self.load_user_from_pnick(prop['person'])
        query="UPDATE user_list SET userlevel = 1 WHERE id = %s"
        self.cursor.execute(query,(idiot.id,))
        irc_msg.client.privmsg('p','remuser #%s %s'%(self.config.get('Auth', 'home'), idiot.pnick,))
        irc_msg.client.privmsg('p',"ban #%s *!*@%s.users.netgamers.org %s"%(self.config.get('Auth', 'home'), idiot.pnick,prop['comment_text']))

        irc_msg.client.privmsg('p',"note send %s A proposition to kick you from %s has been raised by %s with reason '%s' and passed by a vote of %d to %d."%(idiot.pnick,self.config.get('Auth','alliance'),prop['proposer'],prop['comment_text'],yes,no))


        reply="%s has been reduced to level 1 and removed from #%s."%(idiot.pnick,self.config.get('Auth','home'))
        irc_msg.client.privmsg('#%s'%(self.config.get('Auth','home')),reply)

    def do_invite(self,prefix,nick,target,prop):
        gimp=self.load_user_from_pnick(prop['person'])
        if not gimp or gimp.pnick.lower() != prop['person'].lower():
            query="INSERT INTO user_list (userlevel,sponsor,pnick) VALUES (100,%s,%s)"
        else:
            query="UPDATE user_list SET userlevel = 100, sponsor=%s WHERE pnick ilike %s"
        self.cursor.execute(query,(prop['proposer'],prop['person']))
        irc_msg.client.privmsg('P',"adduser #%s %s 399" %(self.config.get('Auth', 'home'), prop['person'],));
        irc_msg.client.privmsg('P',"modinfo #%s automode %s op" %(self.config.get('Auth', 'home'), prop['person'],));


        reply="%s has been added to #%s and given level 100 access to me."%(prop['person'],self.config.get('Auth','home'))
        irc_msg.client.privmsg('#%s'%(self.config.get('Auth','home')),reply)

    def add_return(self,voter_list,voter_id,ret_sum):
        for v in voter_list:
            if v['voter_id'] == voter_id:
                v['return'] = ret_sum
                return
        raise Exception("%d does not match any voters in list '%s'"%(voter_id,map(lambda x: "%d"%(x['voter_id'],),voter_list)))
            
    
    def find_single_prop_by_id(self,prop_id):
        query="SELECT id, prop_type, proposer, person, created, padding, comment_text, active, closed FROM ("
        query+="SELECT t1.id AS id, 'invite' AS prop_type, t2.pnick AS proposer, t1.person AS person, t1.padding AS padding, t1.created AS created,"
        query+=" t1.comment_text AS comment_text, t1.active AS active, t1.closed AS closed"
        query+=" FROM invite_proposal AS t1 INNER JOIN user_list AS t2 ON t1.proposer_id=t2.id UNION ("
        query+=" SELECT t3.id AS id, 'kick' AS prop_type, t4.pnick AS proposer, t5.pnick AS person, t3.padding AS padding, t3.created AS created,"
        query+=" t3.comment_text AS comment_text, t3.active AS active, t3.closed AS closed"
        query+=" FROM kick_proposal AS t3"
        query+=" INNER JOIN user_list AS t4 ON t3.proposer_id=t4.id"
        query+=" INNER JOIN user_list AS t5 ON t3.person_id=t5.id)) AS t6 WHERE t6.id=%d"
        
        self.cursor.execute(query,(prop_id,))
        return self.cursor.dictfetchone()
    def is_member(self,person):
        query="SELECT id FROM user_list WHERE pnick ilike %s AND userlevel >= 100"
        self.cursor.execute(query,(person,))
        return self.cursor.rowcount > 0 

    def is_already_proposed_invite(self,person):
        query="SELECT id FROM invite_proposal WHERE person ilike %s AND active"
        self.cursor.execute(query,(person,))
        return self.cursor.rowcount > 0

    def was_recently_proposed(self,prop_type,person_or_person_id):
        query="SELECT vote_result,compensation FROM %s_proposal WHERE person%s"%(prop_type,['','_id'][prop_type=='kick'])
        query+=" ilike %s AND not active ORDER BY closed DESC"
        self.cursor.execute(query,(person_or_person_id,))
        r=self.cursor.dictfetchone()
        if r and r['vote_result'] != 'yes':
            return r['compensation']
        return 0

    def create_invite_proposal(self,user,person,comment,padding):
        query="INSERT INTO invite_proposal (proposer_id, person, comment_text, padding)"
        query+=" VALUES (%s, %s, %s, %s)"
        self.cursor.execute(query,(user.id,person,comment,padding))
        query="SELECT id FROM invite_proposal WHERE proposer_id = %d AND person = %s AND active ORDER BY created DESC"
        self.cursor.execute(query,(user.id,person))
        return self.cursor.dictfetchone()['id']

    def create_kick_proposal(self,user,person,comment,padding):
        query="INSERT INTO kick_proposal (proposer_id, person_id, comment_text, padding)"
        query+=" VALUES (%s, %s, %s, %s)"
        self.cursor.execute(query,(user.id,person.id,comment,padding))
        query="SELECT id FROM kick_proposal WHERE proposer_id = %d AND person_id = %d AND active ORDER BY created DESC"
        self.cursor.execute(query,(user.id,person.id))
        return self.cursor.dictfetchone()['id']
        
    def is_already_proposed_kick(self,person_id):
        query="SELECT id FROM kick_proposal WHERE person_id = %d AND active" 
        self.cursor.execute(query,(person_id,))
        return self.cursor.rowcount > 0

