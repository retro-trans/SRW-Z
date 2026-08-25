# -*- coding: utf-8 -*-
"""Record 96 - Chiram spacetime device destroyed + Archangel 'Neo Roanoke'."""
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


T = {
15: 'President\n"Durandal, well played..\nTo move to destroy the\nEarth Fed from within\nat this timing.."',
16: 'Wesley\n"For the Fed, the UN\nspanning the whole world\nbecame its undoing."',
17: 'Wesley\n"Citizens learning the\ntruth will likely riot,\nand at worst the Fed\nmay splinter into\nseparate nations."',
18: 'Chiram Soldier\n"The Fed units that had\ninvaded the capital have\nreportedly pulled back."',
19: 'President\n"ZAFT dropped their prized\nnew weapon on them, their\nrear\'s in uproar.. No\nwonder they had to retreat."',
20: 'Wesley\n"As a result, it\'s a\nshame we\'ve ended up\nindebted to Durandal."',
21: 'President\n"Have we..? We may be\nnothing more than pawns\nused in that man\'s\nfarce."',
22: 'Wesley\n"Meaning what,\nexactly, sir?"',
23: 'President\n"Never mind.. Without\nproof, showing hostility\nto the PLANTs now\nis dangerous."',
24: 'President\n"After all, he\'s the man\nof justice exposing the\nEarth Fed\'s corruption."',
25: 'Wesley\n"Haa.."',
26: 'President\n"Return the fleet to the\ncapital. While the\nspacetime device is\nsafe, Chiram won\'t end."',
27: 'President\n"Restart Plan D and\nseize the lead in\nspacetime repair."',
28: 'Wesley\n"Understood.\n..All ships, turn about!"',
29: 'Chiram Soldier\n"Radar contact! A unit\nclosing on us at\nhigh speed!"',
30: 'Wesley\n"A Fed pursuit force!?"',
31: 'Chiram Soldier\n"Match found in the\nspecial-ops reports!\nIt\'s not Fed military!"',
32: 'Asakim\n"..The path to the Taiji..\nOne without the right\nmust not grasp it."',
33: 'President\n"His target is the\nspacetime device!"',
34: 'Wesley\n"Intercept! Protect the\ndevice at all costs!!"',
35: 'Asakim\n"Too slow."',
36: 'Wesley\n"The device!"',
37: 'President\n"What.. Plan D.. the\nworld.. is collapsing.."',
38: 'Asakim\n"This is fine. The frame\nof the multiverse\nsways once more.."',
39: 'Setsuko\n"No.. We were a step\ntoo late again.."',
40: 'Setsuko\n"$n.. We\'re a step behind..\nAt this rate, everything\nwill be too late.."',
41: 'Athena\n"Star 3, explain the\nsituation! Who is\nthat man!?"',
42: 'Setsuko\n"My apologies. I\'ll\npursue that man..\nAsakim Dowin!"',
43: 'Setsuko\n"For details, please ask\n$c\'s\n$F..!"',
44: 'Athena\n"Wait! We\'re not\ndone talking!"',
45: 'Setsuko\n"Then, excuse me!"',
46: 'Athena\n"That woman Setsuko who\nguided us here.. just\nwho on earth is she..?"',
47: 'Olson\n"Athena.. I\'m going too."',
48: 'Athena\n"Huh.."',
49: 'Olson\n"With the spacetime\ndevice destroyed, Plan D\nhas all but failed."',
50: 'Olson\n"If so, the brass will\nagain plan spacetime\nrepair via the Singularity,\nand try to use me\nand Kei."',
51: 'Athena\n"Then let\'s capture Kei\nKatsuragi and secure\nChiram\'s survival.."',
52: 'Olson\n"..I no longer know\nif that is right."',
53: 'Athena\n"Uncle.."',
54: 'Olson\n"So I\'ll go to see Kei.\nAnd think once more\nabout what I ought\nto do."',
55: 'Athena\n"Please wait, Uncle!\nThen I\'ll come with\nyou too!"',
56: 'Olson\n"No. You stay in Chiram\nand gather information."',
57: 'Olson\n"Asakim Dowin, whom that\npilot Setsuko pursues..\nAnd the New Fed\'s\nturmoil.."',
58: 'Olson\n"Things will keep moving.\nI\'m counting on you,\nAthena."',
59: 'Athena\n"Uncle.. I pray for\nyour safety.."',
61: '\u3000\n\u3000\u3000\u3000\u3000\u3000\u301cArchangel, Interior\u301c',
62: 'Neo\n"......."',
63: 'Murrue\n"......."',
64: 'Kira\n"..Is he still asleep?"',
65: 'Murrue\n"When we changed his\nclothes, he opened his\neyes once and named\nhimself Colonel Neo\nRoanoke of the New Earth\nFed 88th Independent\nMobile Corps.."',
66: 'Murrue\n"But the physical data\nfrom the exam matched\nthis ship\'s database\n100%."',
67: 'Cagalli\n"Then..!"',
68: 'Murrue\n"This man is.. the Mwu La\nFlaga we know.. In body,\nat least.."',
69: 'Kira\n"The one called The Storm\nwho delivered Major Flaga\nto us surely knew\nthat too."',
70: 'Jamil\n"Captain Ramius..\nAnd this Major Flaga is?"',
71: 'Murrue\n"He was a crewman of\nthis very Archangel."',
72: 'Murrue\n"Two years ago.. I thought\nhe died in the last\nwar\'s final battle.."',
73: 'Jamil\n(This expression.. So for\nthe captain he was a\nspecial man, then..)',
74: 'Cagalli\n"What does this mean?\nWhat you said about\n\'in body\'.."',
75: 'Murrue\n"That is.."',
76: 'Neo\n"..Listening a while now,\nyou sure say whatever\nyou please.."',
77: 'Neo\n"When did I become\na major?"',
78: 'Kira\n"Ah.."',
79: 'Neo\n"I clearly said colonel.\nDon\'t demote me on a\nwhim just \'cause I\'m\na POW."',
80: 'Murrue\n"A.. ahh.."',
81: 'Neo\n"Wh-what is it.."',
82: 'Neo\n"Love at first sight,\nbeautiful?"',
83: 'Neo\n"She left.. Did I..\nsay something wrong..?"',
84: 'Kira\n"Mwu.."',
85: 'Neo\n"Who\'s Mwu..? Are you\nby chance talking\nabout me?"',
86: 'Jamil\n"This man.. has no\nmemory?"',
87: 'Neo\n"Don\'t be rude. ..Sure,\nmy past is a bit hazy\nin places, but.."',
88: 'Neo\n"I\'ll say it again. I\'m\nColonel Neo Roanoke of\nthe New Earth Fed 88th\nIndependent Mobile Corps."',
89: 'Neo\n"Call me Mwu or Major\nFlaga all you like, I\nhaven\'t a clue what\nyou mean."',
90: 'Cagalli\n"What in the world is\ngoing on.."',
91: 'Kira\n"......."',
92: 'Jamil\n(As a byproduct of research\ninto controlling minds,\nthere\'s memory\nimprinting..)',
93: 'Jamil\n(This man.. has he been\nimprinted with memories\nas Neo Roanoke..?)',
}

T.update({
18: 'Chiram Soldier\n"The Fed units that\ninvaded the capital\nhave pulled back."',
19: 'President\n"ZAFT dropped their prized\nnew weapon on them, their\nrear\'s in uproar.. No\nwonder they retreat."',
23: 'President\n"Never mind.. Without\nproof, hostility to\nthe PLANTs is\ndangerous."',
17: 'Wesley\n"Citizens who learn the\ntruth will riot, and at\nworst the Fed may\nsplinter into nations."',
50: 'Olson\n"If so, the brass will\nagain plan spacetime\nrepair via the Singularity\nand use me and Kei."',
57: 'Olson\n"Asakim Dowin, whom\nSetsuko pursues.. And\nthe New Fed\'s turmoil.."',
69: 'Kira\n"The Storm, who brought\nMajor Flaga to us,\nsurely knew that too."',
87: 'Neo\n"Don\'t be rude. ..Sure,\nmy past is a bit\nhazy, but.."',
24: 'President\n"After all, he\'s the\njust man exposing the\nEarth Fed\'s corruption."',
26: 'President\n"Return the fleet home.\nWhile the spacetime\ndevice is safe, Chiram\nwon\'t end."',
27: 'President\n"Restart Plan D and\nlead the spacetime\nrepair."',
38: 'Asakim\n"This is fine. The\nmultiverse\'s frame\nsways once more.."',
51: 'Athena\n"Then take Kei\nKatsuragi and secure\nChiram\'s survival.."',
65: 'Murrue\n"When we changed his\nclothes, he woke once\nand named himself\nColonel Neo Roanoke of\nthe New Earth Fed 88th\nIndep. Mobile Corps.."',
76: 'Neo\n"..Listening a while,\nyou sure say whatever\nyou please.."',
88: 'Neo\n"I\'ll say it again. I\'m\nColonel Neo Roanoke,\nNew Earth Fed 88th\nIndep. Mobile Corps."',
92: 'Jamil\n(A byproduct of research\ninto mind control..\nmemory imprinting..)',
})

rows = json.load(open(WORK + r'\analysis\rec096_work.json', encoding='utf-8'))
bud = {r['i']: r['budget'] for r in rows}
need = set(bud)
miss = need - set(T)
extra = set(T) - need
over = [(i, bl(T[i]), bud[i]) for i in T if i in bud and bl(T[i]) > bud[i]]
print("rec096: %d/%d rows | missing %s | extra %s | over %s" % (
    len(T), len(need), sorted(miss), sorted(extra), over))
if not miss and not extra and not over:
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record 96 dialogue."""', "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec096_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("  WRITTEN")
