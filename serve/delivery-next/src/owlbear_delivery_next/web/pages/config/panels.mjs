// The layered groups' panels: Agents and runs, Guardrails, and Checks and merge. Each setting's row carries the id the
// unset list links to (GW8RT6).

import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { held, here, project } from "/assets/ui.mjs";
import { ROUNDS, LOOPS, back, state } from "./state.mjs";
import {
  cell, row, setting, table, numberCell, designFailures, widths, sessionsAtOnce, prLabels, prMarker, subagentsCell,
  curatorThreshold, spotterCell, prefRows, USER_KEYS, userConfig, userConfigLabel, contextCell, editable,
  guardLevel, githubAccount, more,
} from "./cells.mjs";

const SPOTTER = [
  ["switch", "On or off", "On or off"],
  ["hand_off_fitness", "Hand-off fitness: the result should not be accepted as it stands", "Hand-off fitness"],
  ["course_and_constraints", "Course and constraints: recoverable work heading materially wrong",
    "Course and constraints"],
  ["outside_state_changes", "Outside-state changes: a consequential change beyond the task's files",
    "Outside-state changes"],
  ["irreversible_harm", "Irreversible harm, in the Spotter's own judgement; it takes precedence", "Irreversible harm"],
  ["steer_share", "Steered share (%)", "Steered share"],
  ["intervention_cap", "Steering notes at most, per step or chat turn", "Notes at most"],
  ["verbose", "Verbose", "Verbose"],
  ["verbose_until", "Verbose until (YYYY-MM-DD; empty: no end)", "Verbose until"],
  ["looks", "Looks (hand-off, plan, state-change, sample)", "Looks"],
  ["sample_rate", "Sampled actions (%)", "Sampled actions"],
  ["look_credit_limit", "Credit limit per look (credits)", "Credit limit per look"],
];

// The way to the role's compaction on Metrics: back to the filters a compaction row's link came from, else the
// role's on this project, or on every project from This machine or Global; unsaved edits keep the page.
function toMetrics(role) {
  if (!project) return nothing;
  let href = back;
  if (!href) {
    const to = new URL(here({ in: state.layer === "project" ? state.loaded.folder || project : "", agent: role },
      "/metrics#compaction"), location.href);
    if (!to.searchParams.get("in")) to.searchParams.set("in", "");  // all projects, not the bar's clone's
    href = `${to.pathname}${to.search}${to.hash}`;
  }
  const leave = (e) => {
    if (e.button === 0 && !(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) && held()) e.preventDefault();
  };
  return html`<br><a class="compaction-link" href=${href} @click=${leave}>Compaction on Metrics</a>`;
}
const none = () => cell(html`<p-text color="contrast-medium">n/a</p-text>`);  // the shaper's chat and a Spotter look

export function agentsGroup() {
  const loop = (owner) => ROUNDS.map(([f]) =>
    (owner === "final_review" ? `final_review.${f}` : `agents.${owner}.${f}`));
  return html`
    <section class="panel" aria-labelledby="agents-title">
      <p-heading size="lg"><h2 id="agents-title" tabindex="-1">Agents</h2></p-heading>
      ${table("Agents: they apply to the next session",
        ["Agent", "Model", "Effort", "Context", "Subagents", "Minutes per session"],
        "agents-rows", Object.keys(state.loaded.settings.agents).map((role) => {
          const timed = !["shaper", "spotter"].includes(role);
          return setting(`set-agents-${role}`, html`${role === "shaper" ? "shaper (a recommendation)"
            : role}${toMetrics(role)}`,
          ["model", "effort", "context", ...(timed ? ["subagents", "minutes"] : [])].map((f) => `agents.${role}.${f}`),
          editable(role, "model"), editable(role, "effort"), contextCell(role),
          timed ? subagentsCell(role) : none(),
          timed ? numberCell(role, "minutes", "Minutes per session", `set-agents-${role}-minutes`) : none());
        }))}
      ${more("What the columns mean",
        "Subagents: an agent may start the runtime's built-in subagents, such as explore or code-review, for side "
        + "questions. They work under the step's own permissions, and Delivery records each one; Maintenance shows "
        + "their use per agent.",
        "Minutes per session, 1 to 480: a session ends after this many minutes in total; its step then counts as a "
        + "failed attempt and runs again. The shaper's chat and the Spotter's looks are no sessions of their own, so "
        + "they show n/a.",
        "The credits under a model are its rates at the row's context tier.")}
      <p-text id="shaper-note" size="xs" color="contrast-medium">The shaper's model and effort are a recommendation
        (TD-328): Delivery's own turns in the shaping chat use them; what you type there runs on the chat's model
        picker, which the chat reminds you of once.</p-text>
      <p-text id="models-note" size="xs" color="contrast-medium" aria-live="polite">${state.modelsNote}</p-text>
    </section>
    <section class="panel" aria-labelledby="rounds-title">
      <p-heading size="lg"><h2 id="rounds-title" tabindex="-1">Challenge rounds</h2></p-heading>
      <p-text>A reviewer and the worker go back and forth in rounds. A round with few new findings is the last; after
        the last allowed round with many, Delivery asks you. A loop keeps the values it started with.</p-text>
      ${table("Challenge rounds: they apply to loops that start after a save", ["Loop", ...ROUNDS.map(([, l]) => l)],
        "rounds", LOOPS.map(([owner, said]) => setting(`set-rounds-${owner}`, said, loop(owner),
          ...ROUNDS.map(([field, label]) => numberCell(owner, field, label)))))}
      <p-text size="xs" color="contrast-medium">Findings per round: 1 to 20. "Last round at or below" must be lower
        than "ask you at or above", which may not exceed the findings per round. The final review inherits the
        builder's values.</p-text>
    </section>
    <section class="panel" aria-labelledby="at-once-title">
      <p-heading size="lg"><h2 id="at-once-title" tabindex="-1">Sessions at once</h2></p-heading>
      <p-text>A step waits for a free slot before it starts. A visual check runs its judges in waves of the slots it
        gets; an Impeccable update takes one slot per session. This machine's total holds across its projects.</p-text>
      ${table("Sessions at once: they apply to the next step that starts", ["Setting", "Value"], "at-once",
        [setting("set-sessions", "Agent sessions at once in one project", ["sessions"], sessionsAtOnce())])}
      <p-text size="xs" color="contrast-medium">At least 1. Steps running now keep their sessions.</p-text>
    </section>`;
}

export function guardrailsGroup() {
  return html`
    <section class="panel" aria-labelledby="spotter-title">
      <p-heading size="lg"><h2 id="spotter-title" tabindex="-1">Spotter</h2></p-heading>
      <p-text>The Spotter looks at an agent's work beside it: at hand-offs, plans, state changes and a sample of
        actions. Its model, effort and context are the spotter row in Agents and runs.</p-text>
      ${more("How the Spotter acts and stops",
        "It files each finding under one of four categories and acts as that category's setting says, in Delivery's "
        + "steps and in the VS Code chats of the enrolled folders (a terminal chat is not followed): it records it, "
        + "steers the agent, refuses its hand-off, stops and resumes it with a note, stops it to ask you, or shows it "
        + "to you on the Improvement page. Irreversible harm acts from any look, in every Change and chat. Otherwise "
        + "sampled and state-change looks only record, and steering, refusing and stopping to resume act only in a "
        + "Change or chat drawn into the steered share; steering notes stop at the set number per step or chat turn. "
        + "Retro grades every record. The enrolled chats are a machine setting.",
        "Each look stops at its own credit limit, also when replayed: once the spend the runtime reports reaches it, "
        + "the look is stopped and its record says so; a call already under way still finishes, so a look may pass "
        + "its limit a little. There is no daily budget.",
        "Off stops its looks and the recording of new outside writes for each Change's page; the reports already "
        + "recorded stay, and steps no longer need its other settings.")}
      ${table("Spotter: it applies to the next look", ["Setting", "Value"], "spotter", SPOTTER.map(([field, name,
        label]) => setting(`set-spotter-${field}`, name, [`spotter.${field}`], spotterCell(field, label))))}
    </section>
    <section class="panel" aria-labelledby="user-config-title">
      <p-heading size="lg">
        <h2 id="user-config-title" tabindex="-1">Your instructions, skills and memory</h2>
      </p-heading>
      <p-text>Whether a Delivery step reads your own Copilot instructions, skills and memory. None has a default:
        until all three are set, a step asks you to set them instead of starting its session.</p-text>
      ${more("What each setting does",
        "A Delivery step reads its repository's instructions and Delivery's own skills. Switched on, it also reads "
        + "your own instruction files in your Copilot folder (instructions/ and copilot-instructions.md, links "
        + "followed), and is offered your own skills there (skills/), never one named as Delivery's. A plugin's files "
        + "and your agents stay off either way.",
        "Copilot Memory on lets every Delivery session recall the memories Copilot keeps for this repository, and "
        + "the planner, preparer, builder, updater and test curator may save or vote on them; the Spotter and Retro "
        + "never use it. A memory saved this way skips OwlBear's memory curation and reaches your later hand-run "
        + "chats in this repository, so off is recommended.")}
      ${table("Your instructions, skills and memory: they apply to the next session", ["Setting", "Value"],
        "user-config", USER_KEYS.map((key) => setting(`set-${key}`, userConfigLabel(key), [key], userConfig(key))))}
    </section>
    <section class="panel" aria-labelledby="curation-title">
      <p-heading size="lg"><h2 id="curation-title" tabindex="-1">Memory curation</h2></p-heading>
      <p-text>The memory curator states its confidence in everything it would do to an entry. At or above this
        threshold it acts alone, Make global included; below it, it asks you in an interactive session and leaves the
        entry as it is in an automatic run.</p-text>
      ${table("Memory curation: it applies to the next curation", ["Setting", "Value"], "curation",
        [setting("set-curator_threshold", "Curator's confidence threshold (%)", ["curator_threshold"],
          curatorThreshold())])}
      <p-text size="xs" color="contrast-medium">50 to 100; one value for every project and machine.</p-text>
    </section>
    <section class="panel" aria-labelledby="guard-title">
      <p-heading size="lg"><h2 id="guard-title" tabindex="-1">Shell guard</h2></p-heading>
      <p-text>Delivery reads each shell command a step runs for ways around Git hooks or signing, and for
        force-pushes. It has no default: until it is set, a step asks you to set it instead of starting its
        session.</p-text>
      ${more("What each level does",
        "Strict refuses the ways it knows and their new variants and warns on weak signs; standard refuses only the "
        + "ways it knew before and warns on the rest; lenient warns on all of them and refuses none; off checks none "
        + "of them.",
        "A warning reaches the agent and the step's journal. At every level a read-only step's writes stay refused, "
        + "and so do the step's folder, tool and file rules.")}
      ${table("Shell guard: it applies to the next step", ["Setting", "Value"], "guard",
        [setting("set-guard_level", "Shell guard level", ["guard_level"], guardLevel())])}
    </section>`;
}

export function checksGroup() {
  const loaded = state.loaded, text = (v) => cell(html`<p-text>${v}</p-text>`);
  const share = (n, of) => `${n} (${Math.round((100 * n) / of)}%)`;
  return html`
    <section class="panel" aria-labelledby="general-title">
      <p-heading size="lg"><h2 id="general-title" tabindex="-1">Visual checks</h2></p-heading>
      ${table("Visual check settings: they apply to the next visual check", ["Setting", "Value"], "general",
        [setting("set-widths", "Screenshot widths", ["widths"], widths()),
          setting("set-design_failures", "Design failures", ["design_failures"], designFailures())])}
      <p-heading size="md"><h3 id="agreement-title" tabindex="-1">Agreement with your visual decisions</h3></p-heading>
      <p-text id="impeccable" size="xs">${loaded.impeccable}</p-text>
      <p-text id="agreement-note" size="xs" color="contrast-medium">${loaded.agreement.length
        ? "From the decided rounds kept in the shared repository; below 20 rounds the numbers only inform."
        : "No decided visual rounds yet, or no shared repository is set up."}</p-text>
      ${table("How often each judge's verdict matched your Pass or Fail, per model",
        ["Judge", "Model", "Decided", "Agreed", "Disagreed", "Unsure"], "agreement",
        loaded.agreement.map((a) => row(...[a.judge, a.model, String(a.decided), share(a.agreed, a.decided),
          share(a.disagreed, a.decided), share(a.unsure, a.decided)].map(text))),
        { id: "agreement-table", hidden: !loaded.agreement.length })}
    </section>
    <section class="panel" aria-labelledby="merge-title">
      <p-heading size="lg"><h2 id="merge-title" tabindex="-1">Merge and cleanup</h2></p-heading>
      <p-text>How OwlBear merges a pull request, cleans up its branch and waits for CI.</p-text>
      ${more("Where these are set",
        "Each setting is set in this project, on this machine or globally; the project's value wins, then this "
        + "machine's, then the global one. None has a built-in default: a step that needs one asks you until it is "
        + "set.")}
      ${table("Merge and cleanup: they apply to the next merge", ["Setting", "Value"], "prefs", prefRows())}
      <p-text size="xs" color="contrast-medium">Seconds are whole numbers; blank inherits.</p-text>
    </section>
    <section class="panel" aria-labelledby="pr-title">
      <p-heading size="lg"><h2 id="pr-title" tabindex="-1">Pull requests</h2></p-heading>
      <p-text>What OwlBear adds to each pull request it opens, and the GitHub account it works on them as.</p-text>
      ${more("Which GitHub account",
        "The account that pushes, opens, labels, answers and merges this project's pull requests; blank uses the "
        + "layers above. repository-owner is the repository owner's account when gh has it, else maba-pag.",
        "The account must be signed in to gh (gh auth login); the account active in gh stays as it is.")}
      ${table("Pull request settings: they apply to the next pull request", ["Setting", "Value"], "pr",
        [setting("set-pr_labels", "Labels", ["pr_labels"], prLabels()),
          setting("set-pr_marker", "Marker line", ["pr_marker"], prMarker()),
          setting("set-github_account", "GitHub account", ["github_account"], githubAccount())])}
    </section>`;
}
