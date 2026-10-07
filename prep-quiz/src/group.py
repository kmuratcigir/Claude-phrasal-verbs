import json,glob,re,sys,collections
L=sys.argv[1]
def norm(s): return re.sub(r'\s+',' ',re.sub(r"\b(uh|um|sorry)\b|[^a-z0-9' ]",' ',s.lower())).strip()
recs=[]
files=sorted(glob.glob(L+'/sessions/*.json'))
order=[f.split('/')[-1][2:10] for f in files]
for f in files:
  s=json.load(open(f)); d=f.split('/')[-1][2:10]
  inter=[it for it in s['interference']['items'] if it.get('type') in('preposition_case','collocation_transfer')]
  for it in inter: recs.append(dict(src='int',date=d,pattern=it['pattern'],quote=it['quote'],fix=it['fix'],tr=it.get('turkish',''),mode=it.get('mode'),impact=it.get('impact'),caught=it.get('caught')))
  nq=[norm(it['quote']) for it in inter]
  for e in s['errors']:
    if e['concept'] not in('err_preposition','err_collocation'): continue
    q=norm(e['quote']); qt=set(q.split())
    dup=False
    for n in nq:
      nt=set(n.split())
      if n and (n in q or q in n or (len(nt)>=2 and len(nt&qt)/len(nt)>=0.75)): dup=True;break
    if not dup: recs.append(dict(src='err',date=d,pattern=e['concept'],quote=e['quote'],fix=e['fix'],tr='',mode=e['mode'],impact=e['impact'],caught=e.get('caught')))
G=[
('mention_discuss',r"mention\w* about|discuss about|research\w* about|referred was"),
('add_to',r"add\w* (\w+ )?into|added into|into my list|into (that|my|the) list|put (\w+ ){0,3}into my list|save (this|it) (\w+ )?into your memory|push next steps into|into my pipeline|into that\b.*add|adding items in it|increase it into|into your notes|put this one into"),
('include_in',r"include \w+ (\w+ )?into|involve\w* (\w+ )?into|involvement into|involves in|put him back into|document them into|into (the )?statistics|into the naturalness"),
('move_on_to',r"moving into|moving in on to|moving onto|move into|before moving"),
('dedicate_to',r"dedicat\w+ (\w+ )?(into|on)|devoting|committed on|committed to stay"),
('on_my_list',r"in (my|our|the|that)( vocab| tracker)? list|in our list|in our, in our"),
('short_on_time',r"short in time"),
('these_days',r"in these days|in these times|days in this week|at those days"),
('over_time',r"\bin time\b"),
('weekends',r"in (the|most of the) weekends?|in the weekend|towards (the )?weekend|towards weekends"),
('of_not_for',r"knowledge for|frequency for|examples? (\w+ )?for|chances (for|to)|way for practicing|test for my|awareness for|possibility turning|precondition of|attempts for"),
('sense_of',r"sense (\w+ )?about|benefits? (\w+ )?about|wrong about|costs about|assessment.*about|developments about|muscles about|reason of"),
('confused_about',r"confused (\w+ )?(\w+ )?on|compulsive on|enthusiastic (\w+ )?on|indecisive on|tension for speaking|lucky to that|insistent|concern"),
('same_about',r"same things? for"),
('same_as',r"same (\w+ )?(\w+ )?with|same uh, window|same thing uh, with|same crew"),
('no_point_in',r"no point"),
('rooted_in',r"rooted|sourced by"),
('save_for',r"save \w+ to|save it to|keep (\w+ ){0,3}to another|save this to"),
('against',r"against to|protecting me against"),
('been_to',r"been in"),
('responsible_for',r"responsible from|in my responsibility|up on our management"),
('specific_to',r"specific for|applied for"),
('pace_at',r"\bpace\b"),
('limit_to',r"limit"),
('begin_lastmin',r"(in|for) the beginning|in the last minutes?|at the middle|at the second part"),
('dates_times',r"in saturday|at 27th|at (\w+ )?28|at 13th|at 27|at the 1st|start in|start on|last in 29|in tomorrow|in the fridays|in this very busy day|in the night|nighttime|earlier time|in both of the days|along the week"),
('good_at',r"good (\w+ ){0,3}on that|better (at )?in\b|good as me on"),
('superior_to',r"superior than"),
('come_across_as',r"come across"),
('basis',r"basis"),
('in_form',r"original form|this shape"),
('angry_with',r"angry to|mad with|bored|from this move|fragile against|close with"),
('remind_of',r"remind\w* (you|me) (the|something)|reminded me something"),
('resonate_with',r"resonate|land on you"),
('key_to',r"key (uh, )?for|answer for your|limit for that"),
('invest_in',r"invest|savings|effort|participated this"),
('paste_into',r"paste"),
('leave_out_of',r"aside|out from|apart from|keep \w+ from normal"),
('have_a_talk',r"make (the|this|a) talk|making this (uh, )?(talk|conversation)|making this uh"),
('do_practice',r"making practice|make a speaking practice|making shadowing|shadowing (uh, )?practices|session is being made"),
('light_verb',r"give (her own|a) (decision|break)|giving the|create\. uh, pressure|rough estimation|quick research|final touches|do a meeting|analysis uh, you make|did our selection|making this holiday|make a score|makes a score|thorough uh, analysis|taking our opinions|having some distance|catch the opportunity|served the goal|receive (uh, )?the call|built a new principle|opened a|reach a meaning|get aware|getting some outcomes"),
('throw_question',r"throw"),
('lift_mood',r"mood"),
('look_into',r"looking after|look after"),
('seek_chase',r"seeking for|chasing for"),
('help_with',r"help me (for|on)"),
('congratulate_on',r"congratulate"),
('scene',r"scene"),
('worth_ing',r"worth to"),
('get_used_to',r"used with"),
('different_from',r"different than"),
('accused_of',r"accus\w+ (by|with)"),
('on_trip_leave',r"in this (uh, )?(business )?trip|annual leave|in a trial|put you in a trial"),
('on_device',r"computer|instagram|nintendo|yas island|at my end|in our side|at my side"),
('wait_for',r"waiting (uh, )?her"),
('swap_for',r"swap|swept|trading off"),
('no_prep_verbs',r"approaching to|contact\w* (with|to)|messaged to|join\w* (uh, )?to|continue (uh, )?to|teaching to|referencing to|head to my home|near to|communicate people|replied him|quit at|participat|knock the door|playing with that game|confrontate|chasing for a meaning|digging it|dig it in|reflection"),
('ask_sb_q',r"ask (the same question|this question|my question|them to me)|question to you|share (\w+ )?(\w+ )?to|give to people|share you|provided me|produce me|force through"),
('for_me',r"to me\b|safer to me|better to you|okay for you|tradition to us|ambiguous for|comfortable for"),
('at_event_place',r"entrance|afterparty|in abroad|to abroad|landed on|in (uh, )?the annual|at some um|obstacle on|on your way|on (english )?native|see on people|filed in|from (the )?previous|from their email|from feedback|from the skill|section 7|instagram application|real-time|plates"),
('struggle_to',r"struggling for|for being a professional|interested in to|wait for making|chances to eating|for having"),
('time_duration',r"since two days|spoken around|take me to another"),
('compared_to',r"compared the|due the|interruptions on|success rate over|exceed it|elaborate on\?|crack on that|which hotel to stay|waste my time less|looked the hotel|take a look on|clutch|from the beginning|got married|apologize|deciding to hotel|started to gymnastic|carve|cross his name|among phrasal|for south korea|trip for"),
]
cg=[(k,re.compile(r)) for k,r in G]
out=collections.defaultdict(list); unc=[]
for r in recs:
  t=norm(r['quote'])+' => '+r['fix'].lower()
  for k,c in cg:
    if c.search(t): out[k].append(r); break
  else: unc.append(r)
json.dump({'order':order,'groups':out,'unc':unc},open(sys.argv[2],'w'),ensure_ascii=False,indent=0)
print(len(recs),'recs',sum(len(v) for v in out.values()),'grouped',len(unc),'unclassified')
for k,_ in G:
  v=out.get(k,[]); ds=sorted({x['date'] for x in v})
  print(f"{k:16} n={len(v):3} sess={len(ds):2} last={ds[-1] if ds else '-'}")
