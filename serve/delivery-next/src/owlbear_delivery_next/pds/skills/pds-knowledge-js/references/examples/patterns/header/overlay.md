# Header: Overlay

The header lies on top of the content, typically a full-bleed hero image or video, and is reduced to a single row with brand, navigation and meta actions. The menu opens a drilldown with the site navigation.

- **Type:** Pattern
- **Components:** [`p-button`](../../../components/p-button/p-button.md), [`p-button-pure`](../../../components/p-button-pure/p-button-pure.md), [`p-crest`](../../../components/p-crest/p-crest.md), [`p-drilldown`](../../../components/p-drilldown/p-drilldown.md), [`p-heading`](../../../components/p-heading/p-heading.md), [`p-wordmark`](../../../components/p-wordmark/p-wordmark.md)
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
          <p-button-pure class="p-static-xs -m-static-xs scheme-dark" type="button" icon="search" hide-label="true">
            Search
          </p-button-pure>
          <p-button-pure class="p-static-xs -m-static-xs scheme-dark" type="button" icon="user" hide-label="true">
            User
          </p-button-pure>
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
            Header
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
```
