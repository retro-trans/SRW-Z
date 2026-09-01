# -*- coding: utf-8 -*-
"""English prologue narration for DATA/MTV_PROS.BIN rawt chunks.

Ordered exactly as the rawt chunks appear when walking records 0-13. Each
entry is (bytes_hashed, sha1-16 of that many bytes of the ORIGINAL japanese
chunk, English text).

WHY A HASH AND NOT THE JAPANESE. The first field only ever guarded chunk
order - patch_mtvpros.py asserted that the chunk it is about to overwrite
starts with the expected japanese, so a mis-ordered walk cannot splice
narration into the wrong slot. It never needed to be readable: hashing the
same leading bytes proves the same thing. It used to hold whole sentences of
Banpresto's prologue, which is their text, and check_publishable.py refused
the repo over it (21 prose runs, the worst offender in the tree). The guard is
unchanged in strength - it still fails loudly on a mis-ordered walk.

The patcher menu-encodes the English (digits/./:;= become fullwidth - they are
control bytes in the reader) and pads with spaces to the original chunk size.
"""

TEXTS = [
    (26, '7385a709004c09b8',
     '\u3000The era called the Universal Century.\n'
     '\u3000Nations were abolished, and humanity, united\n'
     'under the Earth Federation government, built\n'
     'space colonies and spread its life into space.\n'
     '\u3000\n'
     '\u3000But that soil bred new wars. The Principality\n'
     'of Zeon, born in the colony cluster Side 3,\n'
     'declared independence from the Federation, and\n'
     'the conflict grew into the One Year War.\n'
     '\u3000Its scale was unprecedented; its scars on\n'
     'society ran deep.\n'
     '\u3000\n'
     '\u3000Even after the war - which cost mankind a\n'
     'third of its people - ended in Federation\n'
     'victory, the fires never died.\n'
     '\u3000After the attacks of Dr. Hell, who sought\n'
     'to rule with the power of a lost\n'
     'civilization, humanity faced one inhuman foe\n'
     'after another:\n'
     '\u3000the ancient Mycenae Empire, the Dinosaur\n'
     'Empire of reptile-men beneath the earth, and\n'
     'the invading Vega Alliance from space.\n'
     '\u3000Fighting around Mazinger Z, Getter Robo\n'
     'and the Super Robots, humanity crushed Dr.\n'
     'Hell and Mycenae; the wars with the\n'
     'Dinosaurs and Vega neared their end.\n'
     '\u3000\n'
     '\u3000Yet even in those wars, humanity could not\n'
     'become one.\n'
     '\u3000The rift between Earthnoids and Spacenoids,\n'
     'exposed by the One Year War, entered a new\n'
     'phase now, seven years after its end.\n'
     "\u3000The elite corps 'Titans', seizing the Earth\n"
     'Federation Forces from within, bared its ego\n'
     'and oppressed the Spacenoids - and those who\n'
     'saw the danger formed the anti-Federation\n'
     "group 'AEUG' and began to resist.\n"
     '\u3000\n'
     '\u3000As one war ended and another began, a vast\n'
     'storm of destiny was quietly swallowing the\n'
     'world.',
     ),
    (42, '0c7a31ec4619f551',
     '\u3000An age in which the old civilization and\n'
     'nature itself were lost to the Earth, and\n'
     'each region formed its own society and culture.\n'
     '\u3000Through history mankind lost many things -\n'
     'and built new ones in their place.\n'
     '\u3000\n'
     '\u3000The rule of the Innocent, the privileged\n'
     'class of the great northern continent, was\n'
     'ended by the Civilians, the new humanity\n'
     'they had made.\n'
     '\u3000The Central Government of the other lands,\n'
     'broken by the 7th Space War 15 years\n'
     'ago, was regaining control.\n'
     '\u3000So too was its old enemy, the Space\n'
     'Revolutionary Army.\n'
     '\u3000And the Moonrace, who stayed apart from\n'
     'them all, were about to act on their dearest\n'
     'wish.\n'
     '\u3000\n'
     '\u3000While the world approached great upheaval,\n'
     'people lived for their daily bread - knowing\n'
     'neither what future awaited them, nor what\n'
     'had happened in their past.',
     ),
    (40, '563db4c0708dfa4e',
     '\u3000A great spacetime quake broke the walls of\n'
     'dimension, and a new world was born - many\n'
     'worlds and times mixed into one.',
     ),
    (34, 'f737119cd9370032',
     '\u3000But mankind had not perished.',
     ),
    (42, '64e610f16a76c3d7',
     '\u3000In the multiverse born of the spacetime\n'
     "collapse 'Break the World', mankind set out\n"
     'to build a new order.',
     ),
    (42, '3a74b41d9cc14817',
     '\u3000The Earth Federation, Earth Alliance,\n'
     'Central Government and Federal Towers founded\n'
     'a single union of their peoples: the New\n'
     'Earth Federation, meant one day to govern all\n'
     'humanity under its name.\n'
     "\u3000Styling itself the world's police, the New\n"
     'Federation intervened in conflicts everywhere\n'
     'and annexed small nations one by one.\n'
     '\u3000This provoked Chiram, native power of the\n'
     'multiverse - yet the two named each other\n'
     'friends, neighbors in this new world.\n'
     '\u3000Together, the New Federation and Chiram\n'
     'came to hold 70% of the Earth and 75% of\n'
     'its people.',
     ),
    (38, '908f2bb1d32038c3',
     '\u3000Other regions formed societies of their\n'
     'own, apart from the New Federation.\n'
     '\u3000The greatest was Emaan, who joined the\n'
     'multiverse at the same time as Chiram.\n'
     'Centered on southeast Galia, Emaan was a\n'
     'crossroads of trade in goods and information,\n'
     'sending caravans to every corner of the\n'
     'world.',
     ),
    (40, '45739dc6eef35f98',
     "\u3000Through Emaan's efforts and the worldwide\n"
     'unified-information system known as the UN,\n'
     'mankind slowly came to understand the\n'
     'multiverse, to accept it, to adapt - and to\n'
     'build the foundations of life.\n'
     '\u3000\n'
     '\u3000Yet the world remained unknown and\n'
     'unstable.\n'
     '\u3000\n'
     '\u3000High above the sky lay a dimensional wall,\n'
     'the Cross-Realm; passage to space was\n'
     'limited to where it ran thin - southern\n'
     'Galia and parts of the Pacific.\n'
     '\u3000Small spacetime quakes still occurred, and\n'
     'those caught in them never returned.\n'
     '\u3000\n'
     '\u3000Unable to wipe away their unease, people\n'
     'ran to the pleasures of the moment; the\n'
     'multiverse was unstable in all things.\n'
     '\u3000\n'
     '\u3000Some chased the Trapar waves that covered\n'
     'the world; some joined Emaan caravans seeking\n'
     'fortune; and some sharpened their fangs to\n'
     'seize mastery of a world in chaos.',
     ),
    (14, '607855d690efcb3e',
     '\u3000Multidimensional Century year one.\n'
     '\u3000Half a year since Break the World -\n'
     'something unseen was starting to move\n'
     'around this new world.',
     ),
    (40, '516e74cdaa5ff636',
     '\u3000The new world bred new wars - wars made\n'
     'all the more tangled and chaotic by the\n'
     'multiverse itself.\n'
     '\u3000\n'
     '\u3000The New Earth Federation branded spacebound\n'
     'humanity its enemy, taking a warlike stance\n'
     'against the PLANTs and the Moonrace.\n'
     '\u3000They had hoped for dialogue, but against\n'
     "the Federation's attacks they had no choice\n"
     'but to fight.\n'
     '\u3000\n'
     "\u3000Nor was mankind's only enemy itself: it\n"
     'had to defend against Gaizock, Zeravire, the\n'
     'Eldar, Aldebaron, and the Shadow Angels.\n'
     "\u3000And further foes moved in the world's\n"
     'shadows.\n'
     '\u3000\n'
     "\u3000Amid it all, some looked to the world's\n"
     'future and readied their next move: the New\n'
     'Federation, ZAFT, the Moonrace, Chiram,\n'
     'Emaan, and...\n'
     '\u3000\n'
     '\u3000In a world of chaos, people lived with all\n'
     'their strength. Survive today, or there is\n'
     'no tomorrow.\n'
     '\u3000Not knowing where the world was headed,\n'
     "people fought on, each to carry today's life\n"
     'into tomorrow.',
     ),
    (40, '46e3021a04dfb585',
     '\u3000Amid the fighting, a new spacetime warhead\n'
     'broke the dimensional walls once more.\n'
     "\u3000The 'Second Break' changed not just the\n"
     'fragile order, but continents and the very\n'
     'stars.',
     ),
    (42, 'e2308c776732cd5a',
     '\u3000People could only feel anew that they\n'
     'lived in a fleeting world, nothing assured.',
     ),
    (38, '8350fb5c17a82313',
     "\u3000People's fear erupted into riots,",
     ),
    (38, 'b5dbce1cdbb53018',
     'and the news raced across the UN amid',
     ),
    (42, '11f5b4692c20b6c6',
     'reckless rumors, stirring deeper unease.',
     ),
    (42, '946c05dce0cb7fca',
     'The New Federation, reshaped by the coup,',
     ),
    (40, 'aef9ddf33f224956',
     'sent troops to crush the riots - yet the',
     ),
    (40, 'd141dd0d26f92c42',
     'fear rooted deep in their hearts could',
     ),
    (20, 'd3fbfe2f1ec30620',
     'not be removed.',
     ),
    (42, '4d9c47c527b96c60',
     '\u3000And the Second Break had changed the',
     ),
    (40, 'c504f3ae1edef26b',
     'Cross-Realm dividing Earth and space.',
     ),
    (38, 'e571fab702ba967c',
     '\u3000Its power weakened the world over,',
     ),
    (32, '995b446c8a4a639e',
     'and Trapar grew in its place.',
     ),
    (40, 'dc66a851b2f04113',
     'With this, alien attacks and the war of',
     ),
    (40, '782020c0a3c6decc',
     'Earth and space dwellers raged on, and',
     ),
    (40, 'e31c069eeee6ca81',
     'Coralian antibodies stirred everywhere.',
     ),
    (42, 'ddc931ad58b8a79e',
     "\u3000People feared the world's end, yet with\n"
     'no recourse could only dread the shadowy\n'
     'rumors racing across the UN.',
     ),
    (40, '6486722a47fa44d2',
     '\u3000As the world itself wavered, a final\n'
     'battle was beginning - waged by those who\n'
     'sought its future and its crown...',
     ),
]
