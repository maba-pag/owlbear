// The words each setting's Settings row shows, in one place: the rows read them and so do the unset list, Across
// projects and the change notices, so a name there is the name on the page. No imports (groups.mjs does the same).

// TD-209: a loop's round values, as the challenge rounds table names its rows and columns.
export const ROUNDS = [["max_rounds", "Rounds at most"], ["max_findings", "New findings per round at most"],
  ["last_round_at", "Last round at or below"], ["ask_owner_at", "Ask you at or above"]];
// D-01M6P1685N1R5W2PPV5SHKR2H0: the brief loop's wait before Delivery starts a missing challenge, the shaper's only.
export const WAIT = ["challenge_wait", "Challenge starts by itself after (minutes)"];
export const LOOPS = [["shaper", "Brief challenges (shaper)"], ["planner", "Plan challenges (planner)"],
  ["builder", "Task reviews (builder)"], ["final_review", "Final review"],
  ["updater", "Impeccable updates (updater)"]];

// The agents table's columns, in order; the shaper's row says its model and effort are a recommendation (TD-328).
export const COLUMN = { model: "Model", effort: "Effort", context: "Context", subagents: "Subagents",
  minutes: "Minutes per session" };
const AGENT_NAMES = {
  planner: "planner", builder: "builder", reviewer: "reviewer", challenger: "challenger",
  "design-judge": "design-judge", preparer: "preparer", shaper: "shaper (a recommendation)", updater: "updater",
  "test-reviewer": "test-reviewer", "test-curator": "test-curator", picker: "picker", curator: "curator",
  spotter: "spotter", retro: "retro", "retro-review": "retro-review", auditor: "auditor",
};
export function agentName(role) {
  if (!Object.hasOwn(AGENT_NAMES, role)) throw new Error(`No Settings name is known for the agent "${role}"`);
  return AGENT_NAMES[role];
}

// A Spotter row: its key, its name, its control's label.
export const SPOTTER = [
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

// A memory row: its key, its name, its control's label when that differs from the name, and its input mode.
export const RATINGS = [
  ["outstanding_boost", "Points an outstanding rating adds", "Points an outstanding rating adds to an entry's score",
    "decimal"],
  ["unremarkable_penalty", "Points an unremarkable rating takes off",
    "Points an unremarkable rating takes off an entry's score", "decimal"],
  ["stale_factor", "Skipped ratings per other rating before an entry is stale"],
];
export const RECALLS = [
  ["preflight_cap", "Lessons a step starts with, at most", "Lessons a step is told at its start, at most"],
  ["preflight_budget", "Characters of lessons a step starts with, at most",
    "Character budget for a step's starting lessons"],
  ["recall_limit", "Entries the recall tool returns when it is given no limit"],
  ["explore_slots", "Recall slots for the least-rated entries"],
  ["challenge_slots", "Recall slots for the least-outstanding entries"],
];
export const PURGE = [["purge_days", "Days a deleted entry waits before its file can be removed"]];

// R15: the five merge and cleanup preferences.
export const PREF_NAMES = { merge_method: "Merge method",
  delete_remote_branch: "Delete the remote branch after merging", ci_poll_seconds: "CI poll interval (seconds)",
  ci_start_window_seconds: "CI start window (seconds)", ask_before_merge: "Ask before merging" };

export const USER_NAMES = { load_user_instructions: "Your instructions in Delivery steps",
  load_user_skills: "Your skills in Delivery steps", load_user_memory: "Copilot Memory in Delivery sessions" };

// This machine's settings, by their field under machine.
export const MACHINE_LABELS = {
  channel: "Versions this machine takes", update_when_idle: "Update itself when idle",
  update_while_paused: "Update itself while paused", curate_after_merge: "Curate memory after a merge",
  curate_when_idle: "Curate memory when idle (the Maintenance button always runs)",
  sessions: "Agent sessions at once on this machine, across its projects",
  retro_run_credit_limit: "Retro: credit limit per run (credits)",
  replay_run_credit_limit: "Spotter cases: credit limit per paid replay run (credits)",
  retro_after_change: "Retro after a Change ends (the Improvement button always runs)",
  retro_when_idle: "Retro over finished enrolled chats when idle",
  enrolled_chats: "Enrolled chats: workspace folders whose chats the Spotter and Retro may read, comma-separated; "
    + "none for no chats",
  update_check_hours_owlbear: "Hours between checks for a newer OwlBear (it also checks at launch)",
  update_check_hours_pds: "Hours between checks for a newer Porsche Design System (it also checks at launch)",
  update_check_hours_impeccable: "Hours between checks for a newer Impeccable (it also checks at launch)",
};

// The settings that sit alone in a row of their own.
export const PLAIN_NAMES = { sessions: "Agent sessions at once in one project", widths: "Screenshot widths",
  design_failures: "Design failures", curator_threshold: "Curator's confidence threshold (%)",
  guard_level: "Shell guard level", pr_labels: "Labels", pr_marker: "Marker line", github_account: "GitHub account",
  ...USER_NAMES };

// A row name that means little without the heading of its section, which the name then starts with.
const SECTION = { spotter: "Spotter", pr_labels: "Pull requests", pr_marker: "Pull requests" };

// A setting's name in three parts: the section, the row and, in the agents and rounds tables, the column; null where
// the page shows no row for it, undefined for a key the page knows nothing about.
function parts(key) {
  const [head, a, b] = key.split(".");
  const round = (f) => ROUNDS.find(([r]) => r === f);
  // no row: test preparations and data permissions (project-only, no editor yet), the round values of a role that runs
  // no challenge loop, and the Spotter's minutes and subagents (shown as n/a)
  if (["data", "preparations"].includes(key)) return null;
  if (head === "agents" && Object.hasOwn(AGENT_NAMES, a) && b) {
    if (COLUMN[b]) {
      return a === "spotter" && ["minutes", "subagents"].includes(b) ? null : ["", agentName(a), COLUMN[b]];
    }
    const loop = LOOPS.find(([o]) => o === a);
    if (b === WAIT[0]) return a === "shaper" ? ["", loop[1], WAIT[1]] : null;
    if (round(b)) return loop ? ["", loop[1], round(b)[1]] : null;
  } else if (head === "final_review" && round(a)) {
    return ["", LOOPS.find(([o]) => o === "final_review")[1], round(a)[1]];
  } else if (head === "spotter" && SPOTTER.some(([f]) => f === a)) {
    return [SECTION.spotter, SPOTTER.find(([f]) => f === a)[1], ""];
  } else if (head === "memory" && [...RATINGS, ...RECALLS, ...PURGE].some(([f]) => f === a)) {
    return ["", [...RATINGS, ...RECALLS, ...PURGE].find(([f]) => f === a)[1], ""];
  } else if (head === "prefs" && PREF_NAMES[a]) {
    return ["", PREF_NAMES[a], ""];
  } else if (head === "machine" && MACHINE_LABELS[a]) {
    return ["", MACHINE_LABELS[a], ""];
  } else if (PLAIN_NAMES[key]) {
    return [SECTION[key] ?? "", PLAIN_NAMES[key], ""];
  }
  return undefined;
}

// A key of a setting in force that the page knows nothing about is a defect, not a name to guess.
function known(key) {
  const found = parts(key);
  if (found === undefined) throw new Error(`No Settings name is known for the setting "${key}"`);
  return found;
}

// Whether the page knows the setting at all: a change notice kept from an older version can name one since retired.
export function isKnown(key) {
  return parts(key) !== undefined;
}

// Whether the page shows a row, or a cell of one, that sets *key*.
export function hasRow(key) {
  return known(key) !== null;
}

// The words the owner finds on the page for *key*: "Spotter · On or off", "planner · Model", "Final review · Rounds
// at most". A setting with no row is named as it is written.
export function nameOf(key) {
  const found = known(key);
  return found ? found.filter(Boolean).join(" · ") : key;
}
