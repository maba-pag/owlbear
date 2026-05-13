# Data Modeler — Critic Debate Log

## Cycle 1

### Draft Position (6 sections)

1. Priority → color collision is "information loss"
2. Token naming needs namespace separator
3. Variable-height cards need rendering contract
4. Dark theme token parity must be build-time validated
5. Column ordering IS a data concern
6. Blocked/Claimed emoji indicators are implicit schema

### Critic Challenges

- **Critical (§5):** Column ordering already consumed from backend topology. The frontend renders columns in API-provided order. Phantom risk.
- **Moderate (§1):** "Information loss" overstated — priority is a typed field in the model, exposed as DOM attribute, used for sorting. The issue is visual discrimination, not data loss.
- **Moderate (§3):** Tags aren't rendered on cards yet. Brief scopes CSS-only, no new features. "Zero height empty sections" doesn't prevent height variance anyway.
- **Moderate (§4):** PDS auto-responsive tokens change the architecture. "Silent data corruption" is category inflation for a CSS fallback rendering incorrectly.
- **Moderate (§6):** States are typed in the model. Card already has some conditional elements. "Implicit schema" overstated.
- **Minor (§2):** Speculative future-proofing for 17 variables.
- **Blind spots:** Ignored board-level hierarchy (status bar, tabs, filter), interaction states, responsive density.

### Revisions

- §1: Softened to "visual discrimination failure"
- §2: Retracted
- §3: Replaced with interaction state consistency
- §4: Narrowed to manual-override path only
- §5: Retracted (risk doesn't exist in current architecture)
- §6: Narrowed to "add data-* attributes for CSS hooks"
- §7: Added responsive density qualification

## Cycle 2

### Revised Position (6 sections)

1. Priority visual discrimination (conf 0.78)
2. (retracted)
3. Interaction state consistency (conf 0.80)
4. Manual-override token parity (conf 0.75)
5. (retracted)
6. Blocked/Claimed styling hooks (conf 0.73)
7. Responsive density qualification (conf 0.70)

### Critic Challenges

- **Critical (§7):** Internally inconsistent with locked D7 decision. Reintroducing max-height contradicts the user's explicit preference for full content.
- **Moderate (§3):** Many state hooks already exist (selected attribute, drag-target attribute, hover/focus native). Blanket rule overstated. Inline styles already consume CSS variables.
- **Moderate (§4):** Misses the larger migration risk — ALL consumers (Shell.css, Card.tsx) must update `--pds-theme-light-*` references to agnostic names. Parity alone isn't sufficient.
- **Minor (§1):** Priority signal may not remain discriminable when stacked with selection/hover/drag states.
- **Blind spots:** Board empty state data signal, status bar, no theme-state plumbing exists yet (D6 requires both auto + manual but zero infrastructure).

### Final Revisions

- §7: Dropped. D7 is locked. Note trade-off only without proposing contradictory constraints.
- §3: Narrowed to migration completeness. Most hooks exist; the gap is inline-to-CSS migration.
- §4: Expanded to full migration scope: rename + dark block + consumer reference update completeness.
- §1: Added note about state-stacking discriminability.
- Added warning about theme infrastructure gap (D6 decided, nothing built).
