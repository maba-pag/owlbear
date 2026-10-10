---
name: delivery
description: Shape a Change into a brief with the owner, save it for approval, show Delivery status, answer worker questions
---

# Delivery in chat

Delivery turns an approved brief into a reviewed, merged pull request. Chat is for the
conversation; approvals, merge consent and recovery happen in the Changes page.

## Shape a brief

1. Read the repository parts the idea touches before asking anything.
2. Ask the owner one question at a time, only what the code cannot answer: the outcome, what
   must be true when it is done, what is out of scope, and whether something can only be checked
   by a person (for example by looking at a page).
3. Write acceptance criteria a test or command can check. A check only a person can perform
   becomes a person check with steps and what to expect.
4. For a UI change set `ui` and ask which page states must render: each visual state has a
   `name`, a `path` under the preview root and what to `expect`. If the project has no preview to
   render, offer three choices: add one in this Change, declare a person-only visual check, or
   change the scope.
5. Propose a split when the idea is more than one reviewable pull request.
6. Call `save_brief` with title, outcome, criteria, scope, person checks and any visual states. Leave `change`
   empty for a new Change; pass its handle (`c3`) to revise. If it returns errors, each names a
   field: fix those and call again. Never invent a handle.
7. Tell the owner the returned `next` step: approve the brief version in the Changes page, using the
   link exactly as given (it carries the page's access token). Nothing starts before that approval.
8. After approval a reviewer challenges the brief. Its findings come back as a question: revise the
   brief with the owner (call `save_brief` again with its handle), or answer it to plan as it is.

## Status and questions

- Call `show_status` when the owner asks what is happening. Repeat each line as given. If it
  says Delivery is not running, give its start action; nothing advances until it runs. If
  `readiness` lists a problem, give the owner its fix.
- A question with `answer_in: chat` is a worker's question: put it to the owner as it stands,
  then call `answer_question` with its id, the chosen option id and the owner's words.
- A question with `answer_in: changes-page`, merge consent and every stop are the owner's
  decisions in the Changes page. Point there; do not answer them for the owner.
