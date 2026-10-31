# Header: Stacked

The header sits above the content instead of lying on top of it: a note on top, the bar with brand, navigation and meta actions in the middle, and a row of category navigation below. The menu opens a drilldown with the site navigation.

- **Type:** Pattern
- **Components:** [`p-button-pure`](../../../components/p-button-pure/p-button-pure.md), [`p-crest`](../../../components/p-crest/p-crest.md), [`p-drilldown`](../../../components/p-drilldown/p-drilldown.md), [`p-heading`](../../../components/p-heading/p-heading.md), [`p-link-pure`](../../../components/p-link-pure/p-link-pure.md), [`p-tabs-bar`](../../../components/p-tabs-bar/p-tabs-bar.md), [`p-text`](../../../components/p-text/p-text.md), [`p-wordmark`](../../../components/p-wordmark/p-wordmark.md)
- **Conventions and stylesheet:** shared by all examples, see [examples.md](../../../examples.md)

## Markup

```html
<html lang="en">
  <body>
    <header class="grid-template gap-y-0">
      <div class="scheme-dark col-full flex justify-center py-static-xs px-static-md bg-surface">
        <p-text size="xs">All sizes shown for Porsche Lifestyle products are EU sizes</p-text>
      </div>
      <div class="col-wide grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-fluid-md items-center min-h-[80px]">
        <div class="flex flex-wrap gap-static-md items-center justify-start">
          <nav aria-label="Main">
            <p-button-pure
              id="nav-button"
              class="p-static-xs -m-static-xs"
              type="button"
              icon="menu-lines"
              hide-label="{ base: true, s: false }"
              aria="{ 'aria-haspopup': 'dialog' }"
            >
              Menu
            </p-button-pure>
            <p-drilldown id="nav-drilldown">
              <p-drilldown-item identifier="home" label="Home">
                <p-drilldown-link><a href="#">Home overview</a></p-drilldown-link>
                <p-drilldown-link><a href="#">Highlights</a></p-drilldown-link>
                <p-drilldown-item identifier="home-models" label="Models">
                  <p-drilldown-link><a href="#">Models overview</a></p-drilldown-link>
                  <p-drilldown-link><a href="#">911</a></p-drilldown-link>
                  <p-drilldown-link><a href="#">Taycan</a></p-drilldown-link>
                </p-drilldown-item>
              </p-drilldown-item>
              <p-drilldown-item identifier="features" label="Features">
                <p-drilldown-link active><a href="#" aria-current="page">Features overview</a></p-drilldown-link>
                <p-drilldown-link><a href="#">Design</a></p-drilldown-link>
                <p-drilldown-link><a href="#">Technology</a></p-drilldown-link>
              </p-drilldown-item>
              <p-drilldown-link><a href="#">Contact</a></p-drilldown-link>
              <p-drilldown-link><a href="#">Stories</a></p-drilldown-link>
            </p-drilldown>
          </nav>
        </div>
        <p-crest class="sm:hidden" href="#"></p-crest>
        <p-wordmark class="max-sm:hidden" href="#"></p-wordmark>
        <div class="flex flex-wrap gap-static-md items-center justify-end">
          <p-button-pure class="p-static-xs -m-static-xs" type="button" icon="search" hide-label="true">
            Search
          </p-button-pure>
          <p-link-pure class="p-static-xs -m-static-xs" href="#" icon="heart" hide-label="true">Favorites</p-link-pure>
          <p-link-pure class="p-static-xs -m-static-xs" href="#" icon="shopping-cart" hide-label="true">
            Shopping Cart
          </p-link-pure>
          <p-button-pure class="p-static-xs -m-static-xs" type="button" icon="user" hide-label="true">
            User
          </p-button-pure>
        </div>
      </div>
      <nav class="col-full flex justify-center p-static-md border-t-thin border-contrast-low" aria-label="Categories">
        <p-tabs-bar compact>
          <a href="#">All categories</a>
          <a href="#">Timepieces</a>
          <a href="#">Bags &amp; Luggage</a>
          <a href="#">Heritage</a>
          <a href="#">Vehicle Accessories</a>
          <a href="#">Eyewear</a>
        </p-tabs-bar>
      </nav>
    </header>
    <main id="main" class="grid-template">
      <section class="scheme-dark col-full grid grid-cols-subgrid items-end h-[clamp(480px,80vh,1000px)]">
        <img
          class="col-span-full row-span-full min-w-full w-full min-h-full h-full object-cover object-center"
          src="/examples/media/trolley.webp"
          alt
        />
        <div class="col-extended row-span-full mb-fluid-lg">
          <p-heading tag="h1" size="3xl">
            <span class="text-md block">Pattern</span>
            Header
          </p-heading>
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
```
