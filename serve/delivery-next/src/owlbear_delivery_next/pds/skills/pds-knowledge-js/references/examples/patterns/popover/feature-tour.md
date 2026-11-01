# Popover: Feature tour

On first visit, a sequence of popovers guides the user through the key areas of the interface one step at a time ("Step 2 of 4", Back / Next / Skip), each anchored to the element it describes. Only a single step is open at once.

- **Type:** Pattern
- **Components:** [`p-button`](../../../components/p-button/p-button.md), [`p-button-pure`](../../../components/p-button-pure/p-button-pure.md), [`p-crest`](../../../components/p-crest/p-crest.md), [`p-heading`](../../../components/p-heading/p-heading.md), [`p-popover`](../../../components/p-popover/p-popover.md), [`p-text`](../../../components/p-text/p-text.md), [`p-wordmark`](../../../components/p-wordmark/p-wordmark.md)
- **Conventions and stylesheet:** shared by all examples, see [examples.md](../../../examples.md)

## Markup

```html
<html lang="en">
  <body>
    <header class="grid-template border-b border-contrast-lower">
      <div class="col-wide grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-fluid-md items-center min-h-[80px]">
        <div class="flex flex-wrap gap-static-md items-center justify-start">
          <p-popover class="[--p-popover-w:20rem]" open data-tour-step="true">
            <p-button-pure
              slot="button"
              class="p-static-xs -m-static-xs"
              type="button"
              icon="menu-lines"
              hide-label="{ base: true, s: false }"
            >
              Menu
            </p-button-pure>
            <div class="grid gap-static-sm">
              <div class="flex items-center justify-between gap-static-md">
                <p-text size="xs" color="contrast-medium">Step 1 of 4</p-text>
                <p-button-pure
                  class="shrink-0 p-static-xs -m-static-xs"
                  type="button"
                  icon="close"
                  hide-label="true"
                  data-tour="skip"
                >
                  Dismiss tips
                </p-button-pure>
              </div>
              <p-heading tag="h2" size="sm" weight="semibold">Main navigation</p-heading>
              <p-text>Open the menu to explore every section of the site.</p-text>
              <div class="flex gap-static-sm">
                <p-button type="button" compact="true" data-tour="next">Next</p-button>
              </div>
            </div>
          </p-popover>
        </div>
        <p-crest class="sm:hidden" href="#"></p-crest>
        <p-wordmark class="max-sm:hidden" href="#"></p-wordmark>
        <div class="flex flex-wrap gap-static-md items-center justify-end">
          <p-popover class="[--p-popover-w:20rem]" data-tour-step="true">
            <p-button-pure slot="button" class="p-static-xs -m-static-xs" type="button" icon="search" hide-label="true">
              Search
            </p-button-pure>
            <div class="grid gap-static-sm">
              <div class="flex items-center justify-between gap-static-md">
                <p-text size="xs" color="contrast-medium">Step 2 of 4</p-text>
                <p-button-pure
                  class="shrink-0 p-static-xs -m-static-xs"
                  type="button"
                  icon="close"
                  hide-label="true"
                  data-tour="skip"
                >
                  Dismiss tips
                </p-button-pure>
              </div>
              <p-heading tag="h2" size="sm" weight="semibold">Search</p-heading>
              <p-text>Find models, dealers and content from anywhere on the site.</p-text>
              <div class="flex gap-static-sm">
                <p-button type="button" variant="secondary" compact="true" data-tour="back">Back</p-button>
                <p-button type="button" compact="true" data-tour="next">Next</p-button>
              </div>
            </div>
          </p-popover>
          <p-popover class="[--p-popover-w:20rem]" data-tour-step="true">
            <p-button-pure slot="button" class="p-static-xs -m-static-xs" type="button" icon="bell" hide-label="true">
              Notifications
            </p-button-pure>
            <div class="grid gap-static-sm">
              <div class="flex items-center justify-between gap-static-md">
                <p-text size="xs" color="contrast-medium">Step 3 of 4</p-text>
                <p-button-pure
                  class="shrink-0 p-static-xs -m-static-xs"
                  type="button"
                  icon="close"
                  hide-label="true"
                  data-tour="skip"
                >
                  Dismiss tips
                </p-button-pure>
              </div>
              <p-heading tag="h2" size="sm" weight="semibold">Notifications</p-heading>
              <p-text>Your latest updates and messages appear right here.</p-text>
              <div class="flex gap-static-sm">
                <p-button type="button" variant="secondary" compact="true" data-tour="back">Back</p-button>
                <p-button type="button" compact="true" data-tour="next">Next</p-button>
              </div>
            </div>
          </p-popover>
          <p-popover class="[--p-popover-w:20rem]" data-tour-step="true">
            <p-button-pure slot="button" class="p-static-xs -m-static-xs" type="button" icon="user" hide-label="true">
              Your account
            </p-button-pure>
            <div class="grid gap-static-sm">
              <div class="flex items-center justify-between gap-static-md">
                <p-text size="xs" color="contrast-medium">Step 4 of 4</p-text>
                <p-button-pure
                  class="shrink-0 p-static-xs -m-static-xs"
                  type="button"
                  icon="close"
                  hide-label="true"
                  data-tour="skip"
                >
                  Dismiss tips
                </p-button-pure>
              </div>
              <p-heading tag="h2" size="sm" weight="semibold">Your account</p-heading>
              <p-text>Manage your profile, orders and settings from here.</p-text>
              <div class="flex gap-static-sm">
                <p-button type="button" variant="secondary" compact="true" data-tour="back">Back</p-button>
                <p-button type="button" compact="true" data-tour="next">Done</p-button>
              </div>
            </div>
          </p-popover>
        </div>
      </div>
    </header>
    <main id="main" class="grid-template">
      <section class="col-wide my-fluid-lg grid gap-fluid-md">
        <p-heading tag="h1" size="xl">Feature tour</p-heading>
        <p-text>
          On first visit, a sequence of popovers walks the user through the key areas of the interface, one step at a
          time. Only a single step is open at once.
        </p-text>
        <p-button class="justify-self-start" id="restart-tour" type="button" variant="secondary" icon="refresh">
          Restart tour
        </p-button>
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

// Behaviour of the feature tour: exactly one coachmark is open at a time, and the sequence can be walked with the
// keyboard alone.
//
// Every step is used in *controlled* mode, so the open state lives here rather than in the components – that is
// what makes "open the next one and close the current one" a single, atomic step.

const steps = Array.from(document.querySelectorAll('[data-tour-step]'));
const restartButton = document.getElementById('restart-tour');

let current = 0;

// The controls of a step are only rendered once its popover is open, so focus is moved two frames later – one for
// the open state to apply, one for the panel to be laid out.
const focusAfterRender = (element) => {
  if (!element) {
    return;
  }
  requestAnimationFrame(() => requestAnimationFrame(() => element.focus()));
};

/** The affordance a step is anchored to, which is also where focus returns when the tour ends. */
const getTrigger = (step) => step?.querySelector('[slot="button"]');
/** The primary action of a step – the natural place to land, so the tour can be continued from the keyboard. */
const getPrimaryAction = (step) => step?.querySelector('[data-tour="next"]');

// Tells keyboard from pointer activation: pressing Enter or Space synthesizes a click with "detail" 0, while
// mouse and touch report "detail >= 1". Focus is only pulled into the tour for keyboard users, so pointer users
// are not yanked into the coachmark they just opened.
const isKeyboardActivation = (event) => event.detail === 0;

// An index outside the range (-1) closes every step, which is how the tour ends.
const showStep = (index, moveFocus = false) => {
  current = index;
  for (const [i, step] of steps.entries()) {
    step.open = i === index;
  }
  // Without this, closing the current popover takes the activated button with it, focus falls back to <body> and
  // the next Tab restarts the tab order at the top of the page.
  if (moveFocus) {
    focusAfterRender(getPrimaryAction(steps[index]));
  }
};

// Ending the tour returns focus to the affordance the last step pointed at, so the user is left in the header
// they were just told about instead of at the start of the document.
const endTour = (moveFocus = false) => {
  const lastTrigger = getTrigger(steps[current]);
  showStep(-1);
  if (moveFocus) {
    lastTrigger?.focus();
  }
};

// The markup opens the first step; setting every step from here puts them all into controlled mode.
showStep(0);

// One listener for the controls of every step: the click is retargeted to the "p-button"/"p-button-pure" host at
// the shadow boundary, so the element carrying "data-tour" is what "closest()" finds.
document.addEventListener('click', (e) => {
  const control = e.target.closest?.('[data-tour]');
  if (!control) {
    return;
  }

  const viaKeyboard = isKeyboardActivation(e);

  switch (control.getAttribute('data-tour')) {
    case 'next':
      if (current + 1 < steps.length) {
        showStep(current + 1, viaKeyboard);
      } else {
        endTour(viaKeyboard);
      }
      break;
    case 'back':
      showStep(Math.max(0, current - 1), viaKeyboard);
      break;
    case 'skip':
      endTour(viaKeyboard);
      break;
  }
});

// Escape or a click outside the current step ends the tour. The component restores focus to its own trigger on
// keyboard dismissal, so nothing is forced here.
for (const step of steps) {
  step.addEventListener('dismiss', () => endTour());
}

// A tour that can only be seen once cannot be reviewed, so this example offers it again.
restartButton.addEventListener('click', (e) => showStep(0, isKeyboardActivation(e)));
```
