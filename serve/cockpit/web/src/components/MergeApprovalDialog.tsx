import { PButton, PHeading, PModal } from "@porsche-design-system/components-react";
import { useState } from "react";
import { type MergeOffer, WorkItemApiError } from "../api/workItems";

const STALE_OFFER = "ERR_DELIVERY_MERGE_OFFER_STALE";

interface MergeApprovalDialogProps {
  /** The current offer, or null when readiness offers no merge. */
  offer: MergeOffer | null;
  pendingAction: string | null;
  onApproveMerge: (offerId: string, submissionId: string) => Promise<Error | null>;
}

function OfferRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-contrast-medium">{label}</dt>
      <dd className="min-w-0 break-all font-mono text-xs">{value}</dd>
    </>
  );
}

/** Approve merge: the user confirms the exact offer shown; Delivery sends one head-fenced request (N05 D14). */
export default function MergeApprovalDialog({ offer, pendingAction, onApproveMerge }: MergeApprovalDialogProps) {
  // The open dialog keeps the offer under review; a retried approval repeats its submission identity.
  const [shown, setShown] = useState<{ offer: MergeOffer; submissionId: string } | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const close = () => {
    setShown(null);
    setError(null);
  };
  const stale = error instanceof WorkItemApiError && error.code === STALE_OFFER;
  const approve = async () => {
    if (!shown || stale) return;
    const failure = await onApproveMerge(shown.offer.offer_id, shown.submissionId);
    if (failure === null) close();
    else setError(failure);
  };
  const reviewed = shown?.offer;
  return (
    <>
      {offer ? (
        <PButton
          className="mt-static-sm"
          type="button"
          compact
          disabled={pendingAction !== null}
          onClick={() => {
            setError(null);
            setShown({ offer, submissionId: `cockpit-merge-${crypto.randomUUID()}` });
          }}
        >
          Approve merge
        </PButton>
      ) : null}
      {reviewed ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={close}
          aria={{ role: "alertdialog", "aria-label": "Approve merge" }}
        >
          <div
            className="grid w-[min(36rem,calc(100vw-2rem))] gap-static-md text-primary"
            onKeyDownCapture={(event) => {
              if (event.key !== "Escape") return;
              event.preventDefault();
              close();
            }}
          >
            <PHeading tag="h2" size="lg">
              Merge into {reviewed.base_branch}?
            </PHeading>
            <p className="text-sm">
              Delivery merges this pull request into <code>{reviewed.base_branch}</code> in GitHub with a merge commit
              at exactly the head below. Delivery cannot undo the merge.
            </p>
            <dl
              className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs text-sm"
              data-testid="merge-approval-offer"
            >
              <OfferRow label="Pull request" value={`${reviewed.repository}#${reviewed.number} ${reviewed.title}`} />
              <OfferRow label="Head" value={reviewed.head_sha} />
              <OfferRow label="Target" value={`${reviewed.base_branch} at ${reviewed.target_head}`} />
              <OfferRow label="Merge method" value={reviewed.merge_method} />
              <OfferRow
                label="Required checks"
                value={
                  `${reviewed.check_summary.required_passed} passed, ${reviewed.check_summary.required_pending} ` +
                  `pending, ${reviewed.check_summary.required_failed} failed`
                }
              />
              <OfferRow
                label="Proof"
                value={
                  `${reviewed.proof.observation_count} observations, review ${reviewed.proof.review_id.slice(0, 12)}` +
                  `, proof target ${reviewed.proof.proof_target.slice(0, 12)}`
                }
              />
            </dl>
            {reviewed.proof.proof_target !== reviewed.target_head ? (
              <p className="text-sm" data-testid="merge-approval-target-drift">
                {`${reviewed.base_branch} moved after the proof. The proof does not cover the commits between ` +
                  `${reviewed.proof.proof_target.slice(0, 12)} and ${reviewed.target_head.slice(0, 12)}.`}
              </p>
            ) : null}
            {error ? (
              <p className="border-l-4 border-danger bg-surface p-static-sm text-sm" role="alert">
                {stale ? (
                  <>
                    <strong>{STALE_OFFER}</strong>: The offer changed since you opened it, so nothing was merged. Close
                    this dialog and review the current offer.
                  </>
                ) : (
                  <>
                    <strong>{error instanceof WorkItemApiError ? error.code : "Error"}</strong>: {error.message}
                  </>
                )}
              </p>
            ) : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={close}>
                Cancel
              </PButton>
              <PButton type="button" disabled={pendingAction !== null || stale} onClick={() => void approve()}>
                {pendingAction === "merge-approve" ? "Approving..." : "Approve merge"}
              </PButton>
            </div>
          </div>
        </PModal>
      ) : null}
    </>
  );
}
