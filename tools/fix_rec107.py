# -*- coding: utf-8 -*-
"""Hand-trim the residual over-budget rows in DeepSeek's rec107_en.py."""
import importlib.util as u
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


s = u.spec_from_file_location('m', 'rec107_en.py')
m = u.module_from_spec(s)
s.loader.exec_module(m)
wk = {r['i']: r for r in json.load(open(WORK + r'\analysis\rec107_work.json', encoding='utf-8'))}

F = {
140: 'Oliver\n"The Artificial Sun!"',
150: 'Gengoro\n"They\'re all-in on this!\nWatch for reinforcements!"',
157: 'Rina\n"Innocent eyes..\nDangerous, those.."',
184: 'Negros\n"But you escaped it,\nthanks to the Fuhrer\'s favor!"',
185: 'Negros\n"My brother Gallo died by\nthat rule, for turning from\nthe foe! That\'s why I\'ll\nnever forgive you!"',
201: 'Rubina\n"Strike now, while their\ncommand\'s in disarray!"',
206: 'Hanae\n"Grandpa! Something\ncomes from above!!"',
207: 'Heizaemon\n"Reinforcements?!"',
228: 'Garrod\n"New respect for you!\nYou\'re not just the Gran\nKnights\' battle-cry guy!"',
254: 'Sandman\n"Spread those noble wings,\nsoar into tomorrow\'s sky!"',
257: 'Roger\n"No.. his devotion to his\naesthetic deserves praise."',
269: 'Touga\n"Let\'s go, all! We\'re $c..!\nEarth\'s protectors!!"',
274: 'Jun\n"High-dim quantum reaction!\nThat\'s a Shadow Angel!"',
284: 'Apollo\n"Kid or geezer, who cares!\nIf it\'s a Shadow Angel,\nwe take it down!"',
295: 'Quattro\n"The Shadow Angels hit both\nus and the aliens..!"',
296: 'Jamil\n"They stir up the fight..!\nEither way, a nuisance!"',
297: 'Apollo\n"Shadow Angel! Brat or not,\nI won\'t go easy! Prepare\nyourself!"',
304: 'Touga\n"Here it comes, Zeravire!"',
309: 'Marin\n"A subspace field..!\nThe Artificial Sun\'s excess\nenergy warps the space\naround it!"',
316: 'Heizaemon\n"Millions of lives at stake!\nIf one King Beal is the price,\nthat\'s a bargain!"',
329: 'Runa\n"Insane or not, we do it!"',
330: 'Mizuki\n"We\'ll buy all the time we can!\nReady the Artificial Sun!"',
332: 'Touga\n"We\'ll burn our lives full!\nTo protect this Earth!"',
336: 'Banjo\n"The true sun won\'t fall\nto earth..!"',
339: 'Runa\n"Something comes above!"',
376: 'Sandman\n"The system links to the\npilot\'s brain.."',
385: 'Touga\n"Leele.. lend us strength."',
619: 'Marinia\n"Unless Lord Sandman\nallows it.."',
633: 'Sandman\n"I see.. Let\'s meet Touga\nand the rest before dark\nengulfs Earth."',
636: 'Sandman\n"Perhaps now\'s the time..\nThe sun\'s light to dispel\nthis dark cloud.."',
653: 'Rubina\n"I\'ll speak to my father,\nEmperor Vega, and halt\nthe operation somehow."',
656: 'Aphrodia\n"Talk of humanity or justice\nto them is pointless."',
697: 'Breaker\n"Looks like you want hurt,\npal! Then I\'ll give you\nwhat you want.."',
699: 'Faye\n"Broad daylight, in town,\nreeking of booze, raising\na ruckus.. A public\nnuisance."',
741: 'Eiji\n"Don\'t mess with me,\nTouga!"',
874: 'Yashi\n"Leave her, she\'s a child."',
877: 'Ryoshi\n"As ever, Lady Yashi\'s\nsoft on Futaba.."',
881: 'Yashi\n"Before paradise falls again,\nwe\'ll use the Life Tree\'s\npower to free our world\nfrom that curse."',
950: 'Toshiya\n"Need something?"',
}

for i, t in F.items():
    m.T[i] = t

lines = ["# -*- coding: utf-8 -*-", '"""Stage record 107 dialogue (DeepSeek)."""', "", "T = {"]
for k in sorted(m.T):
    lines.append("    %d: %r," % (k, m.T[k]))
lines.append("}")
open("rec107_en.py", "w", encoding="utf-8").write("\n".join(lines) + "\n")
over = [(i, bl(m.T[i]), wk[i]['budget']) for i in m.T if i in wk and bl(m.T[i]) > wk[i]['budget']]
print("rec107 over now (%d): %s" % (len(over), over))
