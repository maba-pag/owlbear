---
name: delivery
description: Shape a Change into a brief with the owner, save it for approval, show Delivery status, answer worker questions
---

# Delivery in chat

Delivery turns an approved brief into a reviewed, merged pull request. Chat is for the
conversation; approvals, merge consent and recovery happen in the Changes page.

## Shape a brief

1. Read the repository parts the idea touches before asking anything. To continue an existing
   Change, call `show_status` with its handle and read its saved brief back to the owner, its
   decisions and non-goals included, before changing any of them.
2. Ask the owner one question at a time, with the answer you recommend and why, and only what the
   code cannot answer: the outcome, what must be true when it is done, what is out of scope, and
   whether something can only be checked by a person (for example by looking at a page). Ask for
   the observable pain, the current workaround, and which statements are evidence and which are
   assumptions. Never infer a business constraint from code. Depth follows uncertainty and stakes,
   not a count: ask until no material gap remains. A reduction of what the owner asked for is a
   scope choice the owner makes explicitly.
3. Write acceptance criteria a test or command can check; a criterion may state what must not
   happen. A check only a person can perform becomes a person check with steps and what to expect.
4. For a UI change ask which page states must render: each visual state has a `name`, a `path`
   under the preview root and what to `expect`. Write each expectation as what a screenshot shows
   ("the Dark mode button is filled and darker than in light mode"), not as a state only the code
   knows ("the button is pressed"); ask the owner what should be visible when that is unclear.
   A state can need clicks or typing first (open a menu, search for a name): each step clicks a
   control or types into a field, named exactly as the page shows it. Steps run only on a
   test copy the project's declared preparation options prepare. If the project has no preview to render, offer three choices: add
   one in this Change, declare a person-only visual check, or change the scope.
5. Propose a split when the idea is more than one reviewable pull request.
6. Read back before saving for approval (see Read-Back below).
7. Call `save_brief` with title, outcome, criteria, scope, non-goals (what the owner agreed is out),
   decisions and person checks. `decisions` holds every choice the owner made and each consequential
   choice of yours, as question, answer and origin: `decided` (the owner chose it), `approved` (it
   came with something the owner approved without being asked) or `autonomous` (you chose it). Send
   all of them again with every save. `specified` names the criteria the owner stated himself (`AC-1`
   is the first); a state or person check he stated himself gets `owner: true`. Everything else is
   your proposal, and the approval page shows it as such. Leave `change` empty for a new Change; pass its handle
   (`c3`) to revise. For a UI change then call
   `save_visual_check` with that handle, `ui`, the states and their steps. If either returns
   errors, each names a field: fix those and call again. Never invent a handle.
8. Tell the owner the returned `next` step: approve the brief version in the Changes page, using the
   link exactly as given (it carries the page's access token). Nothing starts before that approval.
9. After approval a reviewer challenges the brief. Its findings come back as a question: revise the
   brief with the owner (call `save_brief` again with its handle), or answer it to plan as it is.

## Read-Back

Before saving for approval, play back every choice the owner made and your own consequential ones
(those that change what the owner sees or does, cost, safety or reversibility; list yours with a
one-line consequence). Ask one decision per question, paraphrased at the level of the owner's
intent, never quoting the record, with the structured question tool when there is one:

- one to four close variants of the recorded choice, as many as really differ in consequence, the
  matching one at a varying position and never verbatim; a one-line consequence where it helps;
- one or two other directions where real ones exist, the opposite among them;
- then, always in this order: "take your recommendation (…)" with your recommendation named in the
  brackets, "none of these: show me more options", "explain first"; no other recommendation mark;
  free text stays open.

A chosen variant or direction is `decided`. "Take your recommendation": state your choice and why,
record it `autonomous`. "Show me more options": ask again with options across directions, each with
benefits, costs, risks and its own percentage that it is a good choice (they need not add up), your
recommendation marked. "Explain first": explain each option's consequences neutrally, then ask again.
Free text is never recorded as written: offer two to five readings that fill its gaps differently,
plus "your words as written", "show me more readings" and "explain first". When the direction itself
is in doubt, ask the direction first, then its variants.

## Status and questions

- Call `show_status` when the owner asks what is happening. Repeat each line as given. If it
  says Delivery is not running, give its start action; nothing advances until it runs. If
  `readiness` lists a problem, give the owner its fix.
- A question with `answer_in: chat` is a worker's question: put it to the owner as it stands,
  then call `answer_question` with its id, the chosen option id and the owner's words.
- A question with `answer_in: changes-page`, merge consent and every stop are the owner's
  decisions in the Changes page. Point there; do not answer them for the owner.
