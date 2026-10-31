# Feedback: Inline

The rating sits directly in the page flow, typically at the end of the content, and stays visible at all times. Once feedback is submitted, it shows a confirmation and offers the option to start over and give new feedback.

- **Type:** Pattern
- **Components:** [`p-button`](../../../components/p-button/p-button.md), [`p-heading`](../../../components/p-heading/p-heading.md), [`p-segmented-control`](../../../components/p-segmented-control/p-segmented-control.md), [`p-text`](../../../components/p-text/p-text.md), [`p-textarea`](../../../components/p-textarea/p-textarea.md)
- **Conventions and stylesheet:** shared by all examples, see [examples.md](../../../examples.md)

## Markup

```html
<html lang="en">
  <body>
    <main id="main" class="grid-template gap-y-fluid-xl py-fluid-lg">
      <section class="col-wide grid gap-fluid-md">
        <p-heading tag="h1" size="xl">Inline feedback</p-heading>
        <p-text>
          The feedback sits in the page, below the content it asks about. Choosing a rating reveals the optional
          comment; submitting replaces the form with the confirmation, which offers to start over.
        </p-text>
      </section>
      <section
        class="col-extended justify-self-center w-full max-w-prose grid gap-fluid-md justify-items-center"
        aria-label="Feedback"
      >
        <p-heading
          id="feedback-question"
          class="focus-visible:outline outline-focus outline-offset-2 rounded-md"
          tag="h2"
          size="md"
          align="center"
          tabindex="-1"
        >
          How satisfied are you with the information shown on this page?
        </p-heading>
        <form id="feedback-form" class="grid gap-fluid-md justify-items-center">
          <div class="w-full grid md:grid-cols-[auto_minmax(320px,1fr)_auto] items-center gap-static-md">
            <p-text
              class="max-sm:hidden row-2 md:row-auto col-1 md:col-auto justify-self-start"
              size="sm"
              align="start"
              color="contrast-medium"
            >
              Very dissatisfied
            </p-text>
            <p-segmented-control
              id="feedback-rating"
              class="row-1 md:row-auto col-span-2 md:col-auto"
              columns="{ base: 1, s: 5 }"
              label="Select your satisfaction from the scale 1 (very dissatisfied) to 5 (very satisfied)"
              hide-label="true"
            >
              <p-segmented-control-item value="1">
                1 
                <span class="sm:sr-only">(very dissatisfied)</span>
              </p-segmented-control-item>
              <p-segmented-control-item value="2">
                2 
                <span class="sm:sr-only">(dissatisfied)</span>
              </p-segmented-control-item>
              <p-segmented-control-item value="3">
                3 
                <span class="sm:sr-only">(neutral)</span>
              </p-segmented-control-item>
              <p-segmented-control-item value="4">
                4 
                <span class="sm:sr-only">(satisfied)</span>
              </p-segmented-control-item>
              <p-segmented-control-item value="5">
                5 
                <span class="sm:sr-only">(very satisfied)</span>
              </p-segmented-control-item>
            </p-segmented-control>
            <p-text
              class="max-sm:hidden row-2 md:row-auto col-2 md:col-auto justify-self-end"
              size="sm"
              align="end"
              color="contrast-medium"
            >
              Very satisfied
            </p-text>
          </div>
          <p-textarea
            id="feedback-comment"
            class="w-full"
            name="comment"
            label="What two things could we do to make this page better?"
            rows="4"
            hidden
          ></p-textarea>
          <p-button id="feedback-submit" type="button" hidden>Submit feedback</p-button>
        </form>
        <div
          id="feedback-thanks"
          class="grid gap-fluid-md justify-items-center"
          aria-live="polite"
          aria-atomic="true"
          hidden
        >
          <p-heading
            id="feedback-thanks-heading"
            class="focus-visible:outline outline-focus outline-offset-2 rounded-md"
            tag="h2"
            size="md"
            align="center"
            tabindex="-1"
          >
            Thank you for your feedback
          </p-heading>
          <p-text align="center">Your feedback helps us continuously improve our page.</p-text>
          <p-button id="feedback-restart" type="button" variant="secondary" icon="refresh">Give new feedback</p-button>
        </div>
      </section>
    </main>
    <script type="module" src="main.js"></script>
  </body>
</html>
```

## Script

```js
// DO NOT USE IN PRODUCTION!
// EXAMPLE CODE FOR DEMONSTRATION PURPOSE ONLY.

// Behaviour of the feedback flow: which of its two steps – the question or the confirmation – is shown.
//
// No data is sent anywhere: the submission is simulated, so the flow can be reviewed end to end.

const question = document.getElementById('feedback-question');
const form = document.getElementById('feedback-form');
const rating = document.getElementById('feedback-rating');
const comment = document.getElementById('feedback-comment');
const submit = document.getElementById('feedback-submit');
const thanks = document.getElementById('feedback-thanks');
const thanksHeading = document.getElementById('feedback-thanks-heading');

// Handle of the simulated request, so dismissing the modal mid-submission can cancel it.
let pendingSubmission;

const cancelSubmission = () => {
  window.clearTimeout(pendingSubmission);
};

// Choosing a rating reveals the optional free-text field and the submit button.
rating.addEventListener('change', () => {
  comment.hidden = false;
  submit.hidden = false;
});

// Reveal the confirmation once the "submission" has completed.
const showConfirmation = () => {
  form.hidden = true;
  question.hidden = true;
  thanks.hidden = false;
  submit.loading = false;
  // Move focus to the confirmation so keyboard and screen reader users are informed.
  thanksHeading.focus();
};

submit.addEventListener('click', () => {
  // Simulate a short server round-trip: show a loading spinner while "submitting", then reveal the
  // confirmation. In a real integration the request would happen here.
  submit.loading = true;
  pendingSubmission = window.setTimeout(showConfirmation, 1200);
});

const startOver = () => {
  cancelSubmission();
  rating.value = '';
  comment.value = '';
  comment.hidden = true;
  submit.loading = false;
  submit.hidden = true;
  thanks.hidden = true;
  question.hidden = false;
  form.hidden = false;
};

// Offered by the flow shown in the page: starting over from the confirmation.
document.getElementById('feedback-restart')?.addEventListener('click', () => {
  startOver();
  // Return focus to the question so the flow is re-announced and can be repeated from the start.
  question.focus();
});

// Shown in a modal, the flow follows it: a submission still pending when the modal is dismissed is cancelled, and
// the next open starts fresh. The reset waits for "motionHiddenEnd", which fires once the close animation has
// finished, so the content does not visibly snap back while the dialog is still on screen.
const enclosingModal = form.closest('p-modal');
enclosingModal?.addEventListener('dismiss', cancelSubmission);
enclosingModal?.addEventListener('motionHiddenEnd', startOver);
```
