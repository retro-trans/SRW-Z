# -*- coding: utf-8 -*-
"""Record 114 - Shadow Angels (Atlandia) lore scene + Djibril's Requiem attack."""
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


T = {
20: 'Jamaican\n"ZAFT\'s assault force has\ndescended to the\nlunar surface!"',
21: 'Basque\n"Damn you, Djibril!\nHurry it up!"',
22: 'Djibril\n"What are you doing!\nStill no access to\nTiffa Adill!?"',
23: 'Shagia\n"Rest assured, sir.\nHer mind is already\nunder our control."',
24: 'Olba\n"The energy charge will\nbe complete shortly."',
25: 'Djibril\n"Good..! Durandal, first\nI\'ll play a requiem\njust for you!"',
26: 'Yzak\n"Damn LOGOS! Do they\nmean to hole up and\ndefend the fortress!?"',
27: 'Dearka\n"Wait, Yzak! A massive\nenergy reading from\nunder that facility!"',
28: 'Olba\n"Relay station attitude\nstabilized."',
29: 'Shagia\n"Requiem generator\nnormal. 30 seconds\nto critical."',
30: 'Shagia\n"Target: PLANT capital,\nAprilius."',
31: 'Djibril\n"Now let me play it for\nyou, Durandal - your\npeople\'s requiem!"',
33: '\u3000\n\u3000\u3000\u3000\u3000\u3000\u3000\u3000\u301cAtlandia\u301c',
34: 'Shishi\n"Atlandia.. the fair\ncity.."',
35: 'Zushi\n"The blowing wind is\nsweet, stirring the\ntreetops.."',
36: 'Shishi\n"The fairies laugh\nclear and bright.."',
37: 'Zushi\n"Blooms in profusion\nfill the city."',
38: 'Shishi\n"The bell\'s toll, melting\nhuman lives, rings on\nhistory\'s graven wall.."',
39: 'Zushi\n"And the king\'s tomb\nopens, and vivid ruin\nshall cloak this world."',
40: 'Zushi\n"You seem.. to have\ngrown used to life here."',
41: 'Shishi\n"Yes.. As if I\'ve been\nhere since the day\nI was born."',
42: 'Zushi\n"..You were born. Here..\nin the far past, and now."',
43: 'Shishi\n"As the Wing of\nthe Sun..?"',
44: 'Ryoshi\n"Vexed that Zushi was\ntaken by that one,\nOnshi?"',
45: 'Onshi\n"That is an ill wind..\nUnneeded in this\nAtlandia.."',
46: 'Yashi\n"..Leave that one to\nZushi. The door of the\ninfinite prison that\nholds us opens soon."',
47: 'Onshi\n"But won\'t the waking of\nthose in the dimensional\nwall lead the world\nitself to ruin?"',
48: 'Yashi\n"This collapse of the\nmythic balance is proof\ntheir waking is near."',
49: 'Yashi\n"Then the great power\ndescends once more.\nThe power that wrought\nParadise\'s Fall 100\nmillion years ago.."',
50: 'Ryoshi\n"The Fall that chained\nus Shadow Angels to fate\nand sealed us away.."',
51: 'Yashi\n"Since then we\'ve piled\nup countless ages,\nwatching the human world\nchange again and again.."',
52: 'Yashi\n"The curse that binds us\ngrants not even decay,\nforcing sleep and waking\nover and over.."',
53: 'Yashi\n"Again and again we fight\nthe Wingless, like fools\nacting the same play\nevery night.."',
54: 'Chishi\n"And 99.99 million years\nafter the Fall, in that\nbattle, Paradise fell\nonce again."',
55: 'Onshi\n"Back then, Lord Zushi\nsurely met the Wing of\nthe Sun once more.."',
56: 'Onshi\n"Yet the cursed power\nrose again, chained us\nin prison, and even\nstole those memories.."',
57: 'Yashi\n"But now, 12,000 years\non, change is at last\narriving - that spacequake\ncracked causality itself."',
58: 'Ryoshi\n"Break the World.. That\none but the great power\ncould cause a\nspacequake.."',
59: 'Chishi\n"Yet that very thing\nbecame our guidepost\nto Genesis."',
60: 'Yashi\n"All that remains is holy\npollination before the\nTree of Life\'s flower\nfalls, to bear Genesis\'\nfruit."',
61: 'Yashi\n"And that day is\nclose at hand.."',
62: 'Zushi\n"Shishi.. behold the\nworld of the Wingless."',
63: 'Shishi\n"Today too they slay\ntheir own kind.. turning\neven that fair moon\ninto a battlefield.."',
}

T.update({
20: 'Jamaican\n"ZAFT\'s force has\nlanded on the\nlunar surface!"',
26: 'Yzak\n"Damn LOGOS! Mean to\nhole up in the\nfortress, do they!?"',
35: 'Zushi\n"Wind blows sweet,\nstirring treetops.."',
36: 'Shishi\n"Fairies laugh\nbright.."',
37: 'Zushi\n"Blooms fill\nthe city."',
40: 'Zushi\n"You seem used to\nlife here now."',
43: 'Shishi\n"As the Sun\'s Wing..?"',
44: 'Ryoshi\n"Vexed that one took\nZushi, Onshi?"',
51: 'Yashi\n"Since then countless\nages passed, as we\nwatched mankind\'s world\nchange over and over.."',
60: 'Yashi\n"Only holy pollination\nremains ere the Tree of\nLife\'s bloom falls to\nbear Genesis fruit."',
62: 'Zushi\n"Shishi.. see the\nWingless\' world."',
63: 'Shishi\n"Today too they slay\ntheir own.. making\nthat fair moon a\nbattlefield.."',
})

rows = json.load(open(WORK + r'\analysis\rec114_work.json', encoding='utf-8'))
bud = {r['i']: r['budget'] for r in rows}
need = set(bud)
miss = need - set(T)
extra = set(T) - need
over = [(i, bl(T[i]), bud[i]) for i in T if i in bud and bl(T[i]) > bud[i]]
print("rec114: %d/%d rows | missing %s | extra %s | over %s" % (
    len(T), len(need), sorted(miss), sorted(extra), over))
if not miss and not extra and not over:
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record 114 dialogue."""', "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec114_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("  WRITTEN")
