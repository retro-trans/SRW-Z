Ground work:
- Build a glossary DB containing character names, locations and organizations, so that when an agent translates they can find the correct spelling. This keeps the entire translation consistent. If the game has a wiki or any other source on the internet (usually a wiki of the related game/anime) use it to make sure the names are consistent. If there is no entry in the database, ask the orchestrator to research it and add it to the glossary.
+ For each character, research the name, the nickname, the gender, the personality (hothead, noble...) and the position (captain, princess...), and link the source for what you found.
- Determine the maximum number of characters for each type of text we are going to translate. Better: capture a screen where it appears at maximum (or near maximum) size and measure it.

When translating dialogue:
- Always relocate the text to new memory so the translation fits, instead of trying to squeeze it into the existing bytes. In other words, make sure there is no byte budget.
- Each agent translates a slice: 80 consecutive rows of dialogue.
- An agent can check the slice before or after its own to understand the context.
- Agents must report rows-examined vs rows-in-slice. If a row can't be verified even after checking adjacent slices, leave it and say so.
- If the dialogue refers to another person, do not assume their gender (so do not assume he/she) without knowing who it is. If it is someone unknown, use a gender-neutral term.
- Do not infer gender from a name.
- If the translation doesn't fit the limit, compress the meaning or abbreviate — never drop the end of the sentence. If it still does not fit, leave the row and flag it.

When translating any kind of text:
- Do not hesitate to use abbreviations.
- Do not strip strange characters (control codes, links, placeholders), and when they stand in for text that appears at runtime, count the width they will expand to, not the width they occupy.
- When the corpus and the wiki disagree, the wiki wins.

When proofreading:
- Use agents to fix meaning; use scripts to fix names that are incorrect compared to the glossary.
- Once a name is fixed by a script, add it to the agents' do-not-touch list, or they keep re-fixing it and disagreeing with each other about the spelling.
- Apply agent fixes FIRST, run the name script AFTER. Agents work from a stale export, so an agent edit can reintroduce an old spelling.
- When an agent reports a wrong name, do not just fix that row — scan the whole corpus for that name first. One report usually means dozens of rows, including name fields agents can't edit.
- Fix what is wrong; leave what is merely different. Do not rewrite a line because you would have phrased it differently.

About scripts:
- Dry-run every script and read the sample output before it touches the data. Check what it would change, not just how many rows.
