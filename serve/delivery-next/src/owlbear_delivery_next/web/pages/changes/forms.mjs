import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { DIALOG, REVERT, show, draft, notify, send } from "./state.mjs";
import { button, external, field, choice, tick, hd, text, list, row, panel, info } from "./widgets.mjs";
import { taskRounds } from "./progress.mjs";

export function questionForm(q, d) {
  const key = `${d.key}:question:${q.id}`, mine = draft(key, () => ({}));
  if (mine.option !== undefined && !q.options.some((o) => o.id === mine.option)) delete mine.option;  // withdrawn
  const answer = async () => {
    const picked = q.options.some((o) => o.id === mine.option) ? mine.option : null, words = mine.text ?? "";
    const chosen = q.options.find((o) => o.id === picked), told = chosen && consequence(chosen, d);
    if (told && !(await ask(told))) return;
    send("/answers", { question: q.id, option: picked, text: words }, d, key);
  };
  return panel(`Question ${q.id}`, key, text(q.text, { weight: "semibold" }),
    q.options.length ? choice(key, "option", "Choose an option", q.options) : nothing,
    field(key, "text", "Your answer in words"), button("Answer", answer));
}

// The owner's choice after the final review's last round (TD-217): the plan tasks to rebuild, those with an open
// finding ticked for him; with none ticked the work is accepted as done. A kept task that shares changed files with a
// ticked one may depend on it: said beside it, above the button and in the confirmation.
export function retryForm(q, r, d) {
  const key = `${d.key}:retry:${q.id}:${r.attempt}:${r.head}`;
  const mine = draft(key, () => ({ ticked: r.tasks.filter((t) => t.ticked).map((t) => t.id) }));
  const ticked = () => r.tasks.filter((t) => mine.ticked.includes(t.id)).map((t) => t.id);
  const risks = () => {
    const on = new Set(ticked());
    return r.tasks.filter((t) => !on.has(t.id)).map((t) => [t, t.shares.filter((x) => on.has(x))])
      .filter(([, hit]) => hit.length).map(([t, hit]) => `${t.id} may depend on ${hit.join(", ")}: they share `
        + "changed files");
  };
  const said = risks(), n = ticked().length;
  const flip = (id) => (on) => {
    mine.ticked = on ? [...new Set([...mine.ticked, id])] : mine.ticked.filter((x) => x !== id);
    show();
  };
  const decide = async () => {
    const picked = ticked(), why = risks();
    const titled = picked.map((id) => `${id}: ${r.tasks.find((t) => t.id === id).title}`);
    const sure = await ask(picked.length ? {
      title: `Rebuild ${picked.length} task${picked.length > 1 ? "s" : ""}?`, yes: "Rebuild", no: "Back to the tasks",
      now: "Delivery undoes the work of these tasks and their repairs in one commit on the branch; the rejected head "
        + "stays archived on a branch:", items: [...titled, ...why.map((s) => `Kept: ${s}`)],
      then: "Fresh builders build them again in plan order, each reviewed in its own rounds; the last one also runs "
        + "every other task's checks. The final review then looks at the result once more. This uses AI credits.",
      after: "An approval to merge no longer counts.",
      instead: "The question stays open.",
    } : {
      title: "Accept as done?", yes: "Accept as done", no: "Back to the tasks",
      now: r.unmet.length
        ? "The final review completes. Its remaining findings report these criteria unmet; you accept them as "
          + "they are, as your decision:"
        : "The final review completes; its remaining findings are recorded as accepted by you. None of them names "
          + "an acceptance criterion.",
      items: r.unmet,
      then: `Delivery publishes the Change. ${merging(d)}.`,
      instead: "The question stays open.",
    });
    if (sure) {
      const body = picked.length ? { option: "rebuild", tasks: picked, attempt: r.attempt, head: r.head }
        : { option: "accept" };
      send("/answers", { question: q.id, ...body }, d, key);
    }
  };
  const replan = async () => {
    const option = mine.from;
    if (!option) return notify("Choose where planning starts from: the existing code or a clean state.");
    if (await ask({
      title: "Plan again from the brief?", yes: "Plan again", no: "Back to the options",
      now: option === "clean" ? "Delivery undoes the Change's work in one commit, so the branch holds the target's "
        + "code again; the rejected head stays archived on a branch." : "The code stays as it is.",
      then: "The planner makes a new plan from the brief and the challenger checks it; the new plan's tasks replace "
        + "the old ones, and the final review counts its rounds anew. This uses AI credits.",
      after: "An approval to merge no longer counts.",
      instead: "The question stays open.",
    })) send("/answers", { question: q.id, option }, d, key);
  };
  return panel(`Question ${q.id}`, key, text(q.text, { weight: "semibold" }), hd(4, "Plan tasks to rebuild", "sm"),
    r.tasks.map((t) => html`${tick(`${t.id}: ${t.title}`, mine.ticked.includes(t.id), flip(t.id))}
      ${taskRounds(t.id, d, " (rebuild list)")}
      ${text(said.find((s) => s.startsWith(`${t.id} `)) ?? "", { size: "xs" })}`),
    html`<div>${said.map((s) => text(s, { size: "xs", weight: "semibold" }))}</div>`,
    row(button(n ? `Rebuild ${n} task${n > 1 ? "s" : ""}` : "Accept as done", decide, { icon: "check", aria: DIALOG }),
      button("Another round", () => send("/answers", { question: q.id, option: "another" }, d, key),
        { variant: "secondary" })),
    choice(key, "from", "Plan again from the brief, starting from", [
      { id: "replan", label: "the existing code" },
      { id: "clean", label: "a clean state: the Change's work undone" },
    ]),
    button("Plan again from the brief", replan, { variant: "secondary", aria: DIALOG }));
}

// What an answer sets off when it is more than going on: ending the Change, passing over a finding, going back.
function consequence(o, d) {
  const choices = { yes: o.label, no: "Back to the options", instead: "Choose another option." };
  if (o.next === "abandon") {
    return { title: "Abandon this Change?", yes: "Abandon", no: "Keep the Change",
      now: "The Change ends here and is marked abandoned. There is no restore.",
      then: `Delivery closes ${d.pr ? `pull request #${d.pr}` : "its pull request if one is open"}, saves work only `
        + "the worktree holds, and removes the worktree. Branches are kept.",
      after: "The branch and the saved work stay for reference; start a new Change to try again.",
      instead: "The question stays open and the Change waits for your answer." };
  }
  if (o.next === "done") {
    return { ...choices, title: `${o.label}?`,
      now: "What this question raised stays as it is; nothing is sent back to be fixed.",
      then: "Delivery goes on with the next step by itself.",
      after: "Pause at any time; a pause takes effect after the running step." };
  }
  if (o.id === "drop") {
    return { ...choices, title: "Drop this finding?",
      now: "The finding is not fixed. Your note in words tells later reviewers why.",
      then: "Delivery asks about the next disputed finding, or goes on without this one." };
  }
  if (o.next === "accept") {
    return { ...choices, title: `${o.label}?`,
      now: "Delivery cannot prove which model produced this result; you take it as it is. Its verdict still "
        + "applies, including any repair it asks for.",
      then: "Delivery goes on from this result." };
  }
  if (o.next === "shape") {
    return { ...choices, title: "Go back to the brief?",
      now: "The Change returns to its brief. Work already done is kept for now.",
      then: "Nothing runs until you revise the brief in the shaping chat and approve the new version here.",
      after: "The new brief decides which work is kept or redone." };
  }
  if (o.next === "plan") {
    return { ...choices, title: "Plan again?",
      now: "The Change returns to planning. Work already done is kept.",
      then: "The planner makes a new plan from the brief and the challenger checks it; this uses AI credits." };
  }
  return null;
}

// How the Change ends once every gate passed: the project's merge setting decides.
export function merging(d) {
  return d.asks_merge ? "Delivery asks you before merging" : "Delivery merges by itself once every check passes";
}

// What an automatic merge sets off, told at the owner's last gate before it.
export function finale(d) {
  const pr = d.pr ? `pull request #${d.pr}` : "the pull request";
  return `Delivery merges ${pr} into ${d.target} by itself once its checks pass, `
    + `${d.deletes_branch ? "deletes the branch, " : ""}removes the worktree after saving work only it holds, and `
    + `updates your local ${d.target} if that is safe.`;
}

export function criteriaPanel(d) {
  return info("Your visual criteria", text("Every later visual round checks these until you withdraw them."),
    d.owner_criteria.map((k) => {
      const withdraw = async () => {
        const stop = await ask({
          title: `Stop checking ${k.id}?`, yes: "Stop checking", no: "Keep it",
          now: `“${k.text}” is no longer checked in later visual rounds; it stays in this Change's history.`,
          after: "There is no restore. A comment on a later Fail adds a new criterion.",
          instead: "Every later visual round keeps checking it.",
        });
        if (stop) send(`/criteria/${encodeURIComponent(k.id)}/withdraw`, {}, d);
      };
      return row(text(`${k.id}: ${k.text}`), button("Withdraw", withdraw, { variant: "secondary", aria: DIALOG }));
    }));
}

export function checkForm(check, d) {
  const key = `${d.key}:check:${check.id}:${JSON.stringify(check.inputs)}`, mine = draft(key, () => ({}));
  const result = (passed) => ({ check: check.id, passed, note: mine.note ?? "", inputs: check.inputs });
  const last = !d.asks_merge && d.checks.every((c) => c.id === check.id || c.passed === true);
  const passed = async () => {
    const body = result(true);
    if (last && !(await ask({
      title: `Pass ${check.id}, the last step before merging?`, yes: "Pass and merge", no: "Not yet",
      now: `${check.id} is recorded as passed.`,
      then: `It is the last check. ${finale(d)}`,
      after: REVERT,
      instead: "Nothing merges; the check stays open.",
    }))) return;
    send("/check-results", body, d, key);
  };
  const failedCheck = async () => {
    const why = (mine.note ?? "").trim(), body = result(false);
    if (!why) return notify("Say what failed: the builder gets it as the fix task.");
    if (await ask({
      title: `Report ${check.id} as failed?`, yes: "Send to the builder", no: "Keep checking",
      now: "The builder gets this fix task:", items: [why],
      then: "Delivery fixes it, reviews the fix and prepares the check again; this uses AI credits. Then it asks you "
        + "to check again.",
      instead: "The check stays open; you can still mark it passed.",
    })) send("/check-results", body, d, key);
  };
  return panel(`Your check ${check.id}`, key, list(check.steps, true),
    check.expect ? text(`Expected: ${check.expect}`, { weight: "semibold" }) : nothing,
    check.url ? row(external("Open the preview", check.url),
      text(check.url, { size: "xs", color: "contrast-medium", tag: "span" })) : nothing,
    field(key, "note", "What failed (needed for Failed; the builder gets it as the fix task)"),
    row(button("Passed", passed, { icon: "check", aria: last ? DIALOG : undefined }),
      button("Failed", failedCheck, { variant: "secondary", icon: "close", aria: DIALOG })));
}

const CHECKED = { passed: "success", success: "success", failed: "error", failure: "error", error: "error" };

export function mergeForm(m, d) {
  const head = m.head.slice(0, 7), key = `${d.key}:merge:${m.head}`;
  const approve = async () => {
    const sure = await ask({
      title: `Merge pull request #${m.pr} at ${head}?`, yes: "Merge", no: "Not now",
      now: `Delivery merges exactly ${head} into ${d.target} (${m.method}). If the pull request gets a new head `
        + "first, this approval no longer counts.",
      then: `It checks the gates once more, merges, ${d.deletes_branch ? "deletes the branch, " : ""}removes the `
        + `worktree after saving work only it holds, and updates your local ${d.target} if that is safe.`,
      after: `The change is on ${d.target}; reversing it needs a revert you make yourself.`,
      instead: "Nothing merges. The pull request stays open; comments on it come back to Delivery as work.",
    });
    if (sure) send("/merge-consent", { head: m.head }, d, key);
  };
  return panel(`Merge PR #${m.pr}`, key,
    text(`Delivery merges this exact head (${m.method}) once you approve it; a new head needs a fresh approval.`),
    row(external(`PR #${m.pr}`, m.url), external("Diff summary", m.diff)),
    m.void ? text(`Changed since ${m.void.slice(0, 7)}: ${m.delta}`, { color: "error" }) : nothing,
    text("Checks at this head", { size: "xs", weight: "semibold" }),
    m.checks.length ? row(m.checks.map((c) => html`<p-tag variant=${CHECKED[c.state] ?? "secondary"}
      compact="true">${c.name}: ${c.state}</p-tag>`)) : text("No checks reported", { size: "xs",
      color: "contrast-medium" }),
    text(`Head ${m.head}`, { size: "xs", color: "contrast-medium" }),
    button(`Approve merging ${head}`, approve, { icon: "check", aria: DIALOG }));
}

export function restartButton(d) {
  const restart = async () => {
    const sure = await ask({
      title: "Restart the final review loop?", yes: "Restart", no: "Keep it",
      now: "A fresh final review starts at round 1 and reviews the whole Change; this uses AI credits.",
      then: "Its findings go to a builder as before, under the same round rules.",
      after: "The earlier rounds stay in this Change's history. An open question about them closes, and an approval "
        + "to merge no longer counts.",
      instead: "The review loop goes on as it is.",
    });
    if (sure) send("/restart-review", {}, d);
  };
  return button("Restart review loop", restart, { variant: "secondary", icon: "refresh", aria: DIALOG });
}

export function pullbackNote(p, d) {
  const behind = p.state === "behind", title = `Pull-back: ${p.state}`;
  const pull = async () => {
    const sure = await ask({
      title: `Update your local ${d.target}?`, yes: "Update", no: "Leave it",
      now: `Delivery moves your local ${d.target} to the merged one, replaying any local commits on top; their `
        + "commit IDs change.",
      after: "If local changes touch the same files, the update stops and says why.",
      instead: `Your local ${d.target} stays behind; Pull stays here.`,
    });
    if (sure) send("/pull", {}, d);
  };
  return html`<p-inline-notification state=${behind ? "warning" : "success"} heading=${title} heading-tag="h3"
    dismiss-button="false" action-label=${behind ? "Pull" : nothing} action-icon=${behind ? "refresh" : nothing}
    @action=${behind ? pull : nothing}>${p.reason || ""}</p-inline-notification>`;
}
