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
4. Propose a split when the idea is more than one reviewable pull request.
5. Call `save_brief` with title, outcome, criteria, scope and person checks. Leave `change`
   empty for a new Change; pass its handle (`c3`) to revise. If it returns errors, each names a
   field: fix those and call again. Never invent a handle.
6. Tell the owner the returned `next` step: approve the brief version in the Changes page.
   Nothing starts before that approval.

## Status and questions

- Call `show_status` when the owner asks what is happening. Repeat each line as given. If it
  says Delivery is not running, give its start action; nothing advances until it runs.
- A question with `answer_in: chat` is a worker's question: put it to the owner as it stands,
  then call `answer_question` with its id, the chosen option id and the owner's words.
- A question with `answer_in: changes-page`, merge consent and every stop are the owner's
  decisions in the Changes page. Point there; do not answer them for the owner.
