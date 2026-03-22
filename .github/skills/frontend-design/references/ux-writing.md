# UX Writing Reference

> OwlBear adaptation — see `../NOTICE.md` for attribution.

UX writing is the microcopy that guides users through a UI — button labels,
error messages, empty states, and helper text. Poor UX writing is invisible when
done right and infuriating when done wrong.

---

## Button Labels

Buttons should clearly describe **what will happen**, not just that something
will happen.

| Avoid | Use instead | Why |
|-------|-------------|-----|
| "OK" | "Save changes", "Got it", "Continue" | "OK" requires reading the dialog context first |
| "Submit" | "Send message", "Place order", "Sign up" | "Submit" is form-speak, not user-speak |
| "Yes" / "No" | "Delete account" / "Keep account" | Yes/No requires re-reading the question |
| "Cancel" on a confirm dialog | "Cancel" is fine for the dismissal action | This one IS appropriate |
| "Click here" or "Learn more" | "View pricing", "Read the docs" | Descriptive link text aids screen readers |

Primary button: verb + noun (e.g. "Create project"). Destructive button:
verb + object (e.g. "Delete post"). Length: 1–4 words.

---

## Error Messages

The error message formula:
1. **What went wrong** (briefly, plain language)
2. **Why it happened** (if not obvious)
3. **What to do next** (always)

| Avoid | Use instead |
|-------|-------------|
| "An error occurred." | "Couldn't save. Check your network connection and try again." |
| "Invalid input." | "Email address isn't valid. Use the format name@example.com." |
| "403 Forbidden." | "You don't have permission to view this. Contact your admin." |
| "Something went wrong." | "We couldn't load your items. [Refresh] or [Contact support]." |

Error messages must be **actionable** — this is a **universal blocker** if they
are not.

---

## Form Validation Feedback

- Write errors in the **second person** ("Your password must be…"), not passive
  voice ("Password is invalid").
- Validate on blur (field exit), not on keystroke while typing.
- Place the error message adjacent to the field (below it, associated with `aria-describedby`).
- Do not use colour alone to signal errors — include an icon and text.
- For long forms, show a summary at the top and link to each invalid field.

---

## Empty States

Every empty state needs three elements:

1. **Illustration or icon** — gives the user visual confirmation that "empty" is intentional.
2. **Headline** — tells them what is empty (e.g., "No projects yet").
3. **Call to action** — tells them what to do next (e.g., "Create your first project →").

Avoid: "No data found." or just hiding the section. Dead ends erode trust.

---

## Tone

Match tone to context:

| Context | Tone | Example |
|---------|------|---------|
| Onboarding/marketing | Warm, encouraging, active voice | "You're 2 steps away from your first deploy." |
| UI labels and actions | Neutral, efficient, imperative | "Archive", "Export CSV", "Invite member" |
| Errors and warnings | Direct, calm, empathetic | "Failed to save. Your changes are still here — try again." |
| Destructive confirmations | Clear, non-alarming | "This will permanently delete 3 files." |
| Loading states | Brief, present tense | "Loading your workspace…" |

Do not inject humour into error states unless the brand explicitly calls for it —
a frustrated user does not want a joke.

---

## Internationalization (i18n)

Write copy with translation in mind:

- Avoid idioms and colloquialisms that don't translate.
- Build UI to handle **text expansion** — German, Finnish, and Dutch expand
  English strings by 30–50%. Buttons and labels must accommodate longer text.
- Do not concatenate strings to form sentences; use full-sentence templates with
  placeholders: `"Deleting {count} file(s)"` not `"Deleting " + count + " file(s)"`.
- Avoid gender-dependent phrasing where possible.
- Use Unicode-safe number and date formatting (`Intl.NumberFormat`,
  `Intl.DateTimeFormat`) rather than hardcoded separators.

---

## Terminology

Be consistent. Define a terminology glossary early:

- Choose **one word per concept** and use it everywhere (e.g., always "workspace",
  never "workspace/project/organisation").
- Distinguish user-visible labels from internal technical terms.
- Document the glossary in a shared design token or content file.
