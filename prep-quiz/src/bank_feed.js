// ---------- Feed 13.10: your sentences from the Ledger sessions of 12.10 and 13.10 (approved by Murat 14.10) ----------
// Loaded last, so every item is appended after the existing ones and saved history stays valid.
const FEED_1310={
confused_about:[Y('12.10','I’m quite thoughtful ___ that.','about',['on']),Y('13.10','I’m confused ___ one part.','about',['at'])],
add_to:[Y('12.10','Let’s add it ___ the upcoming chunks.','to',['into']),Y('13.10','I can add my own sentences ___ the practice.','to',['into'])],
put_add:[Y('13.10','I can ___ my own sentences.','add',['put'])],
ask_sb_q:[Y('12.10','I have a second question ___ you.','for',['to'])],
over_time:[Y('12.10','Help me improve them ___ time.','over',['in']),Y('13.10','They turned into a backlog ___ time.','over',['throughout','in'])],
same_about:[Y('13.10','I can say the same ___ my Turkish.','about',['for'])],
for_me:[Y('12.10','The subject was quite unfamiliar ___ me.','to',['for']),Y('12.10','I feel so comfortable ___ this speaking practice.','with',['for'],'"Comfortable with" something you are doing.')],
time_duration:[Y('13.10','It has been aching ___ a while.','for',['from','since'])],
save_for:[Y('12.10','How about saving it ___ another round?','for',['to']),Y('13.10','I can put it off ___ tomorrow.','until|till',['to'],'"Put off" or "delay" something until a time: until tomorrow.')],
rooted_in:[Y('12.10','This is rooted ___ having their own country.','in',['to'])],
no_prep_verbs:[Y('13.10','I can’t promise ___ anything.','∅',['for']),Y('13.10','Does it fit ___ the context?','∅',['in'],'"Fit" takes its object directly: it fits the context.')],
of_not_for:[Y('13.10','I need to increase my knowledge ___ language learning.','of',['for'])],
wait_for:[Y('13.10','I can’t just sit and wait ___ them to fade away.','for',['∅'])],
key_to:[Y('13.10','I don’t have an active solution ___ that.','to',['for'])],
dates_times:[Y('13.10','___ day 16, it began to stumble.','On',['In'])],
on_device:[Y('13.10','I read the sentences ___ my screen.','on',['through'])],
on_my_list:[Y('13.10','It’s already ___ the phrasal verb list.','on',['in'])],
sense_of:[Y('12.10','That was the outcome ___ this meeting.','of',['from'],'"The outcome of" something, like "the result of".')],
adv_among_between:[Y('12.10','This number is very high ___ Turkish people.','among',['for','between'],'Inside a group of people: "among".')],
adv_along:[Y('12.10','The event would be on ___ our trip.','during',['at','along'],'A stretch of time: "during".')]
};
BANK.forEach(p=>{if(FEED_1310[p.k])p.items.push(...FEED_1310[p.k]);});
