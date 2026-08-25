# -*- coding: utf-8 -*-
"""Hand-written replacements for scenario lines whose English overran its slot.

apply_record SKIPS an over-budget row, so the Japanese ships. gen_tighten.py
recovers what mechanical rules can (contractions, '...'->'…', '..'->'.', ranks);
everything here needed a real rewrite. Keyed "rec:row", merged into
analysis/tighten_en.json and preferred over the T entry by apply_stage.

Meaning is preserved; length is bought by cutting redundancy, not content.
"""

MANUAL = {
    # --- over by 1-2 bytes ---
    "5:21": "An institute studying space\nand UFO phenomena. Its head is Dr.\n"
            "Genzo Umon, an expert in space\nscience. When the Vega Alliance\n"
            "invaded, it became the base for\nGrendizer, standing against space's\nevil.",
    "55:472": "???\n(Blame the ones near her if you\nwant someone. That woman brings\n"
              "misery to all near her.)",
    "71:252": "???\n\"And that behind my mischief, you\npush your plans too.\"",
    "100:478": "???\n\"And that behind my mischief, you\npush your plans too.\"",
    "119:911": "D.O.M.E.\n\"Seeking evolution's\nillusion\"",
    "119:932": "D.O.M.E.\n\"While you cling to that,\nthere's no future.\"",
    "136:262": "Tetsuya\n\"We and Ghingnham's lot are fools,\nbut you, who gave up on humanity,\n"
               "are worse!\"",
    "136:292": "Banjo\n\"A bitter choice, maybe,\nbut it's giving up on possibility\n"
               "and sealing our future!\"",
    "136:411": "Harry\n\"He'd destroy Earth with\nTurn X's Moonlight Butterfly!\"",
    "136:515": "Ryouma\n\"Apollo!\n Shadow Angels are yours!\"",
    "136:629": "Dianna\n\"Look who's talking,\nyou'd trigger the Black History!\"",
    "136:809": "Ageha Squad\n\"Col., good luck!\"",
    # was "A history of lamenting yet fighting\n'd never end..." - also ungrammatical
    "138:159": "Ray\n\"A history of grief and battle\nwould never end, and someday be\n"
               "called the Black History.\"",
    "138:221": "Kamille\n\"Shinn and the rest..!\"",
    "138:277": "Scirocco\n\"But the world needs no two geniuses! All units, attack! "
               "Hit ZAFT's flagship and $c!\"",
    "138:296": "Meyrin\n\"Please look after my sister and the rest, Mr. Athrun!\"",
    "138:392": "Jerid\n\"Unforgivable!\n I won't forgive you, $c!\"",
    "138:447": "Amuro\n(That's right, Kamille..\nYou still have a place to return to.\n"
               "And a future ahead.)",
    "138:467": "Neo\n\"You won't get the Archangel!\"",
    "138:518": "Shinn\n\"Save..\"",
    "138:802": "Tetsuya\n\"Shinn! Before we fight, I'll ask!\nAnything to say?!\"",
    "139:172": "Sandman\n\"What we should fear is worse.\"",
    "139:181": "Yzak\n\"Dearka reported his forces\nhave started their\natmospheric descent!\"",
    # original also had the typo "are an bigger idiot"
    "139:230": "Tetsuya\n\"We're all fools, Ghingnham and us, but you who gave up on "
               "humanity are worse!\"",
    "139:253": "Quattro\n\"Since Ageha Squad moved, Dewey Novak will likely appear on "
               "this battlefield..!\"",
    "139:282": "Kouji\n\"So you're waiting for the Coralian Antibody?!\"",
    # the original shipped LITERAL backslash-n instead of newlines
    "139:356": "Chishi\n\"But the Tree of Life is safe.\nBefore that void-dweller wakes,\n"
               "a new world'll be born.\"",
    "139:373": "Ghingnham\n\"Turn X is telling me!\nDestroy the Shadow Angels!\"",
    "139:376": "Loran\n\"That's Turn A's job!\"",

    # --- over by 3 bytes ---
    # original ended "are the result of your." - truncated mid-phrase
    "119:866": "D.O.M.E.\n\"Meeting you helped me see.\nThe Black History within me..\n"
               "is the result of your kind.\"",
    "127:997": "D.O.M.E.\n\"Meeting you helped me see.\nThe Black History within me..\n"
               "is the result of your kind.\"",
    "127:1118": "D.O.M.E.\n\"That strength of heart gave you\npower to change the future. "
                "A will\nbound by nothing creates a new era.\"",
    "136:469": "Dorothy\n\"The stage of endless battle..\"",
    "138:241": "Kamille\n\"They've stopped thinking\nfor themselves..!\"",
    "138:401": "Kamille\n\"Life is.. life is power!\n The power supporting space!\"",
    "138:407": "Kamille\n\"This kind of war can't be allowed..!\n Those who want war "
               "shouldn't\n exist!\"",
    "138:520": "Shinn\n\"Future\"",
    "138:544": "Shinn\n(Future)",
    "138:966": "Oliver\n\"But the New Federation's\nadvantage is overwhelming.\"",
    "139:216": "Shishi\n\"Fools repeating war\nwith kin over ugly ego..!\"",
    "139:286": "Zushi\n\"How ugly. The Wingless don't deserve to live!\"",
    # these three shipped LITERAL backslash-n instead of newlines
    "139:354": "Sochie\n\"Everyone, look!\nSomething's there!\"",
    "139:361": "Chishi\n\"To the Tree of Life!\"",
    "139:368": "Onshi\n\"Lord Yashi and the rest\nhave become one with the Tree..\"",
    "139:388": "Loran\n\"And those who fight, giving up self!\"",
    "139:498": "Dianna\n\"Fighting on instinct alone\nleads to ruin, the Black History..\"",
    "139:567": "Zushi\n\"But in the Wingless' land,\nhe was reborn in a new form\n"
               "and returned.\"",
    "139:647": "Zushi\n\"Too late, Wingless. I'll watch over the Tree of Life.\"",
    "139:716": "Ghingnham\n\"With this power, I can\nbring the Black History\n"
               "just as recorded!\"",
    # original was ungrammatical ("If the truth of the Black History and still want")
    "139:760": "Gainer\n\"Knowing the Black History's truth\nand still wanting destruction,\n"
               "you're beyond saving!\"",
    "139:790": "Milan\n\"What's his goal..?\"",
    "139:813": "Quattro\n\"At the same time, I'm ashamed of my\npast self. And bitter regret.\"",
    "139:867": "Kira\n\"Let's plant flowers together.\nNo matter how often they're blown away..\"",
    "139:883": "Kamille\n\"She was supposed to have died\nat Chiram. Why is she here..\"",
    "139:892": "Lunamaria\n\"Mr. Banjo, you're like\na superman.\"",

    # --- over by 4 bytes (and stragglers) ---
    "5:174": "The chief of the PLANT\nSupreme Council, the PLANTs' top\ndecision-making body. "
             "Since the\nJunius Treaty, Gilbert Durandal holds\nthe post. Patrick Zala once "
             "held it\nwith the Defense Committee Chair;\nhis hatred and madness dragged the\n"
             "war into a quagmire, so now holding\nboth posts at once is forbidden.",
    "14:115": "　A 3D fighting game piloting\nOvermen. Supports online multiplayer\ntoo. "
              "At the story's start,\nGainer wins 200 straight and earns\nthe title of King.",
    "91:252": "　A 3D fighting game piloting\nOvermen. Supports online multiplayer\ntoo. "
              "At the story's start,\nGainer wins 200 straight and earns\nthe title of King.",
    "30:315": "　S-1's military, also known\nas the Aldebaron Forces. They serve\nGattler, "
              "who betrayed the Emperor to\nseize power, and invade Earth as a\nnew home. "
              "Cmdr: Rosa Aphrodia.\nWith tech to freely enter subspace,\nthey harried "
              "Earth's forces with\nhit-and-run raids. Based at the\nsubspace fortress Algol, "
              "where many\nS-1 natives sleep in cryo-stasis,\nawaiting the day they wake.",
    "104:374": "The capital of PLANT, in the L5 sphere.\nNear war's end, crazed Djibril\n"
               "targeted it with the strategic beam\ncannon 'Requiem'. The Joule team's\n"
               "efforts diverted the firing line,\nsaving it from destruction. Still,\n"
               "surrounding plants took massive\ndamage.",
    "136:281": "Ageha Squad\n\"We left the ship without\nleave to chase the END.\"",
    "136:393": "Dianna\n\"Fighting on instinct alone\nleads to the Black History's\nruin..\"",
    "136:500": "Zushi\n\"This true light..\nYou've returned.. Wing of the Sun\"",
    "138:230": "Talia\n\"..A genetic social management system.\nIts start is finally declared..\"",
    "138:457": "Sara\n\"A world without Lord Paptimus..\n What meaning is there..\"",
    "138:569": "Kira\n\"Every life is unique!\"",
    "139:129": "Pierre\n\"More importantly..\nwhat is that?!\"",
    "139:288": "Apollo\n\"This is for Baron! I'll take down the Shadow Angels!\"",
    "139:384": "Ghingnham\n\"She came to Earth\nwithout a word of thanks!\"",
    # original read "someone's'll" - a mangled "someone's will"
    "139:409": "Kamille\n\"I sense someone's will somewhere..!?\"",
    "139:507": "Katsura\n\"Sure, all kinds gather,\nand that sparks war!\"",
    "139:537": "Zushi\n\"Do you remember, Apollonius..\n120 million years ago, another universe..\"",
    "139:562": "Zushi\n\"The Wing of the Sun is my beloved\nmythical life-form,\nAquarion!\"",
    "139:570": "Zushi\n\"12,000 years ago..\nIt was such a beautiful light..\"",
    "139:573": "Dorothy\n\"The stage of endless war..\"",
    "139:599": "Shishi\n\"..I'll defeat Zushi!\nApollo, Silvia, lend me power!\"",
    "139:619": "Ryouma\n\"Apollo! Shadow Angels are yours!\"",
    "139:642": "Zushi\n\"I leave it to you, Onshi. I'll await the Tree's birth.\"",
    "139:651": "Tsine\n\"The Sphere's shown you, right?\nSpacetime's collapse is near.\"",
    "139:683": "Eiji\n\"Prepare yourself, villain!\nGravion is the fang for the fangless!\"",
    "139:690": "Shishi\n\"Know that a stray dog like you\nspeaking to me, a Shadow Angel,\n"
               "is pure insolence.\"",
    "139:893": "Banjo\n\"Whether that's happiness, who knows.\"",
    "139:1036": "Ageha Squad\n\"Col., good luck..!\"",
    "139:1069": "Jurgens\n\"..So this is the Ageha Plan's goal..\"",
    # original had "destroyed'd not produce"
    "139:1072": "Dominic\n\"Scabs whose cores were destroyed were predicted not to make "
                "antibodies but wake from dormancy.\"",

    # --- over by 5-6 bytes ---
    "119:843": "D.O.M.E.\n\"And so, the one recording Black\nHistory and watching humanity..\"",
    "119:929": "D.O.M.E.\n\"But I don't think those who use\npower for war can create\n"
               "the future either.\"",
    "127:973": "D.O.M.E.\n\"And those recording Black\nHistory, watching humanity..\"",
    "136:296": "Apollo\n\"This is for Baron!\nI'll take down the Shadow Angels!!\"",
    "136:407": "Ghingnham\n\"That's humanity's true form!\nThe heart that wants war.. the truth!\"",
    "136:466": "Zushi\n\"120 million years ago..\nIt was such a beautiful light..\"",
    "136:495": "Shishi\n\"..I'll defeat Zushi!\nApollo, Silvia, lend me power!\"",
    "136:522": "Sirius\n\"Shut up, Zushi!\n Angel or human, no matter!\n We'll strike you down!\"",
    "136:532": "Zushi\n\"Those in the rift\n and the Wingless shall perish\"",
    "136:536": "Onshi\n\"Gah..!\nThen I'll protect\nthe Tree of Life\nwith Lord Zushi..!\"",
    "138:297": "Lacus\n\"I'm counting on you..\"",
    "138:340": "Emma\n\"Can't you accept your own path\nunless someone gives you something!?\"",
    "138:490": "Athrun\n(I'm counting on you..)",
    "138:549": "Stella\n(See you tomorrow!)",
    "139:268": "Ageha Squad\n\"That our ancestors left Earth, our mother star, for the "
               "promised land was a distorted truth.\"",
    # shipped literal backslash-n
    "139:360": "Yashi\n\"Oh.. drawn through its roots,\nwe shall become new seeds.\"",
    "139:371": "Onshi\n\"Butterfly-winged demon\"",
    "139:380": "Ghingnham\n\"This Turn X is amazing!\nTruly Turn A's big bro!!\"",
    "139:392": "Ghingnham\n\"The Butterfly!!\"",
    "139:410": "Amuro\n\"What is this..!? Countless minds are becoming one!\"",
    "139:461": "Shagia\n\"Until this world is destroyed and\nall humans taste our\n"
               "same despair!!\"",
    "139:517": "Dianna\n\"Don't let your guard down.\nWhile that man has the Moonlight Butterfly..\"",
    "139:555": "Zushi\n\"My judgment is sound.\nCelian's soul split into light and dark,\n"
               "the bright memories to the sister..\"",
    "139:625": "Zushi\n\"Onshi and the Wingless say the same. Come.. Wing of the Sun, "
               "let us rejoice, reunited..\"",
    "139:632": "Zushi\n\"Those in the rift and the Wingless shall perish.\"",
    "139:637": "Apollo\n\"Damn! Not getting away, Shadow Angel!\"",
    "139:644": "Onshi\n\"Those in the rift and the Wingless shall perish.\"",
    "139:680": "Marin\n\"You who don't grasp Earth's beauty\nor the weight of its lives!\"",
    "139:869": "Kamille\n\"Shinn.. let's go.\"",
    "139:1018": "Eureka\n\"Maurice.. I always watched you.\nMom was watching.\"",
    "139:1041": "Dewey\n\"Those kids, rejected by old values, were to be the cornerstone "
                "of a new world order.\"",

    # --- over by 7-9 bytes ---
    # original ended "there were those\ncalled." - truncated mid-phrase
    "127:998": "D.O.M.E.\n\"At the Black History war's\nstart.. there were those\ncalled..\"",
    "136:291": "Duke\n\"A man who ignores his people\nis no king!\"",
    "136:622": "Ghingnham\n\"With this power,\nI can trigger the Black History\nas recorded!\"",
    "136:637": "Garrod\n\"Everyone lives as best they can!\nEnduring sadness and hardship!\"",
    "138:149": "Haman\n\"The Fed and $c..\n One strikes, the other follows,\n and it's a brawl.\"",
    "138:273": "Ray\n\"Shinn, Lunamaria.\nTake out enemies nearing the Chairman.\"",
    "138:416": "Kamille\n\"Paptimus Scirocco! It's men like you\nwho can't feel others' pain\n"
               "who must be removed!\"",
    "138:479": "Arthur\n\"And you, Captain?\"",
    "138:488": "Kouji\n\"Maybe he's passionate.\"",
    "138:635": "Toga\n\"It could still fight,\nso why retreat?\"",
    "139:139": "Shishi\n\"Not Shadow Angels.\nBeautiful Atlandia\nis home to the Heaven Angels..!\"",
    "139:161": "Loran\n\"Angels' new world..\"",
    "139:162": "Katsura\n\"Shadow Angels are fixing spacetime?!\"",
    "139:165": "Sandman\n\"First, defeat the Shadow Angels.\"",
    "139:239": "Shishi\n\"I'll strike down all! For the Shadow Angels' new world!\"",
    # shipped literal backslash-n
    "139:357": "Yashi\n\"..The Wing of the Sun has woken..\nPollen with a resonance we lack\n"
               "will seed the Tree.\"",
    "139:407": "Reika\n\"So that's why Fudo..\"",
    "139:512": "Ghingnham\n\"That's humanity's true form!\nThe heart that craves war.. the truth!\"",
    "139:630": "Zushi\n\"Onshi, fall back. Await the Tree of Life's birth there.\"",
    "139:707": "Kamille\n\"Those who don't understand should vanish!\n"
               "You're the ones who shouldn't exist!!\"",
    "139:1039": "Dewey\n\"They lost their homeland to war,\ntheir existence denied at birth..\n"
                "Bastards of humanity's dark side.\"",
    "139:1045": "Dewey\n\"Bare ego, habit's convention, power structures unchanged from the "
                "old world..! Even in the multiworld!\"",
    "139:1074": "Dominic\n\"In fact, with the Shadow Angels' Tree of Life collapse, "
                "it nearly came to that.\"",

    # --- over by 10+ bytes: these needed real condensing ---
    "119:860": "D.O.M.E.\n\"Over 12,000 years ago, time and\nspace were destroyed, a new\n"
               "world born.\"",
    "136:415": "Loran\n(Turn X's Moonlight Butterfly..!\nTurn A must stop it..!)",
    "136:452": "Zushi\n\"Dark memories that ruined\nthe world, to the brother..\"",
    "136:467": "Zushi\n\"Since then, we've been trapped\nin an endless prison, in cosmic\n"
               "death and rebirth!\"",
    "136:470": "Dorothy\n\"The fallen Angels dance there,\nrobbed of memory each fall,\n"
               "and sink into sleep\"",
    "136:533": "Zushi\n\"The Tree's birth brings\n new Shadow Angels.. a new world\"",
    "136:560": "Apollo\n\"Over!\"",
    "136:606": "Zushi\n\"No rush.\nThe Sun's light will\nseed the Tree of Life..\"",
    "136:613": "Kamille\n\"Those who don't understand should vanish!\n"
               "You're the ones who shouldn't exist!!\"",
    "136:614": "Quattro\n\"This sight.. Does it mean\nsomething in humans\ndesires destruction..\"",
    "136:618": "Loran\n\"If they truly mean to destroy Earth..\"",
    "136:631": "Shinn\n\"These guys differ from the Chairman..!\nThey don't care about the world!\"",
    "136:633": "Kira\n\"Despair and anger..\nEven if some wish for\ndestruction at the end..\"",
    "138:425": "Kamille\n\"You can't understand! Not you,\nScirocco, who uses war as a tool!\n"
               "This power in me!\"",
    "138:628": "Kouji\n\"This was to be a big battle\nwith the alliance,\nbut they seem bored?\"",
    "139:177": "Shishi\n\"The Wingless have no right to live..!\nThe new world is the Angels'!\"",
    "139:235": "Shinn\n\"For a peace sacrificing no one, I'll fight my hardest!\"",
    "139:239": "Shishi\n\"I'll strike down all! For the Angels' new world!\"",
    "139:297": "Duke\n\"A man who ignores his people is no king!\"",
    "139:324": "Anemone\n(I'd tie my hair in the breeze,\ntake a big step forward,\n"
               "and go see him, head high..)",
    "139:398": "Zushi\n\"Impossible..!\nThe Sun's Wing regained true light!\"",

    # --- final pass: parallel lines shared between rec136 and rec139 reuse the
    #     condensed rec136 wording, so the two records stay consistent ---
    "139:405": "Zushi\n\"When the tree withers, its power bursts, dimensional walls "
               "break, and void-dwellers appear in chaos.\"",
    "139:413": "Katsura\n\"Spacetime collapse!?\"",
    "139:518": "Loran\n(Turn X's Moonlight Butterfly..!\nTurn A must stop it..!)",
    "139:556": "Zushi\n\"Dark memories that ruined\nthe world, to the brother..\"",
    "139:571": "Zushi\n\"Since then, we've been trapped\nin an endless prison, in cosmic\n"
               "death and rebirth!\"",
    "139:574": "Dorothy\n\"The fallen Angels dancing there\nlose memory each stage's end,\n"
               "and fall asleep.\"",
    "139:626": "Sirius\n\"Shut up, Zushi! Angel or human, no matter! We'll strike you down!\"",
    "139:633": "Zushi\n\"The Tree's birth brings a new Angel.. a new world.\"",
    "139:645": "Onshi\n\"The Tree's birth brings a new Angel.. a new world.\"",
    "139:676": "Banjo\n\"If you're the clouds over Earth's future,\nwe're the sun to clear you!\"",
    "139:682": "Touga\n\"The Gran Knights won't forgive\nthe evil that shrouds the world!\"",
    "139:695": "Onshi\n\"Sun's Wing!\nI'll take you down myself!\"",
    "139:700": "Zushi\n\"No rush.\nThe Sun's light will\nseed the Tree of Life..\"",
    "139:708": "Quattro\n\"This sight.. Does it mean\nsomething in humans\ndesires destruction..\"",
    "139:712": "Loran\n\"If they truly mean to destroy Earth..\"",
    "139:725": "Shinn\n\"These guys differ from the Chairman..!\nThey don't care about the world!\"",
    "139:727": "Kira\n\"Despair and anger..\nEven if some wish for ruin\nat the end..\"",
    "139:734": "Jamil\n\"Anyone who crushes hope's buds,\nI'll stop them if\n"
               "it costs my life!\"",
    "139:785": "Milan\n\"Messiah fell to Antarctica\nfrom the New Fed's\ngiant weapon.\"",
    "139:788": "Milan\n\"Footage from 30 minutes ago.\nThe giant weapon self-destructed,\n"
               "unable to bear its own power.\"",
    "139:862": "Amuro\n\"People can understand..\"",
    "139:961": "Talho\n\"In classified military files..\"",
    "139:992": "Renton\n\"I promised. I'd always be\nby your side.. protect you.\"",
    "139:401": "Sirius\n\"Zushi! You at least\nI'll take down myself!\"",
}
