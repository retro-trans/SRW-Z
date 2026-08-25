# -*- coding: utf-8 -*-
"""Translated encyclopedia (図鑑) descriptions.

Text is stored as PARAGRAPHS with no hard line breaks - one "\n" separates
paragraphs. zkn_desc_apply.py wraps each paragraph to the box width (about 25
fullwidth = 50 half-width columns, measured from the Japanese, which never
exceeds 27) and re-joins with newlines. Storing pre-wrapped text would bake in
a width we may want to change.

The box SCROLLS - the longest Japanese description runs to 63 lines - so English
is not limited to the Japanese line count, only to sensible wording.

Names follow the project glossary so the encyclopedia matches the dialogue.
"""

# DATA_MTVZKNKW.BIN - glossary terms, keyed by record index.
KW_DSCR = {
    0: "An institute that researches every matter relating to space and UFOs. "
       "Its director is Dr. Genzo Umon, an authority on space science.\n"
       "When the Vegan invasion of Earth began, it became the base for "
       "Grendizer and the Spazer, and stood against the great evil from space.",

    1: "An underground nation ruled by the Reptilian Humanoids, reptiles that "
       "evolved into a humanoid race. Led by Emperor Gore, who worships the "
       "great demon god Yura, they launched an invasion to seize the surface "
       "world.\n"
       "The Reptilian Humanoids once ruled the surface, but they could not "
       "withstand the Getter Rays that suddenly rained down from space, and "
       "were driven into the magma layers deep underground. For that reason "
       "they were obsessed with destroying Getter Robo, which draws its power "
       "from Getter Rays.\n"
       "In their final operation they sent out the Invincible Battleship Dai, "
       "mightiest of all the Mechasaurus. But Musashi Tomoe rammed it in a "
       "Command Machine loaded with explosives, and Dai went out of control. "
       "Gore was caught in the destruction and died, and the Dinosaur Empire "
       "was annihilated.",

    2: "The military of Planet S-1, also called the Aldebaron Army.\n"
       "Following Gattler, who rebelled against the emperor and seized control "
       "of the nation, they set out to invade Earth as their new homeland. "
       "Their supreme commander is Rosa Aphrodia.\n"
       "They possess technology that lets them pass in and out of subspace at "
       "will, and confounded Earth's forces with operations that struck from "
       "nowhere.\n"
       "Their headquarters is the subspace fortress Algol, where great numbers "
       "of S-1 natives sleep in cryogenic capsules, awaiting the time of their "
       "awakening.",

    3: "A layer of distortion lying above the world that formed when parallel "
       "worlds overlapped. Space-time within the layer is unstable and cannot "
       "be crossed, so passage between space and the surface is impossible.\n"
       "Because this layer exists, a greenhouse effect has driven surface "
       "temperatures up, causing serious damage.\n"
       "The term also refers to the merged world itself, born from the effects "
       "of the space-time oscillation bomb.",

    4: "A people of advanced science and technology who live in domed cities "
       "called Points. They supply the Civilians with Walker Machines and buy "
       "up the Blue Stone they mine.\n"
       "Their ancestors were the humans who fled into space to escape the "
       "great upheaval that struck Earth. When they returned long afterward, "
       "what they found was the ravaged land of Zora - a world turned so "
       "hostile that a few hours in the open air meant death for them.\n"
       "So they created a new race suited to Zora's environment, the "
       "Civilians, as the heirs who would carry on their civilization. They "
       "also succeeded in building an economy on trade in Blue Stone, "
       "worthless to the Innocent themselves, and in instilling order through "
       "the Three Day Law.\n"
       "As the Civilians rose, Kashim King feared the Innocent would lose "
       "their dominion over Zora, and cracked down on the resistance again and "
       "again to hold them in check. But Jiron and his companions threw off "
       "even that oppression, and at last the rule of the Innocent was "
       "overturned.",

    5: "The supreme head of the Innocent. His full name is Arthur Rank, a name "
       "handed down through generations of Innocent leaders.\n"
       "He was confined at Point Yop by his aide Kashim King. Rescued by Jiron "
       "and the others, he saw promise in them and entrusted Zora's future to "
       "them.\n"
       "Later, to save Elche after Kashim's mind was transplanted into her, he "
       "had Kashim's consciousness transferred into himself instead. It turned "
       "his character violent, but he wrung out the last of his strength and "
       "leapt from the Iron Gear together with a bomb.",

    6: "The most powerful figure among the Innocent.\n"
       "He clung to the conviction that Zora should be ruled by the Innocent "
       "themselves and not by the new race. To that end he imprisoned his lord "
       "Arthur and sought to control the Civilians as he pleased and rule "
       "Zora.\n"
       "But he met the resistance of the Civilians led by Jiron and his "
       "companions, and died in the decisive battle at X Point. With that "
       "battle the Innocent lost their dominion over Zora.",

    7: "A special forces unit of the Earth Federation Forces, made up of "
       "elites born on Earth. Its current commander is Jamitov Hymem.\n"
       "It was established in U.C. 0083 to keep watch on the Spacenoids, "
       "prompted by the colony drop operation 'Stardust' carried out by "
       "remnants of the Principality of Zeon. In truth, however, it was formed "
       "to oppress the Spacenoids, and would not stop short of massacring "
       "colony residents with poison gas. Its soldiers grew drunk on that "
       "power, sinking into an arrogance that had them boasting the Titans "
       "stood 'two grades above ordinary officers and men'.",

    8: "A military organization formed to oppose the tyranny of the Titans, "
       "centered on Brigadier General Blex Forer, who is also a member of the "
       "Earth Federation Assembly. Its formal name is the 'Anti Earth Union "
       "Government'.\n"
       "Supplied with mobile suits by its sponsor Anaheim Electronics, it "
       "resists the Titans' oppression of the Spacenoids. Many who share its "
       "cause have joined besides career soldiers, but the AEUG is ultimately "
       "an organization within the Earth Federation Forces. For that reason "
       "some hold that the fighting between them is no more than an internal "
       "military insurrection.\n"
       "It keeps a cooperative relationship with Karaba, the anti-Earth "
       "Federation organization on Earth, and their joint operations dealt "
       "heavy blows to the Titans' ground forces.",

    9: "A support organization for the AEUG on Earth, formed by Hayato "
       "Kobayashi. Its flagship is the Garuda-class large transport aircraft "
       "'Audhumla'.\n"
       "Moving in step with the AEUG, it fought the Titans alongside them from "
       "North America through to East Asia.\n"
       "Amuro Ray, a hero of the One Year War, later joined, and the group "
       "went on to build up its strength further, even developing the Dijeh on "
       "its own.",

    10: "A colony cluster in the L2 region on the far side of the Moon, also "
        "known as Munzo. It is the Side farthest from Earth, the place where "
        "Zeon Zum Deikun, who advocated Contolism, once lived, and the "
        "stronghold of the Principality of Zeon during the One Year War.\n"
        "With its ruling Zabi family wiped out to the last in the One Year "
        "War, the Principality of Zeon has since been reborn as the Republic "
        "of Zeon. In the Gryps Conflict, however, it has been forced into "
        "cooperating with the Titans.",

    11: "The doctrine that by moving the foundations of their lives into "
        "space, humankind can attain the 'Newtype' - a new innovation of the "
        "species adapted to space.\n"
        "Advocated by Zeon Zum Deikun, this thinking spread widely among the "
        "Spacenoids who resented the Earth Federation government. Zeon then "
        "had Side 3 declare independence as the Republic of Zeon in order to "
        "put Contolism into practice.\n"
        "But as it merged with 'Elezm', which held that humans should live in "
        "space and revere Earth as a holy land, and with 'Sidezm', which held "
        "that colonies should be recognized as nations Side by Side, it drew "
        "still greater resentment from the Earthnoids living on Earth. The "
        "pressure on the Spacenoids grew harsher as a result, and the two came "
        "to stand on the brink of open conflict.\n"
        "Even so, Zeon sought a settlement through dialogue with the Federation "
        "government - only to die with his work half done. After his death the "
        "Zabi family twisted Contolism into the claim that 'the Spacenoids are "
        "the chosen people', renamed it 'Zeonism', and used it in the One Year "
        "War that broke out against the Earth Federation.",

    12: "The politician who advocated Contolism - that humankind should "
        "advance into space - and who led the Spacenoids. He later had Side 3 "
        "declare independence as the Republic of Zeon. He is also the father "
        "of Char Aznable, known as Quattro Bajeena.\n"
        "He foresaw the birth of the 'Newtype', humans adapted to the space "
        "environment, and kept up patient negotiations with the Earth "
        "Federation to protect Earth's environment and realize that "
        "innovation. But those around him grew impatient with the high-handed "
        "attitude of the Earth Federation government, and came to believe the "
        "Spacenoids' long-held wish should be made known to the world by "
        "force.\n"
        "It was then that Zeon died suddenly, and his hardline aide Degin Sodo "
        "Zabi became his successor. Degin turned the Republic into the "
        "Principality of Zeon and declared war on the Earth Federation, "
        "placing his kin in the military's key posts. From this, the "
        "prevailing theory is that Zeon's death was an assassination by the "
        "Zabi family.",

    13: "The armed forces held by the Inglessa and Borjarno territories. They "
        "are called by the name of the territory they belong to, as in the "
        "'Inglessa Militia'.\n"
        "Until direct negotiations with the Moonrace began, they possessed "
        "only weapons that recalled the age of the Industrial Revolution, such "
        "as biplanes and cannon. But ever since the Turn A Gundam emerged from "
        "the White Doll, they have unearthed mobile suits one after another "
        "from the Mountain Cycles and strengthened their armament.",
}
