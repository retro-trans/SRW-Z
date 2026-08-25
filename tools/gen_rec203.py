# -*- coding: utf-8 -*-
"""Record 203 - the meta 4th-wall scenario-demo command tutorial."""
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


T = {
11: 'Amuro\n"All units, launch!\nThis time we\'re the\nbad guys!"',
12: '???\n"Damn! The noise is bad!\nThe screen\'s pure static!"',
13: 'Bright\n"What are you doing!\nLaunch, now! It\'s plain\neven through the monitor!"',
14: '???\n"Ah.. sorry. Our monitor\nover here just\ncompletely died.."',
15: '???\n"Oh wait, it recovered\na bit. Can you see the\nbottom half or so?"',
17: 'Amuro\n"Right.. So it\'s a\ntwo-choice question."',
18: '"Amuro\'s Choice"\n"Everyone, do your best"\n"Value your life"',
19: 'Amuro\n"Since you picked \'do\nyour best,\' let\'s\ndo our best!"',
21: 'Amuro\n"Since you picked \'value\nyour life,\' don\'t\ngo dying!"',
22: 'Bright\n"For now, let me state\nthe allied units\'\nmissions."',
23: 'Bright\n"The Strike Gundam does\nin-map swapping, or\nrather, transformation.."',
24: 'Bright\n"Ideon: check the Ideon\nSystem. Jeeg can return\nonce from a solo split -\nthe Jeeg solo split.."',
25: 'Bright\n"EVA Unit-01: shootdown\nberserk. Plus the various\nsong systems."',
38: '"Standard-bearer of the third generation of anime" (from Animage)\n'
    'His unique motion and timing, his deformed characters, the shapes of his '
    'explosions and beams, his way of showing off robots - all gave great '
    'influence to many later animators.\n'
    'And even now he goes on influencing them, a charismatic figure of the anime world.',
39: 'Amuro\n"First, the basic-form\nlines. I enter from\nthe right."',
40: 'Amuro\n"The screen\'s sepia\nbecause that\'s the\nsetting."',
41: 'Kamille\n"Then I\'ll come from\nthe left! Angry face!"',
42: 'Kamille\n"Anyway, that\'s enough\nof the sepia filter\nfor now."',
43: 'Bright\n"Judau! What are you\ndoing! We can see it\nplain from the monitor!"',
44: 'Bright\n"Whoa! Too bright!\nAnd with that, comms\nend!"',
45: 'Kamille\n"Good grief.. I\'ll\nhead home too."',
46: 'Amuro\n"Well, same as always.\nI\'ll take my leave too."',
49: 'Kamille\n"So, Amuro, what do\nwe do after this?"',
50: 'Amuro\n"Hmm.. A two-choice\noption, huh."',
51: '"Amuro\'s Choice"\n"Go right"\n"Go left"',
55: 'Amuro\n"By the way, Kamille..\ndo you know of\n<Orphan>?"',
56: 'Kamille\n"Then can you explain\nthe <Balmar War>,\nAmuro?"',
57: 'Amuro\n"Of course I know both\n<Orphan> and the\n<Balmar War>."',
58: 'Amuro\n"And of course I know\n<Orphan>, the <Balmar\nWar>, and <Yoshinori\nKanada> too."',
59: 'Kamille\n"Amazing! <Orphan>, the\n<Balmar War> and\n<Yoshinori Kanada>!\n<Orphan>, the <Balmar\nWar> and <Yoshinori\nKanada>!"',
60: 'Kamille\n"Amazing! ..And so, that\nshould cover all the\nscenario-demo commands."',
61: 'Amuro\n"Before that, let\'s check\nthe new command,\nleft-right active."',
64: 'Amuro\n"Yeah. You use left-right\nactive when everyone\'s\nreacting in surprise\nlike that."',
65: 'Kamille\n"It\'s kind of like MMR\'s\n\'Whaaat!?\', isn\'t it."',
66: 'Amuro\n"Now let\'s head to the\nmap and check that\ncommand there."',
68: 'Bright\n"Well, that\'s about it\nfor this time."',
70: 'Bright\n"Now, don\'t say that.\nThis should cover every\ncommand but the\nmain-character ones.."',
71: 'Amuro\n"Hold on! L-light is\nspreading out..!"',
}

T.update({
11: 'Amuro\n"All units, launch!\nWe\'re the villains!"',
38: '"Standard-bearer of anime\'s third generation" (from Animage)\n'
    'His unique motion and timing, deformed characters, his explosions and '
    'beams, his way of showing robots - all greatly influenced many later '
    'animators.\n'
    'Even now he keeps influencing them, a charismatic figure of the anime world.',
41: 'Kamille\n"Then I enter left!\nAngry face!"',
61: 'Amuro\n"First, let\'s check the\nnew command, left-\nright active."',
})

# Aggressive trims so the record compresses into its 6000-byte slot
# (English compresses worse than JP; shorter rows -> more null padding -> smaller blob).
T.update({
13: 'Bright\n"What are you doing!\nLaunch! We see it plain\neven on the monitor!"',
15: '???\n"Oh, it recovered a bit.\nSee the bottom half?"',
22: 'Bright\n"For now, the allied\nunits\' missions."',
23: 'Bright\n"Strike Gundam does\nin-map swap - well,\ntransform.."',
24: 'Bright\n"Ideon: check the Ideon\nSystem. Jeeg can return\nonce from a solo split."',
25: 'Bright\n"EVA-01: shootdown\nberserk. Plus the\nsong systems."',
38: '"Anime\'s third-generation standard-bearer" (Animage). His motion, '
    'timing, deformed characters, explosions and robot staging shaped '
    'countless later animators - and still do today.',
57: 'Amuro\n"Of course I know\nboth of those."',
58: 'Amuro\n"And of course all\nthree of them, too."',
59: 'Kamille\n"Amazing! <Orphan>, the\n<Balmar War>, and\n<Yoshinori Kanada>!"',
60: 'Kamille\n"Amazing! ..And that\nshould cover the demo\ncommands."',
64: 'Amuro\n"Yeah. Use it when all\nreact in surprise\nlike that."',
70: 'Bright\n"Don\'t say that. This\ncovers every command\nbut the hero ones.."',
71: 'Amuro\n"Hold on! L-light is\nspreading..!"',
})

rows = json.load(open(WORK + r'\analysis\rec203_work.json', encoding='utf-8'))
bud = {r['i']: r['budget'] for r in rows}
need = set(bud)
miss = need - set(T)
extra = set(T) - need
over = [(i, bl(T[i]), bud[i]) for i in T if i in bud and bl(T[i]) > bud[i]]
print("rec203: %d/%d rows | missing %s | extra %s | over %s" % (
    len(T), len(need), sorted(miss), sorted(extra), over))
if not miss and not extra and not over:
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record 203 dialogue."""', "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec203_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("  WRITTEN")
