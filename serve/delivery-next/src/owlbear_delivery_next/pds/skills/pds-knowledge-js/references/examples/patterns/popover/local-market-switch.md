# Popover: Local market switch

On entering the site, a popover anchored to the globe icon in the header suggests switching to the user's local market for correct content and pricing. It is shown on load and can be dismissed via an outside click or the Escape key.

- **Type:** Pattern
- **Components:** [`p-button`](../../../components/p-button/p-button.md), [`p-button-pure`](../../../components/p-button-pure/p-button-pure.md), [`p-crest`](../../../components/p-crest/p-crest.md), [`p-drilldown`](../../../components/p-drilldown/p-drilldown.md), [`p-heading`](../../../components/p-heading/p-heading.md), [`p-link-pure`](../../../components/p-link-pure/p-link-pure.md), [`p-popover`](../../../components/p-popover/p-popover.md), [`p-sheet`](../../../components/p-sheet/p-sheet.md), [`p-tag`](../../../components/p-tag/p-tag.md), [`p-text`](../../../components/p-text/p-text.md), [`p-wordmark`](../../../components/p-wordmark/p-wordmark.md)
- **Conventions and stylesheet:** shared by all examples, see [examples.md](../../../examples.md)

## Markup

```html
<html lang="en">
  <body>
    <header
      class="z-1 grid-template absolute inset-x-0 before:absolute before:inset-[0_0_-60px_0] before:-z-1 before:pointer-events-none before:bg-fade-to-b"
    >
      <div class="col-wide grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-fluid-md items-center min-h-[80px]">
        <div class="flex flex-wrap gap-static-md items-center justify-start">
          <nav aria-label="Main">
            <p-button-pure
              id="nav-button"
              class="p-static-xs -m-static-xs scheme-dark"
              type="button"
              icon="menu-lines"
              hide-label="{ base: true, s: false }"
              aria="{ 'aria-haspopup': 'dialog' }"
            >
              Menu
            </p-button-pure>
            <p-drilldown id="nav-drilldown">
              <p-drilldown-item identifier="home" label="Home">
                <p-drilldown-link active><a href="#" aria-current="page">Home overview</a></p-drilldown-link>
                <p-drilldown-link><a href="#">Highlights</a></p-drilldown-link>
                <p-drilldown-item identifier="home-models" label="Models">
                  <p-drilldown-link><a href="#">Models overview</a></p-drilldown-link>
                  <p-drilldown-link><a href="#">911</a></p-drilldown-link>
                  <p-drilldown-link><a href="#">Taycan</a></p-drilldown-link>
                </p-drilldown-item>
              </p-drilldown-item>
              <p-drilldown-item identifier="features" label="Features">
                <p-drilldown-link><a href="#">Features overview</a></p-drilldown-link>
                <p-drilldown-link><a href="#">Design</a></p-drilldown-link>
                <p-drilldown-link><a href="#">Technology</a></p-drilldown-link>
              </p-drilldown-item>
              <p-drilldown-link><a href="#">Contact</a></p-drilldown-link>
            </p-drilldown>
          </nav>
        </div>
        <p-crest class="sm:hidden scheme-dark" href="#"></p-crest>
        <p-wordmark class="max-sm:hidden scheme-dark" href="#"></p-wordmark>
        <div class="flex flex-wrap gap-static-md items-center justify-end">
          <p-popover id="market-popover" class="[--p-popover-w:22rem]">
            <p-button-pure
              id="market-button"
              slot="button"
              class="scheme-dark p-static-xs -m-static-xs"
              type="button"
              icon="globe"
              hide-label="true"
              aria="{ 'aria-expanded': true }"
            >
              Local Market
            </p-button-pure>
            <div class="grid gap-fluid-sm">
              <div class="flex gap-static-md items-start">
                <p-text>Do you want to switch to your local market for correct content and pricing?</p-text>
                <p-button-pure
                  id="market-dismiss"
                  class="shrink-0 p-static-xs -m-static-xs"
                  type="button"
                  icon="close"
                  hide-label="true"
                >
                  Dismiss market popover
                </p-button-pure>
              </div>
              <div class="flex flex-wrap gap-static-sm">
                <p-button type="button" compact="true">Go to Local Market</p-button>
                <p-button type="button" variant="secondary" compact="true">International</p-button>
              </div>
            </div>
          </p-popover>
          <p-popover
            id="profile-popover"
            class="[--p-popover-w:22rem] [--p-popover-px:var(--spacing-static-lg)] [--p-popover-py:var(--spacing-static-lg)]"
          >
            <p-button-pure
              id="profile-button"
              slot="button"
              class="scheme-dark p-static-xs -m-static-xs"
              type="button"
              icon="user"
              hide-label="true"
              aria="{ 'aria-expanded': false }"
            >
              User
            </p-button-pure>
            <div class="grid gap-fluid-md">
              <p-heading tag="h2" size="md">Welcome, John Doe</p-heading>
              <div class="grid gap-fluid-xs">
                <p-heading tag="h3" size="sm" color="contrast-medium">Services</p-heading>
                <div class="grid gap-static-xs">
                  <p-link-pure class="py-static-xs" stretch="true" icon="none">
                    <a href="#">My Porsche App</a>
                  </p-link-pure>
                  <p-link-pure class="py-static-xs" stretch="true" icon="none">
                    <a href="#">
                      Messages
                      <p-tag class="ms-static-xs" variant="secondary" compact>3</p-tag>
                    </a>
                  </p-link-pure>
                  <p-link-pure class="py-static-xs" stretch="true" icon="none">
                    <a href="#">Find Connect Services</a>
                  </p-link-pure>
                </div>
              </div>
              <div class="grid gap-fluid-xs">
                <p-heading tag="h3" size="sm" color="contrast-medium">Settings</p-heading>
                <div class="grid gap-static-xs">
                  <p-link-pure class="py-static-xs" stretch="true" icon="none">
                    <a href="#">Profile settings</a>
                  </p-link-pure>
                </div>
              </div>
              <p-button type="button" variant="secondary" icon="none">Logout</p-button>
            </div>
          </p-popover>
        </div>
      </div>
    </header>
    <main id="main" class="grid-template">
      <section class="scheme-dark z-0 col-full grid grid-cols-subgrid items-end h-[clamp(480px,80vh,1000px)]">
        <video
          id="hero-video"
          class="z-0 col-span-full row-span-full min-w-full w-full min-h-full h-full object-cover object-center"
          poster="/examples/media/mood-porsche-gts.webp"
          loop
          muted
          autoplay
          playsinline
        >
          <source src="/examples/media/mood-porsche-gts.mp4" type="video/mp4" />
          <source src="/examples/media/mood-porsche-gts.webm" type="video/webm" />
        </video>
        <div class="z-1 col-extended row-span-full mb-fluid-lg">
          <p-heading tag="h1" size="3xl">
            <span class="text-md block">Pattern</span>
            Popover
          </p-heading>
        </div>
        <p-button
          class="z-2 col-wide place-self-end row-span-full mb-fluid-lg"
          variant="secondary"
          compact="true"
          hide-label="true"
          icon="pause"
          id="pause-button"
        >
          Pause Video
        </p-button>
      </section>
    </main>
    <p-sheet id="profile-sheet" aria="{ 'aria-label': 'User profile' }">
      <p-heading slot="header" tag="h2" size="lg">Welcome, John Doe</p-heading>
      <div class="grid gap-fluid-md">
        <div class="grid gap-fluid-xs">
          <p-heading tag="h3" size="sm" color="contrast-medium">Services</p-heading>
          <div class="grid gap-static-xs">
            <p-link-pure class="py-static-xs" stretch="true" icon="none"><a href="#">My Porsche App</a></p-link-pure>
            <p-link-pure class="py-static-xs" stretch="true" icon="none">
              <a href="#">
                Messages
                <p-tag class="ms-static-xs" variant="secondary" compact>3</p-tag>
              </a>
            </p-link-pure>
            <p-link-pure class="py-static-xs" stretch="true" icon="none">
              <a href="#">Find Connect Services</a>
            </p-link-pure>
          </div>
        </div>
        <div class="grid gap-fluid-xs">
          <p-heading tag="h3" size="sm" color="contrast-medium">Settings</p-heading>
          <div class="grid gap-static-xs">
            <p-link-pure class="py-static-xs" stretch="true" icon="none"><a href="#">Profile settings</a></p-link-pure>
          </div>
        </div>
        <p-button type="button" variant="secondary" icon="none">Logout</p-button>
      </div>
    </p-sheet>
    <script type="module" src="main.js"></script>
  </body>
</html>
```

## Script

```js
// DO NOT USE IN PRODUCTION!
// EXAMPLE CODE FOR DEMONSTRATION PURPOSE ONLY.

// Behaviour of the header navigation: the menu button opens the drilldown, and the drilldown reports the level
// the user drilled into.

const navButton = document.getElementById('nav-button');
const navDrilldown = document.getElementById('nav-drilldown');

navButton.addEventListener('click', () => {
  navDrilldown.open = true;
});

// Closing is requested by the component (Escape, the close button, a click on the backdrop) – the open state is
// owned by the page, so it has to be written back.
navDrilldown.addEventListener('dismiss', (e) => {
  e.target.open = false;
});

navDrilldown.addEventListener('update', (e) => {
  e.target.activeIdentifier = e.detail.activeIdentifier;
});

// Behaviour of the hero video: a pause control that follows the actual state of the video.

const video = document.getElementById('hero-video');
const pauseButton = document.getElementById('pause-button');

// The button hides its label, so its text content is its accessible name – it has to follow the actual state of
// the video, not the last click. Deriving it from the media events also covers autoplay being refused by the
// browser.
const syncPauseButton = () => {
  pauseButton.textContent = video.paused ? 'Play Video' : 'Pause Video';
  pauseButton.icon = video.paused ? 'play' : 'pause';
};

video.addEventListener('play', syncPauseButton);
video.addEventListener('pause', syncPauseButton);

pauseButton.addEventListener('click', () => {
  video[video.paused ? 'play' : 'pause']();
});

// WCAG 2.2: an animation that starts on its own must be stoppable – and it must not start at all when the
// operating system was asked for reduced motion.
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  video.autoplay = false;
  video.pause();
}

syncPauseButton();

// Behaviour of the popover pattern: which of the two disclosures of the header is open, and in which container.
//
// The navigation and the hero video bring their own behaviour, rendered by the partials they are built from. Only
// what is specific to this pattern is written here.
//
// Both popovers and the sheet are used in *controlled* mode: "open" is set from here, so the page always knows
// which one is showing and can mirror it onto the "aria-expanded" of the trigger. In uncontrolled mode the
// component owns that state and the page could not keep the two triggers mutually exclusive.

const marketPopover = document.getElementById('market-popover');
const marketButton = document.getElementById('market-button');
const marketDismiss = document.getElementById('market-dismiss');
const profilePopover = document.getElementById('profile-popover');
const profileSheet = document.getElementById('profile-sheet');
const profileButton = document.getElementById('profile-button');

// A panel anchored to a header icon has no room below "s", so the profile menu is a sheet there and a popover
// above.
const desktopQuery = window.matchMedia('(min-width: 480px)');

// Keeps a trigger's "aria-expanded" in sync with the disclosure it controls. "hide-label" only hides the label
// visually, so the button keeps its accessible name and only the state has to be announced.
const setExpanded = (button, isExpanded) => {
  button.aria = { 'aria-expanded': isExpanded };
};

/** The profile menu, in whichever container the current viewport calls for. Closing covers both. */
const setProfileOpen = (isOpen) => {
  const useSheet = isOpen && !desktopQuery.matches;
  profilePopover.open = isOpen && !useSheet;
  profileSheet.open = useSheet;
  setExpanded(profileButton, isOpen);
};

const setMarketOpen = (isOpen) => {
  marketPopover.open = isOpen;
  setExpanded(marketButton, isOpen);
};

// The market switch is the message the page offers on load; the profile menu waits to be asked for.
setMarketOpen(true);
setProfileOpen(false);

marketButton.addEventListener('click', () => {
  const isOpen = !marketPopover.open;
  setProfileOpen(false);
  setMarketOpen(isOpen);
});

marketDismiss.addEventListener('click', (e) => {
  setMarketOpen(false);
  // Return focus to the trigger for keyboard activation only: pressing Enter/Space synthesizes a click with
  // "detail" 0, while pointer clicks report "detail >= 1". Without it the dismissed panel takes the focused
  // button with it and the next Tab restarts at the top of the page.
  if (e.detail === 0) {
    marketButton.focus();
  }
});

profileButton.addEventListener('click', () => {
  const isOpen = !(profilePopover.open || profileSheet.open);
  setMarketOpen(false);
  setProfileOpen(isOpen);
});

// Escape, a click outside or focus leaving the panel request a close in controlled mode – the components restore
// focus to the trigger themselves, so only the state has to be written back.
marketPopover.addEventListener('dismiss', () => setMarketOpen(false));
profilePopover.addEventListener('dismiss', () => setProfileOpen(false));
profileSheet.addEventListener('dismiss', () => setProfileOpen(false));

// Crossing the breakpoint moves an open profile menu into the other container instead of closing it.
desktopQuery.addEventListener('change', () => setProfileOpen(profilePopover.open || profileSheet.open));
```
