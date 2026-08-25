# -*- coding: utf-8 -*-
"""Tighten the 56 over-budget rows in rec068_en.py (Copeland/Bloodman broadcast)."""
import importlib.util as u
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


s = u.spec_from_file_location('m68', 'rec068_en.py')
m = u.module_from_spec(s)
s.loader.exec_module(m)
wk = {r['i']: r for r in json.load(open(WORK + r'\analysis\rec068_work.json', encoding='utf-8'))}

F = {
13: 'Kamille\n"As the Chairman said,\nthe Council of Sages\nstarted this war.."',
84: 'Jerid\n"War\'ll end all right!\nOnce all obstacles\nare cleared!"',
131: 'Citizen\n"That bank\'s chief\naided the Council\nof Sages."',
142: 'Fran\n"You\'re Lady Lili,\nBorjarno ruler\'s\ndaughter, right?"',
146: 'Lili\n"An ex-ruler\'s\ndaughter? How\ndiligent."',
152: 'Lili\n"I mean how people\nchoose to be."',
182: 'Kuzemi\n"Too late already.\nBy the time Ageha was\nreported.. by the time\nchaos took the world.."',
183: 'Kuzemi\n"Humanity had\noverrun this earth"',
192: 'Coda\n"Since I freed you\nfrom your cell, I knew\nit might come\nto this."',
197: 'Dewey\n"The Kte-class are just\na gateway. Soon, things\nlike antibodies appear,\nand mankind\'s\nextermination begins."',
200: 'Coda\n"The powerless can\'t\nclaim supremacy."',
204: 'Scirocco\n"Ambition..? I can\'t\nentrust the world to\none who speaks of\nthings in such\nvulgar terms."',
209: 'Scirocco\n"They\'ll wager the\nworld\'s rule and fight\nto the last against\nany and all,\nno doubt."',
210: 'Jamitov\n"Hawks, the very\nembodiment of lust for\npower. To them, self-\npreservation and fury\noutweigh what comes\nafter."',
220: 'Scirocco\n"For you, glorious first\npresident of the New\nEarth Fed, I\'ve a\nfitting curtain call."',
231: 'Tetsuya\n"I never said that.\n..But if their path\ndiffers from ours,\nnothing can be done."',
234: '$n\n"Besides.. we can\'t\naccept them, same as\nthey can\'t accept us.."',
235: '$n\n"Those people.. they\'ve\nraided ZAFT bases\neverywhere, dragging\ntowns into their\nfights.."',
237: 'Kappei\n"But hold on. In the\nChiram battle, those\nguys fought the\nFederation too."',
239: 'Tetsuya\n"What do you mean,\nLieutenant Reeven?"',
241: 'Reeven\n"And the anti-Council\nfaction will likely\nseize this chance to\ngo on the offensive."',
248: 'Reeven\n"Unfortunately, no..\nShuran\'s investigating\nhard too, but given\nthings, it\'s proving\ndifficult.."',
249: 'Reeven\n"General Edel, who runs\nour supply lines, is\nmost likely under house\narrest by the\nopposition."',
250: 'Roberto\n"So, Lieutenant, you\nthink the Gekko-Goh and\nFreeden aid that\nopposition?"',
253: 'Uchuta\n"Everyone! The N.Fed\'s\nmaking a big\nannouncement\nthrough the UN!"',
255: 'Sayaka\n"A big announcement..\nabout the spacetime\ncollapse, maybe?"',
257: 'Copeland\n"To all people of the\nEarth Sphere. I am\nJoseph Copeland, New\nEarth Fed President."',
258: 'Copeland\n"As you know, PLANT\'s\nChairman Gilbert\nDurandal revealed the\nNew Earth Fed\'s supreme\ndecision-making body.."',
259: 'Copeland\n"Known as the Council\nof Sages, now made\npublic to the whole\nworld."',
261: 'Copeland\n"I admit the Council\'s\nmembers, myself included,\nmade extralegal calls in\npolitics, military and\neconomy on private\nviews.."',
263: 'Copeland\n"Council members and\ntheir aides are already\narrested or punished,\nand the New Earth Fed\nis now being\nreformed."',
266: 'Copeland\n"From here I entrust\nfull authority to him,\nand pray with you all\nfor order and peace to\nreturn soon."',
269: 'Bloodman\n"As a Federal Congress\nmember, I find this\naffair deeply regret-\ntable, and will pursue\nthe Council of Sages\'\nresponsibility anew."',
270: 'Bloodman\n"The recent Chiram\ninvasion, too, was the\nCouncil\'s doing. On this,\nthe new government will\napologize to Chiram and\npledge unchanged\nfriendship."',
271: 'Bloodman\n"In fact, as anti-\nCouncil members, we sent\nour own independent\nspecial forces against\nthat invasion."',
277: 'Bloodman\n"As part of our anti-\nCouncil faction, they\nsaved Orb\'s Rep from\nbecoming a tool of\npolitical marriage.."',
278: 'Bloodman\n"In the recent Chiram\ninvasion too, they and\ntheir allies stopped\nthe force the Council\nsent."',
279: 'Lunamaria\n"Those $c people\nthere.. they really\nwere with the\nFederation!"',
286: 'Reeven\n"At this point, even\nsetting aside emotional\nstuff like Blue Cosmos,\na simple ceasefire\nwon\'t come easy.."',
287: 'Kouji\n"So Ryo\'s group and the\nGekko-Goh were helping\nthe Archangel this\nwhole time.."',
293: 'Bloodman\n"For the peace and\nsafety of all citizens,\nthe New Earth Fed\nwill fight!"',
300: 'Emma\n"So someone\'s pulling\nthe strings behind\nthis?"',
301: 'Amuro\n"I can\'t see it any\nother way. This whole\nannouncement may be\nhis staged farce."',
302: '$n\n"So he used Chairman\nDurandal\'s announcement\nto pull off this\ncoup.."',
305: 'Bloodman\n"The New Earth Fed\nalone is mankind\'s\nunifying will, the one\ntrue leader to guide\nthis chaotic world\nrightly!"',
310: 'Basque\n"I won\'t let Scirocco\nand Dewey have their\nway!"',
316: 'Jamaican\n"Colonel Basque.. an\nincoming transmission\nfrom someone calling\nthemselves the Frost\nBrothers."',
318: 'Jamaican\n"They say they\'ll join\nus, bringing valuable\ninfo as a gift."',
319: 'Basque\n"Hmph.. missed their\nride with Scirocco,\ndid they. Fine, send\nthe rendezvous point."',
332: 'Arthur\n"I hear LOGOS forces\nare holed up in bases\neverywhere, still\nresisting the regular\narmy."',
333: 'Arthur\n"The Chairman declared\nwar on the Council as\nmankind\'s enemy, but\ntheir opposition says\nthey\'ll keep warring\nwith PLANT.."',
334: 'Meyrin\n"So in the end,\nboth are our enemies.."',
335: 'Arthur\n"Sigh.. our troubles\nare far from over.."',
339: 'Talia\n"..With formal orders\ngiven, no need to\nhesitate if we meet\nthem in battle."',
342: 'Meyrin\n"Detecting a force\nnearing us! This\nsignature.. it\'s the\nFederation!"',
343: 'Talia\n"Seems we neared\nN.Fed territory.."',
}

F.update({
197: 'Dewey\n"The Kte-class are just\na gateway. Soon, things\nlike antibodies appear,\nand mankind\'s\ncleansing begins."',
210: 'Jamitov\n"Hawks, the embodiment\nof lust for power. To\nthem, self-preservation\nand fury outweigh the\naftermath."',
234: '$n\n"Besides.. we can\'t\naccept them, nor\nthey us.."',
237: 'Kappei\n"But wait. In the\nChiram battle, those\nguys fought the\nFederation too."',
255: 'Sayaka\n"A big announcement..\nabout the spacetime\ncollapse?"',
261: 'Copeland\n"I admit Council\nmembers, myself included,\nmade extralegal calls in\npolitics, military and\neconomy on private\nviews.."',
269: 'Bloodman\n"As a Congress member,\nI find this affair\ndeeply regrettable, and\nwill pursue the\nCouncil\'s responsibility\nanew."',
270: 'Bloodman\n"The recent Chiram\ninvasion, too, was the\nCouncil\'s doing. The new\ngovernment will apologize\nto Chiram and pledge\nunchanged friendship."',
277: 'Bloodman\n"As part of our anti-\nCouncil faction, they\nsaved Orb\'s Rep from\na political-marriage\nploy.."',
278: 'Bloodman\n"In the recent Chiram\ninvasion too, they and\nallies stopped the\nCouncil\'s force."',
286: 'Reeven\n"At this point, even\nsetting aside feelings\nlike Blue Cosmos, a\nsimple ceasefire\nwon\'t come easy.."',
287: 'Kouji\n"So Ryo\'s group and the\nGekko-Goh aided the\nArchangel all along.."',
293: 'Bloodman\n"For the peace and\nsafety of all, the\nNew Earth Fed\nwill fight!"',
300: 'Emma\n"So someone\'s pulling\nstrings behind this?"',
316: 'Jamaican\n"Colonel Basque.. a\ntransmission from ones\ncalling themselves the\nFrost Brothers."',
332: 'Arthur\n"I hear LOGOS forces\nare holed up in bases\neverywhere, still\nresisting the army."',
333: 'Arthur\n"The Chairman declared\nwar on the Council as\nmankind\'s foe, but\ntheir opposition says\nthey\'ll keep warring\nwith PLANT.."',
335: 'Arthur\n"Sigh.. our troubles\nare far from over."',
339: 'Talia\n"..With orders given,\nno need to hesitate\nif we meet them\nin battle."',
})

for i, t in F.items():
    m.T[i] = t

lines = ["# -*- coding: utf-8 -*-", '"""Stage record 68 dialogue."""', "", "T = {"]
for k in sorted(m.T):
    lines.append("    %d: %r," % (k, m.T[k]))
lines.append("}")
open("rec068_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
over = [(i, bl(m.T[i]), wk[i]['budget']) for i in m.T if i in wk and bl(m.T[i]) > wk[i]['budget']]
print("rec068 over now (%d):" % len(over), over)
