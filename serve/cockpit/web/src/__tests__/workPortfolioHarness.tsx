import { PorscheDesignSystemProvider, PToast } from "@porsche-design-system/components-react";
import { fireEvent, render, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, expect, vi } from "vitest";
import type {
  AbandonedChangeRecord,
  ChangeGroupView,
  ChangePauseUnavailableReason,
  CompletedChangeRecord,
  DeliveryHealthResponse,
  DeliveryProgress,
  DeliveryReadiness,
  DeliverySituation,
  DeliveryUnavailableChangeResponse,
  DesignWorkDetailResponse,
  PortfolioChangeLifecycleStatus,
  PublicationChecksObservationResponse,
  WorkItemAvailableDetailResponse,
  WorkItemCardView,
  WorkItemDetailResponse,
  WorkItemPortfolioResponse,
  WorkItemPublicationReconciliationResponse,
} from "../api/workItems";
import { completedChangeRecordId } from "../api/workItems";
import WorkPortfolioPage from "../pages/WorkPortfolioPage";

export interface WorkPortfolioState {
  currentPortfolio: WorkItemPortfolioResponse;
  currentDetail: WorkItemAvailableDetailResponse;
  currentUnavailableDetail: WorkItemDetailResponse | null;
  currentDesignWork: DesignWorkDetailResponse;
  portfolioAfterPublication: WorkItemPortfolioResponse | null;
  portfolioFailure: boolean;
  detailFailure: boolean;
  pendingDetailItemKey: string | null;
  pendingDetailRelease: (() => void) | null;
  pendingMutationPath: string | null;
  pendingMutationRelease: (() => void) | null;
  pendingPublicationChecksObservation: boolean;
  pendingPublicationChecksRelease: (() => void) | null;
  moveBackwardUpdatesDetailStage: WorkItemCardView["stage"];
  moveBackwardFailure: boolean;
  mutationFailurePath: string | null;
  releaseStuckWorkerActive: "write" | "processes" | "unobservable" | null;
  designFailure: boolean;
  acceptanceObservationFailure: boolean;
  publicationChecksFailure: boolean;
  publicationChecksResponse: PublicationChecksObservationResponse;
  supersedeFailuresRemaining: number;
  completedRecords: CompletedChangeRecord[];
  completedDetailRecord: CompletedChangeRecord | null;
  completedDetailMismatch: CompletedChangeRecord | null;
  completedHistoryNextCursor: string | null;
  completedHistoryPageRecords: CompletedChangeRecord[];
  completedHistoryPageFailuresRemaining: number;
  completedDetailFailuresRemaining: number;
  completedDetailNotFound: boolean;
  completedHistoryFailuresRemaining: number;
  completedHistorySearchPending: boolean;
  completedHistorySearchFailuresRemaining: number;
  completedHistorySearchRecords: CompletedChangeRecord[];
  completedHistorySearchNextCursor: string | null;
  completedHistorySearchPageRecords: CompletedChangeRecord[];
  completedHistorySearchRelease: (() => void) | null;
  publicationReconciliationResult: WorkItemPublicationReconciliationResponse;
  requests: Array<{ url: string; method: string; body: unknown }>;
}

export const fixtureState = {} as WorkPortfolioState;

export function requirePresent<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) {
    throw new Error("Expected value to be present");
  }
  return value;
}

export function card(overrides: Partial<WorkItemCardView> = {}): WorkItemCardView {
  return {
    item_key: "outcome:OUT-001",
    work_item_id: "OUT-001",
    change_id: "change-alpha",
    scope: "outcome",
    title: "Delivery foundation",
    stage: "implementation",
    needs: "none",
    needs_headline: null,
    next_actor: "agent",
    next_step: "Work in progress",
    activity: {
      state: "working",
      worker_role: "builder",
      started_at: "2026-08-08T10:00:00Z",
      task_id: "TASK-001",
    },
    progress: {
      kind: "tasks",
      label: "1 of 2 Delivery tasks reviewed",
      done: 1,
      total: 2,
    },
    action: { kind: "none", label: null, command: null },
    ...overrides,
  };
}

export function group(overrides: Partial<ChangeGroupView> = {}): ChangeGroupView {
  return {
    change_id: "change-alpha",
    title: "Portfolio redesign",
    snapshot_version: "a".repeat(64),
    lifecycle: "in-delivery",
    outcome_total: 2,
    outcome_completed: 0,
    items: [
      card(),
      card({
        item_key: "outcome:OUT-002",
        work_item_id: "OUT-002",
        title: "User controls",
        stage: "planning",
        needs: "you",
        needs_headline: "Decision required",
        next_actor: "you",
        next_step: "Decision required",
        activity: {
          state: "idle",
          worker_role: null,
          started_at: null,
          task_id: null,
        },
        progress: {
          kind: "plan",
          label: "Task plan not published",
          done: null,
          total: null,
        },
        action: {
          kind: "answer-request",
          label: "Answer request",
          command: null,
        },
      }),
    ],
    ...overrides,
  };
}

export function changeStatus(
  changeId: string,
  overrides: Partial<PortfolioChangeLifecycleStatus> = {},
): PortfolioChangeLifecycleStatus {
  return {
    change_id: changeId,
    admission: "admitted",
    stage: "building",
    actionable_runtime: true,
    diagnostic_code: null,
    diagnostic_detail: null,
    ...overrides,
  };
}

export function situation(value: DeliverySituation, overrides: Partial<DeliveryProgress> = {}): DeliveryProgress {
  return { situation: value, headline: `Headline for ${value}.`, waiting_on: "none", ...overrides };
}

export function readiness(overrides: Partial<DeliveryReadiness> = {}): DeliveryReadiness {
  return {
    status: "waiting",
    operation: null,
    executable: false,
    next_actor: "agent",
    reason_code: "task-incomplete",
    checks_state: "not-run",
    basis: {
      contract_digest: "c".repeat(64),
      frontier_digest: "d".repeat(64),
      source_head: null,
      target_head: null,
      continuation_id: null,
      candidate_head: "1".repeat(40),
      reviewed_head: "2".repeat(40),
      workspace_fingerprint: null,
      diagnostic_sequence: 0,
    },
    action: null,
    last_attempt: null,
    ...overrides,
  };
}

export function unavailableChange(changeId: string, title: string | null = null): DeliveryUnavailableChangeResponse {
  return {
    kind: "unavailable",
    change_id: changeId,
    title,
    diagnostics: ["runtime-unavailable"],
    coordination_status: null,
    readiness: readiness({
      status: "unavailable",
      next_actor: "none",
      reason_code: "runtime-unavailable",
      checks_state: "unknown",
      basis: {
        contract_digest: "c".repeat(64),
        frontier_digest: null,
        source_head: null,
        target_head: null,
        continuation_id: null,
        candidate_head: null,
        reviewed_head: null,
        workspace_fingerprint: null,
        diagnostic_sequence: null,
      },
      progress: situation("needs-attention", {
        headline: "Delivery cannot read this Change's state; diagnose it before continuing.",
        waiting_on: "you",
      }),
    }),
  };
}

export function portfolio(
  groups: ChangeGroupView[] = [group()],
  health: DeliveryHealthResponse = { status: "healthy", diagnostics: [] },
): WorkItemPortfolioResponse {
  const items = groups.flatMap((item) => item.items);
  const reference = (item: WorkItemCardView) => ({
    change_id: item.change_id,
    item_key: item.item_key,
    scope: item.scope === "change-publication" ? ("publication" as const) : ("outcome" as const),
  });
  const claimed = items.filter((item) => item.activity.state === "working").map(reference);
  const queued = items.filter((item) => item.activity.state === "ready").map(reference);
  const interventions = items.filter((item) => item.needs === "you").map(reference);
  const dependencyWaits = items.filter((item) => item.needs === "dependency").map(reference);
  const guidance: WorkItemPortfolioResponse["operating"]["guidance"] = [];
  if (interventions.length > 0)
    guidance.push({
      kind: "intervene",
      change_ids: [...new Set(interventions.map((item) => item.change_id))],
      work_count: interventions.length,
    });
  if (claimed.length > 0)
    guidance.push({
      kind: "work-underway",
      change_ids: [...new Set(claimed.map((item) => item.change_id))],
      work_count: claimed.length,
    });
  else if (queued.length > 0)
    guidance.push({
      kind: "start-orchestration",
      change_ids: [...new Set(queued.map((item) => item.change_id))],
      work_count: queued.length,
    });
  else if (dependencyWaits.length > 0)
    guidance.push({
      kind: "wait",
      change_ids: [...new Set(dependencyWaits.map((item) => item.change_id))],
      work_count: dependencyWaits.length,
    });
  if (groups.length === 0) guidance.push({ kind: "create-change", change_ids: [], work_count: 0 });
  return {
    groups,
    totals: {
      total: items.length,
      complete: items.filter((item) => item.stage === "completed" && item.scope === "outcome").length,
      needs: {
        you: items.filter((item) => item.needs === "you").length,
        dependency: items.filter((item) => item.needs === "dependency").length,
        none: items.filter((item) => item.needs === "none").length,
      },
      activity: {
        idle: items.filter((item) => item.activity.state === "idle").length,
        ready: items.filter((item) => item.activity.state === "ready").length,
        working: items.filter((item) => item.activity.state === "working").length,
      },
    },
    operating: {
      unfinished_change_count: groups.length,
      completed_change_count: 0,
      statuses: groups.map((item) => changeStatus(item.change_id)),
      draft_design_change_ids: [],
      design_required_change_ids: [],
      claimed,
      queued_for_orchestration: queued,
      interventions,
      dependency_waits: dependencyWaits,
      guidance,
    },
    health,
  };
}

export function withUnadmittedDesign(
  data: WorkItemPortfolioResponse,
  changeId = "design-draft",
): WorkItemPortfolioResponse {
  return {
    ...data,
    operating: {
      ...data.operating,
      statuses: [
        ...data.operating.statuses,
        changeStatus(changeId, {
          admission: "unadmitted",
          stage: "design",
          actionable_runtime: false,
        }),
      ],
      draft_design_change_ids: [changeId],
    },
  };
}

export function detail(
  overrides: Partial<WorkItemAvailableDetailResponse["item"]> = {},
): WorkItemAvailableDetailResponse {
  const publication = overrides.publication && {
    publication_generations: [],
    ...overrides.publication,
  };
  return {
    item: {
      snapshot_version: "a".repeat(64),
      change_title: "Portfolio redesign",
      card: card(),
      promise: "Make Delivery supervision coherent.",
      acceptance: ["The current state is unambiguous."],
      commitments: [
        {
          commitment_id: "COM-001",
          commitment_class: "protected-request",
          provenance: "user request",
          statement: "Keep user attention explicit.",
        },
      ],
      dependencies: [],
      tasks: [
        {
          task_id: "TASK-001",
          title: "Build the projection",
          result: "A reviewed grouped snapshot.",
          status: "reviewed",
          completed_commit: "1".repeat(40),
          acceptance_observations: ["Projection is observable."],
          proof_boundaries: ["Focused component test"],
        },
      ],
      block: null,
      requests: [],
      active_claim: null,
      held_finalizer: null,
      return_context: null,
      operator_moves: [],
      recovery_attention: null,
      retry_diagnostic: null,
      abandon_available: true,
      ...overrides,
      publication: publication || null,
    },
  };
}

export type PublicationView = NonNullable<WorkItemAvailableDetailResponse["item"]["publication"]>;

export function publicationForChecks(
  phase: "pull-request-draft" | "awaiting-merge" | "ready-for-finalization",
  publishedHead = "1".repeat(40),
): PublicationView {
  return {
    phase,
    finalization_id: "f".repeat(64),
    finalized_head: publishedHead,
    published_head: publishedHead,
    pending_checkpoint_head: null,
    pending_checkpoint_triggers: [],
    invalidated_expected_head: null,
    invalidated_observed_head: null,
    repository: null,
    pull_request_number: null,
    pull_request_head: null,
    accepted_merge_commit: null,
    merged_at: null,
    publication_generations: [
      {
        repository: "owlbear/example",
        number: 42,
        node_id: "PR_example_42",
        head_sha: publishedHead,
      },
    ],
  };
}

export function publicationCardForChecks(overrides: Partial<WorkItemCardView> = {}): WorkItemCardView {
  return card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "agent",
    next_step: "Review publication checks",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Pull request is draft",
      done: null,
      total: null,
    },
    action: { kind: "none", label: null, command: null },
    ...overrides,
  });
}

export const completed: CompletedChangeRecord = {
  schema_version: 2,
  record_kind: "completion-receipt",
  change_id: "change-alpha",
  completion_id: "b".repeat(64),
  finalization_receipt_id: "c".repeat(64),
  finalized_change_head: "d".repeat(40),
  repository_identity: "owlbear/example",
  pull_request_identity: { number: 41, node_id: "PR_example_41" },
  accepted_target_ref: "main",
  accepted_merge_commit: "e".repeat(40),
  merged_at: "2026-08-11T12:00:00Z",
  acceptance_observation_id: "f".repeat(64),
  check_observation_ids: ["0".repeat(64)],
  review_receipt_ids: ["1".repeat(64)],
  acceptance_evidence_digest: "2".repeat(64),
  completed_at: "2026-08-11T13:00:00Z",
  title: "Portfolio redesign",
  semantic_summary: "Shipped the grouped Delivery workspace.",
  outcome_titles: ["Ship the grouped Delivery workspace"],
  outcome_promises: ["Give operators a clear view of grouped Delivery work."],
};

export const receiptCompleted: CompletedChangeRecord = {
  schema_version: 2,
  record_kind: "completion-receipt",
  change_id: "change-receipt",
  completion_id: "1".repeat(64),
  title: "Receipt-backed delivery",
  semantic_summary: "Accepted through a merged pull request.",
  outcome_titles: ["Accept the merged Delivery change"],
  outcome_promises: ["Record the accepted change with durable evidence."],
  finalization_receipt_id: "2".repeat(64),
  finalized_change_head: "3".repeat(40),
  repository_identity: "owlbear/example",
  pull_request_identity: { number: 42, node_id: "PR_example_42" },
  accepted_target_ref: "main",
  accepted_merge_commit: "4".repeat(40),
  merged_at: "2026-08-11T12:00:00Z",
  acceptance_observation_id: "5".repeat(64),
  check_observation_ids: ["6".repeat(64)],
  review_receipt_ids: ["7".repeat(64)],
  acceptance_evidence_digest: "8".repeat(64),
  completed_at: "2026-08-11T13:00:00Z",
};

export function abandonedRecord(overrides: Partial<AbandonedChangeRecord> = {}): AbandonedChangeRecord {
  return {
    schema_version: 1,
    record_kind: "abandoned-change",
    change_id: "change-alpha",
    abandonment_id: "9".repeat(64),
    title: "Abandoned portfolio change",
    semantic_summary: "Stopped before completion with its terminal evidence retained.",
    outcome_titles: ["Preserve the abandoned Change record"],
    outcome_promises: ["Keep the abandoned Change recoverable for cleanup."],
    prior_stage: "building",
    reason: "User stopped the Change",
    abandoned_at: "2026-08-11T14:00:00Z",
    cleanup_available: true,
    target_sync_conflict: false,
    target_sync_conflict_target_head: null,
    target_sync_conflict_operation_id: null,
    ...overrides,
  };
}

export function response(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function requestUrl(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
}

export function installFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = init?.method ?? "GET";
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : null;
      fixtureState.requests.push({ url, method, body });

      if (method === "GET" && url === "/api/work-items") {
        return fixtureState.portfolioFailure
          ? response({ detail: "Temporary polling failure" }, 503)
          : response(fixtureState.currentPortfolio);
      }
      if (method === "GET" && url.startsWith("/api/changes/change-alpha/work-items/")) {
        if (fixtureState.pendingDetailItemKey !== null && url.endsWith(fixtureState.pendingDetailItemKey)) {
          await new Promise<void>((resolve) => {
            fixtureState.pendingDetailRelease = resolve;
          });
        }
        return fixtureState.detailFailure
          ? response({ detail: "Delivery runtime is absent: change-alpha" }, 409)
          : response(fixtureState.currentUnavailableDetail ?? fixtureState.currentDetail);
      }
      if (method === "GET" && url === "/api/design-work/design-draft") {
        return fixtureState.designFailure
          ? response({ detail: "Design source temporarily unavailable" }, 503)
          : response(fixtureState.currentDesignWork);
      }
      if (method === "GET" && url === "/api/work-items/completed") {
        if (fixtureState.completedHistoryFailuresRemaining > 0) {
          fixtureState.completedHistoryFailuresRemaining -= 1;
          return response({ detail: "Completed history unavailable" }, 503);
        }
        return response({
          records: fixtureState.completedRecords,
          total_count: fixtureState.completedRecords.length + fixtureState.completedHistoryPageRecords.length,
          next_cursor: fixtureState.completedHistoryNextCursor,
        });
      }
      if (method === "GET" && url.startsWith("/api/work-items/completed?cursor=")) {
        if (fixtureState.completedHistoryPageFailuresRemaining > 0) {
          fixtureState.completedHistoryPageFailuresRemaining -= 1;
          return response({ detail: "Next completed history page unavailable" }, 503);
        }
        return response({
          records: fixtureState.completedHistoryPageRecords,
          total_count: fixtureState.completedRecords.length + fixtureState.completedHistoryPageRecords.length,
          next_cursor: null,
        });
      }
      if (method === "GET" && url.startsWith("/api/work-items/completed/search?")) {
        if (fixtureState.completedHistorySearchPending) {
          await new Promise<void>((resolve) => {
            fixtureState.completedHistorySearchRelease = resolve;
          });
        }
        if (fixtureState.completedHistorySearchFailuresRemaining > 0) {
          fixtureState.completedHistorySearchFailuresRemaining -= 1;
          return response({ detail: "Completed history search unavailable" }, 503);
        }
        const pageRequest = url.includes("cursor=");
        return response({
          records: pageRequest
            ? fixtureState.completedHistorySearchPageRecords
            : fixtureState.completedHistorySearchRecords,
          total_count:
            fixtureState.completedHistorySearchRecords.length + fixtureState.completedHistorySearchPageRecords.length,
          next_cursor: pageRequest ? null : fixtureState.completedHistorySearchNextCursor,
        });
      }
      if (method === "GET" && url.startsWith("/api/work-items/completed/")) {
        const selected =
          fixtureState.completedDetailMismatch ??
          (fixtureState.completedDetailRecord &&
          url.includes(completedChangeRecordId(fixtureState.completedDetailRecord))
            ? fixtureState.completedDetailRecord
            : fixtureState.completedRecords.find((record) => url.includes(completedChangeRecordId(record))));
        if (fixtureState.completedDetailNotFound) return response({ detail: "Completion detail was removed" }, 404);
        if (fixtureState.completedDetailFailuresRemaining > 0) {
          fixtureState.completedDetailFailuresRemaining -= 1;
          return response({ detail: "Completion detail temporarily unavailable" }, 503);
        }
        return selected ? response(selected) : response({ detail: "Not found" }, 404);
      }

      if (method === "POST" && url.endsWith("/publication/checks/observe")) {
        if (fixtureState.pendingPublicationChecksObservation) {
          await new Promise<void>((resolve) => {
            fixtureState.pendingPublicationChecksRelease = resolve;
          });
        }
        if (fixtureState.publicationChecksFailure) {
          return response(
            {
              detail: {
                code: "ERR_DELIVERY_PROVIDER_UNAVAILABLE",
                detail: "GitHub is unavailable",
                authority: "delivery",
                retry_safe: true,
              },
            },
            502,
          );
        }
        return response(fixtureState.publicationChecksResponse);
      }
      if (method === "POST" && fixtureState.mutationFailurePath && url.endsWith(fixtureState.mutationFailurePath)) {
        return response(
          {
            detail: {
              code: "ERR_DELIVERY_CONTROL_CONFLICT",
              detail: "The Delivery operation was rejected while the confirmation was open.",
              authority: "delivery",
              retry_safe: true,
            },
          },
          409,
        );
      }

      if (method === "POST" && url.includes("/requests/")) {
        const requestId = url.split("/requests/")[1].split("/")[0];
        fixtureState.currentDetail = detail({
          ...fixtureState.currentDetail.item,
          requests: fixtureState.currentDetail.item.requests.map((item) =>
            item.request_id === requestId
              ? {
                  ...item,
                  resolution: body as {
                    selected_option_id: string | null;
                    response_text: string | null;
                  },
                }
              : item,
          ),
        });
        return response({});
      }
      if (method === "POST" && url.includes("/blocks/")) {
        fixtureState.currentDetail = detail({ ...fixtureState.currentDetail.item, block: null });
        return response({});
      }
      if (method === "POST" && url.endsWith("/workers/release-stuck")) {
        if (fixtureState.releaseStuckWorkerActive === "write") {
          return response(
            {
              code: "ERR_DELIVERY_WORKER_ACTIVE",
              detail:
                "Custody, files and retry accounting are unchanged. The worker's worktree changed recently, so the " +
                "worker may still be active. Retry at or after 2026-10-02T12:00:30Z.",
              authority: "delivery",
              retry_safe: true,
              retry_after: "2026-10-02T12:00:30Z",
            },
            409,
          );
        }
        if (fixtureState.releaseStuckWorkerActive === "processes") {
          return response(
            {
              code: "ERR_DELIVERY_WORKER_ACTIVE",
              detail:
                "Custody, files and retry accounting are unchanged. 1 process (node) is still active in the " +
                "worker's worktree, so the worker may still be running. Retry after they exit.",
              authority: "delivery",
              retry_safe: true,
            },
            409,
          );
        }
        if (fixtureState.releaseStuckWorkerActive === "unobservable") {
          return response(
            {
              code: "ERR_DELIVERY_WORKER_ACTIVE",
              detail:
                "Custody, files and retry accounting are unchanged. The worker's worktree or its processes could " +
                "not be observed safely, so the worker may still be active.",
              authority: "delivery",
              retry_safe: true,
            },
            409,
          );
        }
        fixtureState.currentDetail = detail({
          ...fixtureState.currentDetail.item,
          active_claim: null,
          held_finalizer: null,
        });
        return response({});
      }
      if (method === "POST" && url.endsWith("/move-backward/preview")) {
        return response({
          outcome_id: "OUT-001",
          target: (body as { target: string }).target,
          snapshot_version: "a".repeat(64),
          invalidated_outcome_ids: ["OUT-001", "OUT-002"],
        });
      }
      if (method === "POST" && url.endsWith("/move-backward")) {
        if (fixtureState.moveBackwardFailure) {
          return response(
            {
              detail: {
                code: "ERR_DELIVERY_ADMINISTRATIVE_MOVE",
                detail: "The Delivery frontier changed before the move was applied.",
                authority: "delivery",
                retry_safe: true,
              },
            },
            409,
          );
        }
        if (fixtureState.moveBackwardUpdatesDetailStage) {
          fixtureState.currentDetail = detail({
            ...fixtureState.currentDetail.item,
            card: {
              ...fixtureState.currentDetail.item.card,
              stage: fixtureState.moveBackwardUpdatesDetailStage,
            },
          });
        }
        return response({ invalidated_outcome_ids: ["OUT-002"], move: {} });
      }
      if (
        method === "POST" &&
        (url.endsWith("/target/sync") ||
          url.endsWith("/target/conflict/abort") ||
          url.endsWith("/target/conflict/resolve") ||
          url.endsWith("/publication/reconcile") ||
          url.endsWith("/publication/ready") ||
          url.endsWith("/publication/supersede") ||
          url.endsWith("/acceptance/observe") ||
          url.endsWith("/attention/resolve") ||
          url.endsWith("/defer") ||
          url.endsWith("/resume") ||
          url.endsWith("/abandon") ||
          url.endsWith("/worktree/cleanup/abandoned") ||
          url.endsWith("/worktree/cleanup/abandoned/target-sync-discard") ||
          url.endsWith("/worktree/cleanup/completed") ||
          url.endsWith("/worktree/recover"))
      ) {
        if (fixtureState.pendingMutationPath && url.endsWith(fixtureState.pendingMutationPath)) {
          await new Promise<void>((resolve) => {
            fixtureState.pendingMutationRelease = resolve;
          });
        }
        if (url.endsWith("/publication/reconcile")) return response(fixtureState.publicationReconciliationResult);
        if (url.endsWith("/acceptance/observe") && fixtureState.acceptanceObservationFailure) {
          return response(
            {
              detail: {
                code: "ERR_DELIVERY_ACCEPTANCE_WAITING",
                detail: "The pull request is still open and unmerged.",
                authority: "delivery",
                retry_safe: true,
              },
            },
            409,
          );
        }
        if (fixtureState.portfolioAfterPublication)
          fixtureState.currentPortfolio = fixtureState.portfolioAfterPublication;
        if (url.endsWith("/publication/supersede")) {
          if (fixtureState.supersedeFailuresRemaining > 0) {
            fixtureState.supersedeFailuresRemaining -= 1;
            return response(
              {
                detail: {
                  code: "ERR_PROVIDER_UNAVAILABLE",
                  detail: "Provider unavailable",
                  authority: "delivery",
                  retry_safe: true,
                },
              },
              409,
            );
          }
          return response({
            schema_version: 1,
            receipt_id: "d".repeat(64),
            operation_id: (body as { operation_id: string }).operation_id,
            change_id: "change-alpha",
            predecessor_publication_id: "e".repeat(64),
            successor_publication_id: "f".repeat(64),
          });
        }
        if (url.endsWith("/target/sync")) {
          return response({
            schema_version: 1,
            receipt_id: "a".repeat(64),
            operation_id: "cockpit-target-sync-test",
            change_id: "change-alpha",
            target_branch: "main",
            expected_target: "1".repeat(40),
            target_head: "1".repeat(40),
            change_head_before: "2".repeat(40),
            merged_head: "3".repeat(40),
            merge_commit: true,
            review_required: false,
          });
        }
        if (url.endsWith("/target/conflict/abort")) {
          return response({
            schema_version: 1,
            receipt_id: "b".repeat(64),
            operation_id: "cockpit-target-sync-conflict",
            change_id: "change-alpha",
            target_head: "4".repeat(40),
            restored_head: "5".repeat(40),
          });
        }
        if (url.endsWith("/target/conflict/resolve")) {
          return response({
            schema_version: 1,
            receipt_id: "c".repeat(64),
            operation_id: "cockpit-target-sync-conflict",
            change_id: "change-alpha",
            target_branch: "main",
            expected_target: "4".repeat(40),
            target_head: "4".repeat(40),
            change_head_before: "5".repeat(40),
            merged_head: "6".repeat(40),
            merge_commit: true,
            review_required: true,
          });
        }
        if (url.endsWith("/worktree/cleanup/abandoned/target-sync-discard")) {
          return response({
            cleanup_id: "d".repeat(64),
            change_id: "change-alpha",
            branch: "owlbear/change/change-alpha",
            worktree_path: ".owlbear/delivery/worktrees/change-alpha",
            branch_head: "5".repeat(40),
          });
        }
        return response({});
      }
      return response({ detail: "Not found" }, 404);
    }),
  );
}

export function selectValue(element: Element, value: string) {
  const host = element as HTMLElement & { value: string };
  host.value = value;
  fireEvent(host, new CustomEvent("change", { detail: { value }, bubbles: true }));
}

export function inputValue(element: Element, value: string) {
  const host = element as HTMLElement & { value: string };
  host.value = value;
  fireEvent(host, new CustomEvent("input", { detail: { value }, bubbles: true }));
}

export function namedPdsHost(
  container: HTMLElement,
  tagName: "p-input-text" | "p-select",
  name: string,
): Element | null {
  return (
    Array.from(container.querySelectorAll<HTMLElement & { name?: string }>(tagName)).find(
      (element) => element.name === name || element.getAttribute("name") === name,
    ) ?? null
  );
}

export function renderPage(path = "/delivery") {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[path]}>
        <LocationProbe />
        <WorkPortfolioPage />
      </MemoryRouter>
      <PToast />
    </PorscheDesignSystemProvider>,
  );
}

export function LocationProbe() {
  const location = useLocation();
  return <output data-testid="test-location">{location.pathname}</output>;
}

export function installWorkPortfolioHarness() {
  beforeEach(() => {
    fixtureState.currentPortfolio = portfolio();
    fixtureState.currentDetail = detail();
    fixtureState.currentUnavailableDetail = null;
    fixtureState.currentDesignWork = {
      change_id: "design-draft",
      package_id: "d".repeat(64),
      intent_markdown: "# Design Draft\n\nShape a coherent operator workflow.",
      design_markdown: "# Architecture\n\nKeep authority explicit.",
    };
    fixtureState.portfolioAfterPublication = null;
    fixtureState.portfolioFailure = false;
    fixtureState.detailFailure = false;
    fixtureState.pendingDetailItemKey = null;
    fixtureState.pendingDetailRelease = null;
    fixtureState.pendingMutationPath = null;
    fixtureState.pendingMutationRelease = null;
    fixtureState.pendingPublicationChecksObservation = false;
    fixtureState.pendingPublicationChecksRelease = null;
    fixtureState.moveBackwardUpdatesDetailStage = null;
    fixtureState.moveBackwardFailure = false;
    fixtureState.mutationFailurePath = null;
    fixtureState.releaseStuckWorkerActive = null;
    fixtureState.designFailure = false;
    fixtureState.acceptanceObservationFailure = false;
    fixtureState.publicationChecksFailure = false;
    fixtureState.publicationReconciliationResult = {
      change_id: "change-alpha",
      attempted_head: null,
      reconciled: true,
      error_code: null,
      error_detail: null,
      pending_checkpoint_attempt_count: 0,
      pending_checkpoint_last_attempted_at: null,
      pending_checkpoint_error_code: null,
      pending_checkpoint_error_detail: null,
    };
    fixtureState.publicationChecksResponse = {
      schema_version: 1,
      observation_id: "a".repeat(64),
      change_id: "change-alpha",
      repository: "owlbear/example",
      pull_request_number: 42,
      exact_commit: "1".repeat(40),
      observed_at: "2026-08-11T16:00:00Z",
      rollup_state: "failure",
      checks: [
        {
          check_id: "required-failure",
          kind: "check_run",
          name: "Unit tests",
          status: "completed",
          conclusion: "failure",
          required: true,
          blocking_state: "blocking",
        },
        {
          check_id: "required-pending",
          kind: "check_run",
          name: "Integration tests",
          status: "queued",
          conclusion: null,
          required: true,
          blocking_state: "required-pending",
        },
        {
          check_id: "optional-failure",
          kind: "check_run",
          name: "Optional lint",
          status: "completed",
          conclusion: "failure",
          required: false,
          blocking_state: "not-blocking",
        },
      ],
      required_failure_count: 1,
      truncated_count: 0,
    };
    fixtureState.supersedeFailuresRemaining = 0;
    fixtureState.completedRecords = [completed];
    fixtureState.completedDetailRecord = null;
    fixtureState.completedDetailMismatch = null;
    fixtureState.completedHistoryNextCursor = null;
    fixtureState.completedHistoryPageRecords = [];
    fixtureState.completedHistoryPageFailuresRemaining = 0;
    fixtureState.completedDetailFailuresRemaining = 0;
    fixtureState.completedDetailNotFound = false;
    fixtureState.completedHistoryFailuresRemaining = 0;
    fixtureState.completedHistorySearchPending = false;
    fixtureState.completedHistorySearchFailuresRemaining = 0;
    fixtureState.completedHistorySearchRecords = [];
    fixtureState.completedHistorySearchNextCursor = null;
    fixtureState.completedHistorySearchPageRecords = [];
    fixtureState.completedHistorySearchRelease = null;
    fixtureState.requests = [];
    installFetch();
  });
}

export const runningBuilderClaim = {
  attempt_id: "attempt-one",
  claim_id: "claim-one",
  owner_id: "host-one",
  process_id: "session-one",
  continuation: false,
  started_at: "2026-08-08T10:00:00Z",
  worker_role: "builder" as const,
  task_id: "TASK-001",
};

export const CONTINUATION_PROMPT =
  "/continue-change change-alpha reread get_change and pass its readiness basis unchanged to acquire_change_action; " +
  "declare only capabilities this session can dispatch and execute only the acquired operation.";

export function continuationCard(overrides: Partial<WorkItemCardView> = {}): WorkItemCardView {
  return card({
    next_step: "Run the continuation prompt in Copilot Chat",
    activity: { state: "ready", worker_role: null, started_at: null, task_id: null },
    action: { kind: "start-orchestration", label: "Copy continuation prompt", command: null },
    readiness: readiness({
      status: "ready",
      operation: "start-orchestration",
      executable: true,
      reason_code: "ready",
      action: { kind: "start-orchestration", label: "Copy continuation prompt", command: null },
      prompt: CONTINUATION_PROMPT,
      progress: situation("ready-for-next-step", { headline: "Run the prompt in Copilot Chat to start the step." }),
    }),
    ...overrides,
  });
}

export function heldCard(progress: DeliveryReadiness["progress"] = null): WorkItemCardView {
  return card({
    next_step: "Claimed by Builder",
    readiness: readiness({ status: "running", reason_code: "active-custody", progress }),
  });
}

export const PAUSE_REQUESTED = {
  pause_available: false,
  pause_unavailable_reason: "pause-requested",
  pause_requested: true,
} as const;
export const PAUSE_AVAILABLE = { pause_available: true, pause_unavailable_reason: null } as const;

export const PAUSE_REFUSALS: [ChangePauseUnavailableReason, string][] = [
  ["finalizer-custody", "A Finalizer attempt holds this Change."],
  ["step-in-progress", "A step is in progress; Pause is available when it returns."],
  ["recovery-required", "An interrupted step must be recovered first."],
  ["state-unavailable", "Delivery cannot confirm this Change is idle, so Pause is unavailable."],
];

export function quietCard(status: DeliveryReadiness["status"], reason: DeliveryReadiness["reason_code"]) {
  return card({
    activity: { state: "idle", worker_role: null, started_at: null, task_id: null },
    readiness: readiness({ status, reason_code: reason }),
  });
}

export async function expectPauseRefused(control: HTMLElement, message: string) {
  const pause = within(control).getByText("Pause") as HTMLElement & { disabled: boolean };
  expect(pause.disabled).toBe(true);
  expect(control).toHaveTextContent(message);
  fireEvent.click(pause);
  await waitFor(() => expect(within(control).queryByText("Confirm pause")).not.toBeInTheDocument());
  expect(fixtureState.requests.some((request) => request.url.endsWith("/defer"))).toBe(false);
}

export function expectPauseOffered(control: HTMLElement) {
  const pause = within(control).getByText("Pause") as HTMLElement & { disabled: boolean };
  expect(pause.disabled).toBe(false);
  for (const [, message] of PAUSE_REFUSALS) expect(control).not.toHaveTextContent(message);
}
