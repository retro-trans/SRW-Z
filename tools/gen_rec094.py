# -*- coding: utf-8 -*-
"""Record 94 - Overdevil awakening climax (King Gainer) + Xabungle bazaar bit."""
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


T = {
6: 'Martina\n"So it\'s awakened.. the\ntrue Overdevil..!"',
7: 'Asuham\n"Uoooh! Overdevil!\nAmazing.. I feel\nincredible power!"',
8: 'Asuham\n"This is truly demonic\nenergy! Hyahahahaha!"',
9: 'Kids\n"That fiend! He means\nto make contact with\nthe Overdevil!"',
10: 'Asuham\n"I\'ll obtain it!\nThe ultimate power,\nin my hands!!"',
11: 'Asuham\n"Now, Overdevil!\nGrant me your power!\nAll of it, to me!!"',
12: 'Asuham\n"Why!? Why is there\nno response! Is something\nmissing!?"',
13: 'Kids\n"What\'s missing is your\nsense of taste,\nAsuham~!"',
14: 'Asuham\n"Nnngh! Curse\nyou!!"',
15: 'Kids\n"Oh! You\'re back,\nCynthia!"',
16: 'Martina\n"So that\'s Cynthia.."',
17: 'Kashmar\n"Th-the Overdevil\nis here too!?"',
18: 'Asuham\n"Tch! Interference!"',
19: 'Cynthia\n"Asuham Boone!\nWhat did you do\nto Lord Kids!?"',
20: 'Asuham\n"Silence, charging brat!\nNo use for one who\ncouldn\'t stop the\nhair-clad one!"',
21: 'Cynthia\n"You! I won\'t forgive\nthat, even as a joke!"',
22: 'Asuham\n"I was kind to you\nthinking you had use,\nbut it seems I\nmisjudged!"',
23: 'Cynthia\n"I won\'t forgive you,\nAsuham! I won\'t let the\nlikes of you hurt\nLord Kids!"',
24: 'Cynthia\n"What!?"',
25: 'Kashmar\n"Cynthia Lane!\nLeave this to me!"',
26: 'Kashmar\n"A-ah.. cold.. freezing..\nAh.. my.. diamonds..\nfreezing.."',
27: 'Cynthia\n"!"',
28: 'Cynthia\n"D-don\'t come!!"',
29: 'Cynthia\n"N-no..! I don\'t want\nto become some ice\nqueen from ancient\ntimes!"',
30: 'Kids\n"The Overdevil is taking\nCynthia into itself!"',
31: 'Cynthia\n"A.. ahh.."',
32: 'Martina\n"Cynthia!"',
33: 'Asuham\n"Why, Overdevil!\nWhy do you not\nchoose me!?"',
34: 'Asuham\n"Can I obtain nothing\nI truly desire!?\nNot Karin\'s heart..\nnor Gain\'s power!"',
35: 'Asuham\n"Overdevil! I want you\nfor my purpose!\nIt\'s you I want!!"',
36: 'Asuham\n"Me! I offer you this\nsoul full of despair!"',
37: 'Asuham\n"So please! Hear the\nvoice of this pitiful\nman called Asuham!!"',
38: 'Asuham\n"Ooh! Ooooh!! Do you\nanswer my voice at\nlast!!"',
39: 'Asuham\n"Dominator! Come\nto my side!"',
40: 'Asuham\n"Sing, Overdevil!\nOverfreeze the world!"',
41: 'Kids\n"No good! Asuham! His\nheart\'s been taken\nby the Overdevil!"',
42: 'Kids\n"We\'re pulling out!\nAbandon the Agato\ncrystal!"',
43: 'Martina\n"Cynthia..!"',
44: 'Kids\n"We\'ll regroup! Contact\nevery Siberian Railway\nbranch worldwide!!"',
45: 'Angel\n"So that\'s the Overdevil\'s\ntrue power.. a member of\nthe destroyer legion\nsung of in Black History.."',
46: 'Angel\n"Shadow Angels, Overdevil,\nMoon Butterfly.. The\nworld moves toward\nits end.."',
47: 'Angel\n"The truth that shows\nat the very end..\nit is a great power.."',
48: 'Asuham\n"Hahahahaha! Overdevil,\ncloak the world in a\ndark white night!!"',
49: 'Asuham\n"If you won\'t bend to\nmy will, so be it!"',
50: 'Asuham\n"But you heard the voice\nof my heart! From today\nI am part of you! Let\'s\nfreeze the world\ntogether!!"',
51: 'Asuham\n"Hahahahaha!\nHahahahahahahahaha!!"',
52: 'Cynthia\n(Gainer.. it\'s cold..\nI.. I feel like I\'m\nfreezing..)',
54: 'Jiron\n"What are you doing,\nCattset!? We\'re setting\nout for Chiram right\naway!"',
55: 'Cattset\n"Wait! These past few\ndays of fighting turned\nup tons of finds at\nthe bazaar!"',
56: 'Chil\n"This is no time for that!\nCome on! We\'re going!"',
57: 'Cattset\n"O-okay! Just one..\nlet me buy just one\npart!!"',
58: 'Cattset\n"They were selling a rare\npart for Walker Machines\nover there!"',
59: 'Jiron\n"Hurry it up! Dawdle and\nthe Iron Gear\'ll leave\nyou behind!"',
}

T.update({
21: 'Cynthia\n"You! Not forgiven,\neven as a joke!"',
45: 'Angel\n"That\'s the Overdevil\'s\ntrue power.. a destroyer\nlegion sung of in\nBlack History.."',
46: 'Angel\n"Shadow Angels, Overdevil,\nMoon Butterfly.. The\nworld nears its end.."',
47: 'Angel\n"The truth shown at\nthe very end.. it is\na great power.."',
})

rows = json.load(open(WORK + r'\analysis\rec094_work.json', encoding='utf-8'))
bud = {r['i']: r['budget'] for r in rows}
need = set(bud)
miss = need - set(T)
extra = set(T) - need
over = [(i, bl(T[i]), bud[i]) for i in T if i in bud and bl(T[i]) > bud[i]]
print("rec094: %d/%d rows | missing %s | extra %s | over %s" % (
    len(T), len(need), sorted(miss), sorted(extra), over))
if not miss and not extra and not over:
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record 94 dialogue."""', "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec094_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("  WRITTEN")
