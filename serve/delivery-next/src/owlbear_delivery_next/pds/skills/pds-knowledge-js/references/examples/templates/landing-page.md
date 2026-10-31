# Landing page

The template is designed for campaigns that require a high-impact, conversion-focused experience. It's built to capture user attention and guide them toward a singular goal, whether that's signing up for a newsletter, exploring a new model, or registering for an event.

- **Type:** Template
- **Components:** [`p-button`](../../components/p-button/p-button.md), [`p-button-pure`](../../components/p-button-pure/p-button-pure.md), [`p-carousel`](../../components/p-carousel/p-carousel.md), [`p-crest`](../../components/p-crest/p-crest.md), [`p-drilldown`](../../components/p-drilldown/p-drilldown.md), [`p-flag`](../../components/p-flag/p-flag.md), [`p-heading`](../../components/p-heading/p-heading.md), [`p-link`](../../components/p-link/p-link.md), [`p-link-pure`](../../components/p-link-pure/p-link-pure.md), [`p-link-tile`](../../components/p-link-tile/p-link-tile.md), [`p-select`](../../components/p-select/p-select.md), [`p-text`](../../components/p-text/p-text.md), [`p-wordmark`](../../components/p-wordmark/p-wordmark.md)
- **Conventions and stylesheet:** shared by all examples, see [examples.md](../../examples.md)

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
              <p-drilldown-link><a href="#features">Jump to features</a></p-drilldown-link>
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
    <main id="main" class="grid-template gap-y-fluid-xl pb-fluid-2xl">
      <section
        class="scheme-dark z-0 col-full grid grid-cols-subgrid items-end h-[clamp(480px,80vh,1000px)] relative before:absolute before:inset-[50%_0_0_0] before:z-1 before:pointer-events-none before:bg-linear-to-t before:from-canvas before:to-transparent"
        aria-labelledby="heading-section-1"
      >
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
          <p-heading id="heading-section-1" class="pb-fluid-md" tag="h1" size="3xl">
            <span class="text-md block">Template</span>
            Landing Page
          </p-heading>
          <p-button variant="secondary">Some label</p-button>
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
      <section
        id="features"
        class="scheme-dark col-full grid grid-cols-subgrid gap-y-fluid-md bg-canvas p-fluid-xl -mt-fluid-xl -mb-fluid-xl"
        aria-label="Some section 2 label"
      >
        <div class="col-basic grid grid-cols-subgrid gap-y-fluid-md">
          <p-link-tile
            class="col-span-full sm:col-span-one-half"
            href="#"
            label="Tickets 2026"
            description="Teaser Headline"
            compact="true"
            weight="regular"
            aspect-ratio="{base: '4/3', xs: '16/9', s: '3/4', m: '1/1'}"
          >
            <img
              src="/examples/media/chrono-car.webp"
              alt="Some alternative text for screen readers describing the media element"
            />
          </p-link-tile>
          <p-link-tile
            class="col-span-full sm:col-span-one-half"
            href="#"
            label="Results"
            description="Teaser Headline"
            compact="true"
            weight="regular"
            aspect-ratio="{base: '4/3', xs: '16/9', s: '3/4', m: '1/1'}"
          >
            <img
              src="/examples/media/addon.webp"
              alt="Some alternative text for screen readers describing the media element"
            />
          </p-link-tile>
        </div>
      </section>
      <section class="col-full grid grid-cols-subgrid py-fluid-xl" aria-label="Some section 3 label">
        <p-carousel
          class="col-span-full"
          slides-per-page="{ base: 1, xs: 1, m: 1 }"
          align-header="center"
          width="extended"
          heading="Carousel"
        >
          <p-link-tile
            gradient
            href="#"
            label="Timeless Enthusiast"
            description="Teaser Heading"
            compact="true"
            aspect-ratio="{base: '1/1', xs: '16/9'}"
            weight="regular"
          >
            <img
              src="/examples/media/interieur-1.webp"
              alt="Some alternative text for screen readers describing the media element"
            />
          </p-link-tile>
          <p-link-tile
            gradient
            href="#"
            label="The Loyalist"
            description="Teaser Heading"
            compact="true"
            aspect-ratio="{base: '1/1', xs: '16/9'}"
            weight="regular"
          >
            <img
              src="/examples/media/interieur-2.webp"
              alt="Some alternative text for screen readers describing the media element"
            />
          </p-link-tile>
          <p-link-tile
            gradient
            href="#"
            label="Urbanist"
            description="Teaser Heading"
            compact="true"
            aspect-ratio="{base: '1/1', xs: '16/9'}"
            weight="regular"
          >
            <img
              src="/examples/media/interieur-3.webp"
              alt="Some alternative text for screen readers describing the media element"
            />
          </p-link-tile>
          <p-link-tile
            gradient
            href="#"
            label="Urbanist"
            description="Teaser Heading"
            compact="true"
            aspect-ratio="{base: '1/1', xs: '16/9'}"
            weight="regular"
          >
            <img
              src="/examples/media/interieur-4.webp"
              alt="Some alternative text for screen readers describing the media element"
            />
          </p-link-tile>
        </p-carousel>
      </section>
      <section class="col-basic grid grid-cols-subgrid gap-y-fluid-xl" aria-label="Some section 4 label">
        <div class="col-span-full grid grid-cols-subgrid gap-y-fluid-lg">
          <img
            class="col-span-full md:col-start-1 md:col-end-7 md:row-start-1 w-full aspect-4/3 md:aspect-3/4 object-cover rounded-3xl"
            src="/examples/media/cockpit.webp"
            alt="Some alternative text for screen readers describing the media element"
          />
          <div
            class="col-span-full md:col-start-8 md:col-end-13 md:row-start-1 flex flex-col justify-center items-start"
          >
            <p-heading tag="h3" size="md">Some Title</p-heading>
            <p-text class="mt-fluid-sm">
              Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore
              et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum
            </p-text>
            <p-text class="mt-fluid-sm" size="xs" color="contrast-medium">
              Lorem ipsum dolor sit amet, consetetur sadipscing elitr
            </p-text>
            <p-link class="mt-fluid-lg"><a href="#">Some label</a></p-link>
          </div>
        </div>
        <div class="col-span-full grid grid-cols-subgrid gap-y-fluid-lg">
          <img
            class="col-span-full md:col-start-7 md:col-end-13 md:row-start-1 w-full aspect-4/3 md:aspect-3/4 object-cover rounded-3xl"
            src="/examples/media/chrono.webp"
            alt="Some alternative text for screen readers describing the media element"
          />
          <div
            class="col-span-full md:col-start-1 md:col-end-6 md:row-start-1 flex flex-col justify-center items-start"
          >
            <p-heading tag="h3" size="md">Some Title</p-heading>
            <p-text class="mt-fluid-sm">
              Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore
              et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum
            </p-text>
            <p-text class="mt-fluid-sm" size="xs" color="contrast-medium">
              Lorem ipsum dolor sit amet, consetetur sadipscing elitr
            </p-text>
            <p-link class="mt-fluid-lg"><a href="#">Some label</a></p-link>
          </div>
        </div>
      </section>
    </main>
    <footer class="grid-template py-fluid-lg bg-surface">
      <form
        class="col-extended grid xs:grid-cols-2 md:grid-cols-3 gap-fluid-md"
        action="#"
        aria-label="Change your delivery country"
      >
        <p-select name="region" value="de" label="Change your delivery country">
          <span slot="selected" class="h-full flex items-center gap-fluid-sm grow">
            <p-flag name="de"></p-flag>
            Germany
          </span>
          <p-optgroup label="Asia">
            <p-select-option value="cn">
              <p-flag name="cn"></p-flag>
              China
            </p-select-option>
            <p-select-option value="jp">
              <p-flag name="jp"></p-flag>
              Japan
            </p-select-option>
            <p-select-option value="kr">
              <p-flag name="kr"></p-flag>
              South Korea
            </p-select-option>
          </p-optgroup>
          <p-optgroup label="Europe">
            <p-select-option value="at">
              <p-flag name="at"></p-flag>
              Austria
            </p-select-option>
            <p-select-option value="fr">
              <p-flag name="fr"></p-flag>
              France
            </p-select-option>
            <p-select-option value="de">
              <p-flag name="de"></p-flag>
              Germany
            </p-select-option>
            <p-select-option value="gb">
              <p-flag name="gb"></p-flag>
              Great Britain
            </p-select-option>
            <p-select-option value="it">
              <p-flag name="it"></p-flag>
              Italy
            </p-select-option>
            <p-select-option value="pt">
              <p-flag name="pt"></p-flag>
              Portugal
            </p-select-option>
            <p-select-option value="es">
              <p-flag name="es"></p-flag>
              Spain
            </p-select-option>
          </p-optgroup>
          <p-optgroup label="North America">
            <p-select-option value="ca">
              <p-flag name="ca"></p-flag>
              Canada
            </p-select-option>
            <p-select-option value="us">
              <p-flag name="us"></p-flag>
              USA
            </p-select-option>
          </p-optgroup>
        </p-select>
      </form>
      <nav
        class="col-extended grid xs:grid-cols-2 md:grid-cols-3 gap-x-fluid-md gap-y-fluid-lg mt-fluid-sm mb-fluid-lg"
        aria-label="Footer"
      >
        <div class="flex flex-col gap-fluid-sm">
          <p-heading id="heading-footer-1" tag="h3" size="2xs" color="contrast-medium">Legal Services</p-heading>
          <ul class="grid gap-fluid-sm">
            <li>
              <p-link-pure icon="none"><a href="#">Terms and Conditions</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Privacy Notice</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">California Privacy</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Imprint and Legal Notice</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Accessibility Statement</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Open Source Software Notice</a></p-link-pure>
            </li>
          </ul>
        </div>
        <div class="flex flex-col gap-fluid-sm">
          <p-heading tag="h3" size="2xs" color="contrast-medium">Porsche Design</p-heading>
          <ul class="grid gap-fluid-sm">
            <li>
              <p-link-pure icon="none"><a href="#">Press</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Jobs and Careers</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Studio F. A. Porsche</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Data Privacy</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Timepieces Warranty &amp; Service</a></p-link-pure>
            </li>
          </ul>
        </div>
        <div class="flex flex-col gap-fluid-sm">
          <p-heading tag="h3" size="2xs" color="contrast-medium">Online Services</p-heading>
          <ul class="grid gap-fluid-sm">
            <li>
              <p-link-pure icon="none"><a href="#">My Orders</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Porsche Homepage</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Porsche Car Configurator</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Porsche New and Pre-Owned Vehicles</a></p-link-pure>
            </li>
            <li>
              <p-link-pure icon="none"><a href="#">Compare Porsche models</a></p-link-pure>
            </li>
          </ul>
        </div>
      </nav>
      <article
        class="col-extended grid sm:grid-cols-[auto_minmax(0,1fr)] items-center gap-x-fluid-lg gap-y-static-lg"
        aria-label="Social media and payment service providers"
      >
        <div class="flex gap-fluid-md">
          <p-link-pure class="p-static-sm -m-static-sm" icon="logo-instagram" hide-label="true" size="md">
            <a href="#">Instagram</a>
          </p-link-pure>
          <p-link-pure class="p-static-sm -m-static-sm" icon="logo-facebook" hide-label="true" size="md">
            <a href="#">Facebook</a>
          </p-link-pure>
          <p-link-pure class="p-static-sm -m-static-sm" icon="logo-x" hide-label="true" size="md">
            <a href="#">X</a>
          </p-link-pure>
          <p-link-pure class="p-static-sm -m-static-sm" icon="logo-pinterest" hide-label="true" size="md">
            <a href="#">Pinterest</a>
          </p-link-pure>
          <p-link-pure class="p-static-sm -m-static-sm" icon="logo-youtube" hide-label="true" size="md">
            <a href="#">YouTube</a>
          </p-link-pure>
        </div>
        <div class="flex gap-fluid-xs">
          <a class="focus-visible:outline outline-focus outline-offset-2 rounded-sm" href="#">
            <img
              src="https://images.ctfassets.net/1oyzmkwpf3d5/hskK1tzN0CS8cdGIttugu/883187acee1c66e7d4593141f3e659c3/Visa.svg"
              alt="visa logo"
            />
          </a>
          <a class="focus-visible:outline outline-focus outline-offset-2 rounded-sm" href="#">
            <img
              src="https://images.ctfassets.net/1oyzmkwpf3d5/34g5LXmVhTzseATJL7CLFj/501eba81ff4787357277faff4ea04f4d/Master__1_.svg"
              alt="master card logo"
            />
          </a>
          <a class="focus-visible:outline outline-focus outline-offset-2 rounded-sm" href="#">
            <img
              src="https://images.ctfassets.net/1oyzmkwpf3d5/4NeGQiGeYT5VZ3G591li1k/c12d0cc589f608a6db3d3e7d2aae0255/PayPal.svg"
              alt="paypal logo"
            />
          </a>
        </div>
      </article>
      <article class="col-extended grid gap-fluid-md mt-fluid-md" aria-label="Consumption and emission information">
        <p-text size="2xs" color="contrast-medium">
          The consumption and emission values stated were determined in accordance with the legally prescribed
          measurement procedures. Since September 1, 2017, certain new vehicles have been type-approved in accordance
          with the Worldwide Harmonized Vehicles Test Procedure (WLTP), a more realistic test procedure for measuring
          fuel/electricity consumption and CO₂ emissions. Since September 1, 2018, the WLTP has replaced the New
          European Driving Cycle (NEDC). Due to the more realistic testing conditions, the fuel/electricity consumption
          and CO₂ emission values measured according to the WLTP are, in many cases, higher than those measured
          according to the NEDC. As a result, vehicle taxation may change accordingly starting September 1, 2018.
          Further information on the differences between WLTP and NEDC can be found at www.porsche.com/wltp.
        </p-text>
        <p-text size="2xs" color="contrast-medium">
          Currently, regardless of the applied type-approval procedure, it remains mandatory to communicate NEDC values.
          The additional disclosure of WLTP values may be done on a voluntary basis until their mandatory use. In the
          case of new vehicles type-approved according to WLTP, NEDC values are derived from WLTP values and stated
          during the transitional period. Where NEDC values are stated as ranges, they do not refer to a specific
          individual vehicle and are not part of the offer. They serve solely for comparison purposes between different
          vehicle types. Optional equipment and accessories (attachments, tire formats, etc.) can alter relevant vehicle
          parameters such as weight, rolling resistance, and aerodynamics, and can influence fuel/electricity
          consumption, CO₂ emissions, and performance values of a vehicle in addition to weather and traffic conditions
          and individual driving behavior. Further information on the official fuel/electricity consumption and official
          specific CO₂ emissions of new passenger cars can be found in the &quot;Guide on fuel consumption, CO₂
          emissions and electricity consumption of new passenger cars,&quot; available free of charge at all sales
          outlets and from DAT.
        </p-text>
        <p-text size="2xs" color="contrast-medium">
          Neither the number of active users of this Porsche Connect Store nor the number of active users of the App
          Center available in the connected vehicle (Macan electric) upon activation of the Connect services exceeds the
          threshold of 45 million active users in the European Union as defined by the Digital Services Act (DSA).
          Important information regarding fully electric Porsche models can be found here.
        </p-text>
      </article>
      <div class="col-extended grid gap-fluid-md justify-items-center mt-fluid-md">
        <p-wordmark></p-wordmark>
        <p-text size="2xs" color="contrast-medium">© 2026 Porsche Sales and Marketplace, Inc.</p-text>
        <ul class="flex flex-wrap justify-center gap-fluid-md">
          <li>
            <p-link-pure icon="none" size="xs" underline><a href="#">Legal notice</a></p-link-pure>
          </li>
          <li>
            <p-link-pure icon="none" size="xs" underline><a href="#">Privacy notice</a></p-link-pure>
          </li>
          <li>
            <p-link-pure icon="none" size="xs" underline><a href="#">Accessibility Statement</a></p-link-pure>
          </li>
          <li>
            <p-link-pure icon="none" size="xs" underline><a href="#">Open Source Software Notice</a></p-link-pure>
          </li>
        </ul>
      </div>
    </footer>
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
