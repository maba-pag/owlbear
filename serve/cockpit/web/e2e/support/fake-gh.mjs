// Fake `gh` for the assembled merge E2E: answers Delivery's fixed `gh api` calls from one JSON state file.
// Usage: gh api ... (from Delivery), or from tests `node fake-gh.mjs __merge <number>`, `__move-head <number> <sha>`
// and `__restore-target` (main back to the seeded base, so later fixtures keep their proof target).
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { appendFileSync, readFileSync, renameSync, writeFileSync } from "node:fs";

const statePath = process.env.OWLBEAR_FAKE_GH_STATE;
if (!statePath) {
  process.stderr.write("gh: OWLBEAR_FAKE_GH_STATE is not set\n");
  process.exit(1);
}

function load() {
  return JSON.parse(readFileSync(statePath, "utf8"));
}

function save(state) {
  writeFileSync(`${statePath}.tmp`, JSON.stringify(state, null, 2));
  renameSync(`${statePath}.tmp`, statePath);
}

function log(entry) {
  appendFileSync(`${statePath}.calls.jsonl`, `${JSON.stringify(entry)}\n`);
}

function fail(status, message) {
  process.stdout.write(JSON.stringify({ message }));
  process.stderr.write(`gh: ${message} (HTTP ${status})\n`);
  process.exit(1);
}

function reply(payload) {
  process.stdout.write(JSON.stringify(payload));
  process.exit(0);
}

function branchHead(state, ref) {
  return execFileSync("git", ["--git-dir", state.mirror, "rev-parse", `refs/heads/${ref}`], {
    encoding: "utf8",
  }).trim();
}

function headSha(state, pull) {
  return pull.merged ? pull.merged_head : (pull.head_override ?? branchHead(state, pull.head));
}

function restPull(state, pull) {
  const open = pull.state === "open";
  return {
    number: pull.number,
    node_id: pull.node_id,
    head: { ref: pull.head, sha: headSha(state, pull) },
    base: { ref: pull.base, sha: state.branches[pull.base] },
    title: pull.title,
    body: pull.body,
    draft: pull.draft,
    state: pull.state,
    merged: pull.merged,
    mergeable: open ? true : null,
    mergeable_state: open ? (pull.draft ? "draft" : "clean") : "unknown",
    merged_at: pull.merged_at ?? null,
    merged_by: pull.merged ? { login: "e2e-user" } : null,
  };
}

function merge(state, pull) {
  const head = headSha(state, pull);
  const parent = state.branches[pull.base];
  const sha = createHash("sha1").update(`merge:${pull.number}:${parent}:${head}`).digest("hex");
  Object.assign(pull, {
    merged: true,
    state: "closed",
    merged_head: head,
    merge_commit: sha,
    parents: [parent, head],
    merged_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  });
  state.branches[pull.base] = sha;
  return sha;
}

function pullByNumber(state, number) {
  const pull = state.pulls[String(number)];
  if (!pull) fail(404, "Not Found");
  return pull;
}

function graphql(state, request) {
  const { operationName: name, variables } = request;
  if (name === "MarkPullRequestReadyForReview" || name === "ConvertPullRequestToDraft") {
    const pull = Object.values(state.pulls).find((item) => item.node_id === variables.pullRequestId);
    if (!pull) fail(404, "Not Found");
    pull.draft = name === "ConvertPullRequestToDraft";
    save(state);
    const field = name[0].toLowerCase() + name.slice(1);
    return { data: { [field]: { pullRequest: { id: pull.node_id, isDraft: pull.draft } } } };
  }
  const pull = pullByNumber(state, variables.number);
  const head = headSha(state, pull);
  const repository = { nameWithOwner: state.repository };
  if (name === "ObservePublicationChecks") {
    const check = {
      __typename: "CheckRun",
      id: `CR_unit_${pull.number}_${head.slice(0, 8)}`,
      name: "unit",
      status: "COMPLETED",
      conclusion: "SUCCESS",
      startedAt: "2026-10-05T00:00:00Z",
      completedAt: "2026-10-05T00:01:00Z",
      detailsUrl: null,
      isRequired: true,
    };
    const rollup = {
      state: "SUCCESS",
      contexts: { totalCount: 1, pageInfo: { hasNextPage: false, endCursor: null }, nodes: [check] },
    };
    const commits = { nodes: [{ commit: { oid: head, statusCheckRollup: rollup } }] };
    return { data: { repository: { ...repository, pullRequest: { number: pull.number, headRefOid: head, commits } } } };
  }
  const merged = {
    number: pull.number,
    headRefOid: head,
    baseRefName: pull.base,
    merged: pull.merged,
    mergedAt: pull.merged_at ?? null,
  };
  if (name === "ReadMergedPullRequest") {
    return {
      data: { repository: { ...repository, pullRequest: { ...merged, mergeCommit: { oid: pull.merge_commit } } } },
    };
  }
  if (name === "ReadMergeCommit") {
    const parents = { totalCount: 2, nodes: pull.parents.map((oid) => ({ oid })) };
    const mergeCommit = pull.merged ? { oid: pull.merge_commit, parents } : null;
    return { data: { repository: { ...repository, pullRequest: { ...merged, mergeCommit } } } };
  }
  return fail(422, `unsupported GraphQL operation ${name}`);
}

function createPull(state, body) {
  const number = state.next_number;
  state.next_number += 1;
  const pull = {
    number,
    node_id: `PR_e2e_${number}`,
    head: body.head,
    base: body.base,
    title: body.title,
    body: body.body,
    draft: body.draft,
    state: "open",
    merged: false,
  };
  state.pulls[String(number)] = pull;
  save(state);
  return restPull(state, pull);
}

function rest(state, method, endpoint, body) {
  const [path, query = ""] = endpoint.split("?");
  const parts = path.split("/");
  const repository = `${decodeURIComponent(parts[1])}/${decodeURIComponent(parts[2])}`;
  if (parts[0] !== "repos" || repository !== state.repository) fail(404, "Not Found");
  const segments = parts.slice(3);
  if (segments.length === 0) {
    return {
      full_name: state.repository,
      default_branch: "main",
      allow_merge_commit: true,
      allow_squash_merge: true,
      allow_rebase_merge: true,
      permissions: { push: true },
    };
  }
  if (segments[0] === "branches") {
    return { name: segments[1], commit: { sha: state.branches[decodeURIComponent(segments[1])] } };
  }
  if (segments[0] === "rules") return [];
  if (segments[0] !== "pulls") fail(404, "Not Found");
  if (segments.length === 1 && method === "GET") {
    const filter = new URLSearchParams(query);
    const head = filter.get("head")?.split(":")[1];
    return Object.values(state.pulls)
      .filter((pull) => pull.head === head && pull.base === filter.get("base"))
      .map((pull) => ({ number: pull.number }));
  }
  if (segments.length === 1 && method === "POST") return createPull(state, body);
  const pull = pullByNumber(state, segments[1]);
  if (segments.length === 2 && method === "PATCH") {
    Object.assign(pull, { title: body.title, body: body.body });
    save(state);
  }
  if (segments.length === 2) return restPull(state, pull);
  if (segments[2] === "merge-async" && method === "PUT") {
    if (pull.merge_response === "unknown") fail(502, "Bad Gateway");
    if (body.sha !== headSha(state, pull) || pull.merged) fail(409, "Head branch was modified");
    const sha = merge(state, pull);
    save(state);
    return { status: "merged", details: { sha } };
  }
  return fail(404, "Not Found");
}

const args = process.argv.slice(2);
if (args[0] === "__merge" || args[0] === "__move-head") {
  const state = load();
  const pull = pullByNumber(state, args[1]);
  if (args[0] === "__merge") merge(state, pull);
  else pull.head_override = args[2];
  save(state);
  process.exit(0);
}
if (args[0] === "__restore-target") {
  const state = load();
  state.branches.main = state.seed_base;
  save(state);
  process.exit(0);
}
if (args[0] !== "api") fail(400, `unsupported gh command ${args[0]}`);
let method = "GET";
let input = null;
let endpoint = null;
for (let index = 1; index < args.length; index += 1) {
  if (args[index] === "--method") method = args[++index];
  else if (args[index] === "--header") index += 1;
  else if (args[index] === "--input") input = args[++index];
  else endpoint = args[index];
}
const body = input === null ? null : JSON.parse(readFileSync(input === "-" ? 0 : input, "utf8"));
const state = load();
const parts = endpoint.split("?")[0].split("/");
const graph = endpoint === "graphql";
const pullLabel = graph ? (body?.variables?.number ?? null) : parts[3] === "pulls" ? (parts[4] ?? null) : null;
log({
  method,
  endpoint,
  operation: graph ? body.operationName : null,
  pull: pullLabel,
  body: graph ? body.variables : body,
});
reply(graph ? graphql(state, body) : rest(state, method, endpoint, body));
