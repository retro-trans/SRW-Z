# -*- coding: utf-8 -*-
"""Record 81 - Gekkostate flees to South Ameria + Council of Sages scene."""
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


T = {
2: 'Moamu\n"Looks like we shook off\nChiram\'s pursuit force,\nsomehow!"',
3: 'Shaia\n"Yesterday the Fed,\ntoday Chiram.. Tomorrow\nwill ZAFT be chasing us?"',
4: 'Elchi\n"Don\'t be so carefree!\nAnd after we crossed the\nPacific to flee all\nthe way here!"',
5: 'Jamil\n"But South Ameria\nis mostly wasteland."',
6: 'Jamil\n"If we hide ourselves\nwell, we should get\nto rest a while."',
7: 'Elchi\n"You say \'a while,\' but\ndo we have to keep\nliving like this\nforever?"',
8: 'Jamil\n"......."',
9: 'Holland\n"Shut it, Breaker. If you\nhate it, turn tail and\ngo drop dead somewhere\non your own."',
10: 'Elchi\n"What did you say!\nSay that one more\ntime!"',
11: 'Cattset\n"H-hey, miss! Don\'t pick\nfights at a time\nlike this!"',
12: 'Hap\n"Don\'t snap at her either,\nHolland. In a spot like\nthis, no wonder\nshe\'s fed up."',
13: 'Holland\n"Tch.."',
14: 'Holland\n(In the end, these guys\njust don\'t get what\ntheir own role is.)',
15: 'Talho\n"......."',
16: 'Kengo\n"For now, we\'ve got to\nrepair each ship. We\'ll\nsettle down somewhere\nfor once."',
17: 'Sara\n"There seems to be a\nlarge underground cavern\n30 km southwest.\nHow about heading there?"',
18: 'Jamil\n"Hm.. There we could\nshake the enemy\'s\npursuit. ..Holland,\nthat all right?"',
19: 'Holland\n"..No need to check\nwith me every time."',
20: 'Jamil\n"Then we head for the\ncavern. Ships, don\'t\nforget your jamming."',
21: 'Baraya\n"..Chiram refused to\nprovide spacetime\ncontrol tech?"',
22: 'Jamitov\n"Hm.. They mean to push\ntheir Plan D and repair\nspacetime by their\nown power."',
23: 'Kuzemi\n"In other words, to\nremake the world as\nChiram sees fit.."',
24: 'Jamitov\n"That Chiram.. Still\ndragging along the order\nfrom before Break\nthe World."',
25: 'Kuzemi\n"That was a nation built\nby people flung into the\nmultiverse 20 years early\nby the time-axis shift\nof the spacetime break."',
26: 'Kuzemi\n"Its core, I hear, was a\nstate opposed to the\nAtlantic Federation, heart\nof the old Earth Alliance."',
27: 'Jamitov\n"And thanks to their\n20-year advantage, they\nhold spacetime control\ntech that we lack."',
28: 'Djibril\n"Jamitov Hymen! This\nis your blunder, as\nour negotiator!"',
29: 'Djibril\n"Chiram may use Plan D\nas a shield to force\nour submission, you\nknow!"',
30: 'Jamitov\n"Calm down, Djibril.\nEven Chiram has not yet\ncompleted its spacetime\ncontrol system."',
31: 'Jamitov\n"And they surely have no\nconviction that it will\nfully function."',
32: 'Coda\n"Per Dewey\'s report,\nboth Chiram and Emaan\ncontinue to pursue\nthe Singularity."',
33: 'Kuzemi\n"So the Singularity\nbroke from Emaan.."',
34: 'Baraya\n"What do we do? Secure\nthe Singularity as\ninsurance?"',
35: 'Djibril\n"With half-hearted talk\nof capture, we may be\noutdone by Chiram\nor Emaan."',
36: 'Djibril\n"Rather than leave a\nfuture worry, we should\nexterminate it."',
37: 'Jamitov\n"That too is one plan.\n..One ordinary man blind\nto the big picture must\nnot remake the world.."',
38: 'Jamitov\n"For this Council of\nSages exists to decide\nthe world\'s course."',
39: 'Coda\n"Kudan\'s Limit.. That\nwhich would destroy the\nlaws of this multiverse\nmust be stopped at\nall costs."',
40: 'Coda\n"To sever its root, we\napproved that man\'s\nreturn.."',
41: 'Djibril\n"What is the Ageha Squad\ndoing? That Singularity\nmoves together with\nGekkostate too."',
42: 'Djibril\n"Just hurry, catch them,\nand dispose of them\nSingularity and all."',
43: 'Coda\n"Don\'t be so hasty. The\nAgeha Squad\'s aim isn\'t\nGekkostate\'s destruction\nalone."',
44: 'Jamitov\n"Still, we can\'t ignore\nthe Singularity. Colonel\nDewey shall advance the\nplan and also seize the\none named Kei Katsuragi."',
45: 'Jamitov\n"Of course, should capture\nprove hard, killing\nis permitted too."',
46: 'Coda\n"Understood. I\'ll order\nDewey accordingly."',
47: 'Kuzemi\n"And what of their\ncurrent movements?"',
48: 'Jamitov\n"To dodge Emaan\'s pursuit,\nthey\'ve fled into\nSouth Ameria."',
49: 'Djibril\n"South Ameria.. Fleeing\ninto a lawless land -\njust what rats\nwould do."',
50: 'Edel\n"......."',
51: 'Jamitov\n"And Chiram, refusing to\naid the Earth Fed, is\nnothing but a nuisance."',
52: 'Djibril\n"A good chance. Let\'s\ndeploy that machine\nagainst Chiram."',
53: 'Edel\n"Please wait. Invading\nChiram at this moment\ngains us nothing."',
54: 'Edel\n"If they have their own\nplan to repair spacetime,\nwe should pool both plans\nand study the best way\nto stop the world\'s\ncollapse."',
55: 'Jamitov\n"Brigadier Edel.. That\ncan be accomplished with\nthe Singularity or\nthe Ageha Squad."',
56: 'Jamitov\n"What we should weigh is\nalready the next stage."',
57: 'Edel\n"But.. if the world\ncollapses, everything\ncomes to nothing."',
58: 'Jamitov\n"Mind your tongue,\nEdel Bernal..!"',
59: 'Kuzemi\n"Chairman Jamitov is\nright. This Council of\nSages exists to rule\nthe multiverse."',
60: 'Coda\n"We let you join, lowest\nseat though it is, valuing\nthe UN\'s work. Know\nyour place."',
61: 'Edel\n"..Yes, sir."',
62: 'Djibril\n(Heh.. A Council of Sages\nbacked by LOGOS\'s wealth\nis, in the end, just\nfor show..)',
63: 'Djibril\n(Someday I\'ll make these\nold men realize that\ntoo..)',
64: 'Jamitov\n"This world will not\nperish. And ruling it,\nguiding people to a\nbetter path, is\nour duty."',
65: 'Jamitov\n"We must not hand this\nworld over to the likes\nof Durandal."',
66: 'Edel\n(A man bound by immediate\ngain has no power to\nsee the future..)',
67: 'Edel\n(The very people here may\nbe those who\'d shut the\nworld in darkness..)',
}

T.update({
2: 'Moamu\n"Looks like we shook off\nChiram\'s pursuit,\nsomehow!"',
19: 'Holland\n"..No need to check\nwith me each time."',
25: 'Kuzemi\n"A nation built by people\nflung into the multiverse\n20 years early by the\nbreak\'s time-axis shift."',
26: 'Kuzemi\n"Its core was a state\nopposed to the Atlantic\nFed, heart of the old\nEarth Alliance."',
36: 'Djibril\n"Rather than leave a\nfuture worry, we\nshould kill it."',
52: 'Djibril\n"A good chance. Let\'s\nsend the machine\nagainst Chiram."',
62: 'Djibril\n(A Council backed by\nLOGOS\'s wealth is, in\nthe end, just for show..)',
66: 'Edel\n(A man bound by gain\nhas no power to see\nthe future..)',
44: 'Jamitov\n"Still, we can\'t ignore\nthe Singularity. Colonel\nDewey shall advance the\nplan and also seize\nKei Katsuragi."',
})

rows = json.load(open(WORK + r'\analysis\rec081_work.json', encoding='utf-8'))
bud = {r['i']: r['budget'] for r in rows}
need = set(bud)
miss = need - set(T)
extra = set(T) - need
over = [(i, bl(T[i]), bud[i]) for i in T if i in bud and bl(T[i]) > bud[i]]
print("rec081: %d/%d rows | missing %s | extra %s | over %s" % (
    len(T), len(need), sorted(miss), sorted(extra), over))
if not miss and not extra and not over:
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record 81 dialogue."""', "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec081_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("  WRITTEN")
