# Admin panel

The template is designed for internal tools and management interfaces that require a clear, efficient, and data-driven layout. It's built to help administrators oversee and manage content, users, or system settings with ease — whether that's monitoring key metrics, managing user accounts, or configuring application settings.

- **Type:** Template
- **Components:** [`p-accordion`](../../components/p-accordion/p-accordion.md), [`p-button`](../../components/p-button/p-button.md), [`p-button-pure`](../../components/p-button-pure/p-button-pure.md), [`p-canvas`](../../components/p-canvas/p-canvas.md), [`p-checkbox`](../../components/p-checkbox/p-checkbox.md), [`p-divider`](../../components/p-divider/p-divider.md), [`p-heading`](../../components/p-heading/p-heading.md), [`p-input-search`](../../components/p-input-search/p-input-search.md), [`p-link-pure`](../../components/p-link-pure/p-link-pure.md), [`p-modal`](../../components/p-modal/p-modal.md), [`p-popover`](../../components/p-popover/p-popover.md), [`p-select`](../../components/p-select/p-select.md), [`p-table`](../../components/p-table/p-table.md), [`p-tabs-bar`](../../components/p-tabs-bar/p-tabs-bar.md), [`p-text`](../../components/p-text/p-text.md)
- **Conventions and stylesheet:** shared by all examples, see [examples.md](../../examples.md)

## Markup

```html
<html lang="en" class="scheme-light-dark bg-surface">
  <body>
    <p-canvas id="admin-canvas">
      <a href="#" slot="title">Admin Panel</a>
      <p-button
        id="search-button"
        slot="header-end"
        icon="search"
        variant="secondary"
        compact="true"
        hide-label="true"
        aria="{ 'aria-haspopup': 'dialog' }"
      >
        Open search
      </p-button>
      <p-button
        id="settings-button"
        slot="header-end"
        icon="user"
        variant="secondary"
        compact="true"
        hide-label="true"
        aria="{ 'aria-expanded': false }"
      >
        Open settings sidebar
      </p-button>
      <div class="@container grid grid-cols-12 gap-x-fluid-md">
        <div class="col-span-full flex gap-static-md items-center">
          <p-heading size="xl" tag="h1">Porsche Models</p-heading>
          <p-button type="button" icon="plus" compact="true">Add model</p-button>
        </div>
        <p-tabs-bar id="model-tabs" class="col-span-full mt-fluid-lg" background="surface" active-tab-index="0">
          <button type="button">Overview</button>
          <button type="button">Drafts</button>
        </p-tabs-bar>
        <p-popover>
          <p-button
            class="col-span-full mt-fluid-md justify-self-start"
            slot="button"
            variant="secondary"
            type="button"
            compact="true"
            icon="filter"
          >
            Filter
          </p-button>
          <form class="space-y-fluid-sm" aria-label="Filter models">
            <p-checkbox label="New Car" name="new-car"></p-checkbox>
            <p-checkbox label="Used Car" name="used-car"></p-checkbox>
            <p-checkbox label="Reserved" name="reserved"></p-checkbox>
            <p-checkbox label="Delivered" name="delivered"></p-checkbox>
            <p-checkbox label="Archived" name="archived"></p-checkbox>
          </form>
        </p-popover>
        <p-table
          class="[--p-table-scroll-indicator-top:64px] [--p-table-scroll-indicator-bottom:var(--spacing-static-md)] col-span-full mt-fluid-sm"
          caption="Porsche Models"
          sticky
        >
          <p-table-head>
            <p-table-head-row>
              <p-table-head-cell>Model</p-table-head-cell>
              <p-table-head-cell>Interest</p-table-head-cell>
              <p-table-head-cell>VIN</p-table-head-cell>
              <p-table-head-cell>Purchase Intention</p-table-head-cell>
              <p-table-head-cell>Status</p-table-head-cell>
              <p-table-head-cell>Comment</p-table-head-cell>
              <p-table-head-cell>Lead ID</p-table-head-cell>
              <p-table-head-cell>Action</p-table-head-cell>
            </p-table-head-row>
          </p-table-head>
          <p-table-body>
            <p-table-row>
              <p-table-cell>
                <img src="/examples/media/718.webp" width="80" height="45" alt="Porsche 718 Cayman" />
              </p-table-cell>
              <p-table-cell>New Car</p-table-cell>
              <p-table-cell>
                <p-link-pure underline icon="none"><a href="#">5GAKVCKD8EJ335750</a></p-link-pure>
              </p-table-cell>
              <p-table-cell>08/2021</p-table-cell>
              <p-table-cell>Won</p-table-cell>
              <p-table-cell class="min-w-[10rem]" multiline>-</p-table-cell>
              <p-table-cell>
                0000824402
                <p-popover><p-text>Some additional content</p-text></p-popover>
              </p-table-cell>
              <p-table-cell class="flex gap-static-md">
                <p-button-pure type="button" icon="edit" hide-label="true">Edit 718 Cayman</p-button-pure>
                <p-button-pure type="button" icon="delete" hide-label="true">Delete 718 Cayman</p-button-pure>
              </p-table-cell>
            </p-table-row>
            <p-table-row>
              <p-table-cell>
                <img src="/examples/media/911.webp" width="80" height="45" alt="Porsche 911 Carrera" />
              </p-table-cell>
              <p-table-cell>Used Car</p-table-cell>
              <p-table-cell>
                <p-link-pure underline icon="none"><a href="#">WP0ZZZ99ZTS392124</a></p-link-pure>
              </p-table-cell>
              <p-table-cell>09/2021</p-table-cell>
              <p-table-cell>Won</p-table-cell>
              <p-table-cell class="min-w-[10rem]" multiline>-</p-table-cell>
              <p-table-cell>
                0000824408
                <p-popover><p-text>Some additional content</p-text></p-popover>
              </p-table-cell>
              <p-table-cell class="flex gap-static-md">
                <p-button-pure type="button" icon="edit" hide-label="true">Edit 911 Carrera</p-button-pure>
                <p-button-pure type="button" icon="delete" hide-label="true">Delete 911 Carrera</p-button-pure>
              </p-table-cell>
            </p-table-row>
          </p-table-body>
        </p-table>
        <div class="col-span-full mt-fluid-lg grid grid-cols-subgrid gap-y-fluid-lg">
          <div class="col-span-full @2xl:col-span-4 grid gap-fluid-sm">
            <p-heading size="md" tag="h2">Your Favorites</p-heading>
            <ul class="grid gap-fluid-xs">
              <li>
                <p-link-pure><a href="#">New Relic</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">Bise</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">AWS</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">GRBX Integration Manager</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">Cloud Documentation</a></p-link-pure>
              </li>
            </ul>
          </div>
          <div class="col-span-full @2xl:col-span-4 grid gap-fluid-sm">
            <p-heading size="md" tag="h2">Most Suggested</p-heading>
            <ul class="grid gap-fluid-xs">
              <li>
                <p-link-pure><a href="#">Grafana</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">New Relic</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">BISE Scanners</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">Integration Manager</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">Prisma Cloud</a></p-link-pure>
              </li>
            </ul>
          </div>
          <div class="col-span-full @2xl:col-span-4 grid gap-fluid-sm">
            <p-heading size="md" tag="h2">Quick Links</p-heading>
            <ul class="grid gap-fluid-xs">
              <li>
                <p-link-pure><a href="#">Tools &amp; Services</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">Quick Guide</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">Integration Manager</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">Confluence</a></p-link-pure>
              </li>
              <li>
                <p-link-pure><a href="#">News</a></p-link-pure>
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div slot="sidebar-start">
        <nav id="sidebar-nav" class="flex flex-col gap-static-sm" aria-label="Main">
          <p-heading class="mt-static-md first:mt-0" tag="h2" size="2xs" color="contrast-medium">Fleet</p-heading>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Models</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">911</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Taycan</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Macan</a></p-link-pure>
          </p-accordion>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Configurations</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Exterior</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Interior</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Wheels</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Packages</a></p-link-pure>
          </p-accordion>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Inventory</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">In stock</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">In transit</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Reserved</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Delivered</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Returned</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Archived</a></p-link-pure>
          </p-accordion>
          <p-heading class="mt-static-md first:mt-0" tag="h2" size="2xs" color="contrast-medium">Sales</p-heading>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Leads</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">New</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Qualified</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Won</a></p-link-pure>
          </p-accordion>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Contracts</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Drafts</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Signed</a></p-link-pure>
          </p-accordion>
          <p-heading class="mt-static-md first:mt-0" tag="h2" size="2xs" color="contrast-medium">
            Administration
          </p-heading>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Users</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">People</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Roles</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Invitations</a></p-link-pure>
          </p-accordion>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Dealers</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Locations</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Opening hours</a></p-link-pure>
          </p-accordion>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Integrations</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Webhooks</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">API keys</a></p-link-pure>
          </p-accordion>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Billing</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Invoices</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Payment methods</a></p-link-pure>
          </p-accordion>
          <p-accordion class="[&>:not([slot]):not(:last-child)]:mb-static-sm" compact>
            <p-heading slot="summary" tag="h3" size="sm" weight="semibold">Audit log</p-heading>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Sign-ins</a></p-link-pure>
            <p-link-pure class="w-full ps-static-sm" icon="none"><a href="#">Changes</a></p-link-pure>
          </p-accordion>
        </nav>
        <p-divider class="my-fluid-lg"></p-divider>
        <footer class="grid gap-static-xs justify-items-start">
          <p-text size="2xs" color="contrast-medium">
            © 2026 Dr. Ing. h.c. F. Porsche AG.
            <ul class="flex flex-col gap-fluid-xs mt-fluid-xs">
              <li>
                <p-link-pure icon="none" size="inherit" color="inherit" underline>
                  <a href="#">Privacy Policy</a>
                </p-link-pure>
              </li>
              <li>
                <p-link-pure icon="none" size="inherit" color="inherit" underline>
                  <a href="#">Legal Notice</a>
                </p-link-pure>
              </li>
              <li>
                <p-link-pure icon="none" size="inherit" color="inherit" underline><a href="#">License</a></p-link-pure>
              </li>
              <li>
                <p-link-pure icon="none" size="inherit" color="inherit" underline>
                  <a href="#">Accessibility Statement</a>
                </p-link-pure>
              </li>
            </ul>
          </p-text>
        </footer>
      </div>
      <div slot="sidebar-end">
        <div class="flex gap-fluid-sm items-center">
          <span
            class="w-16 h-16 aspect-square rounded-full bg-surface text-contrast-medium text-lg grid place-content-center"
            aria-hidden="true"
          >
            FP
          </span>
          <p-text>
            Ferdinand Porsche
            <br />
            <span class="text-contrast-medium">Admin</span>
          </p-text>
        </div>
        <p-divider class="my-fluid-md"></p-divider>
        <p-link-pure class="my-static-xs w-full" icon="user"><a href="#">Account</a></p-link-pure>
        <p-link-pure class="my-static-xs w-full" icon="configurate"><a href="#">Settings</a></p-link-pure>
        <p-link-pure class="my-static-xs w-full" icon="chart"><a href="#">Analytics</a></p-link-pure>
        <p-link-pure class="my-static-xs w-full" icon="information"><a href="#">Help</a></p-link-pure>
        <p-divider class="my-fluid-md"></p-divider>
        <p-select id="scheme-select" name="color-scheme" value="scheme-light-dark" label="Color Scheme" compact>
          <p-select-option value="scheme-light">Light</p-select-option>
          <p-select-option value="scheme-dark">Dark</p-select-option>
          <p-select-option value="scheme-light-dark">Light Dark</p-select-option>
        </p-select>
        <p-divider class="my-fluid-md"></p-divider>
        <p-button class="w-full" type="button" icon="none">Logout</p-button>
      </div>
    </p-canvas>
    <p-modal id="search-dialog" class="[--p-modal-width:min(50rem,80vw)]" aria="{ 'aria-label': 'Search' }">
      <p-heading size="md" tag="h2">What are you looking for?</p-heading>
      <p-input-search
        class="mt-fluid-md"
        name="query"
        label="Search"
        indicator
        clear
        placeholder="Search"
        hide-label="true"
      ></p-input-search>
    </p-modal>
    <script type="module" src="main.js"></script>
  </body>
</html>
```

## Script

```js
// DO NOT USE IN PRODUCTION!
// EXAMPLE CODE FOR DEMONSTRATION PURPOSE ONLY.

// Behaviour of the admin panel: the two sidebars of the canvas, the categories of its navigation, the tabs above
// the list, the search dialog and the color scheme switch.
//
// Every one of them is used in *controlled* mode: the components report what the user asked for and this page
// writes the new state back. That is what lets the sidebar affordance mirror its sidebar onto "aria-expanded" and
// the search dialog be opened from a button that is not part of it. None of these events bubbles, so each element
// is wired up itself rather than through a listener on a container.

const canvas = document.getElementById('admin-canvas');
const searchButton = document.getElementById('search-button');
const searchDialog = document.getElementById('search-dialog');
const settingsButton = document.getElementById('settings-button');
const sidebarNav = document.getElementById('sidebar-nav');
const modelTabs = document.getElementById('model-tabs');
const schemeSelect = document.getElementById('scheme-select');

// Keeps the affordance and the sidebar it opens in sync. "hide-label" only hides the label visually, so the
// button keeps its accessible name and only the state has to be announced.
const setSettingsOpen = (isOpen) => {
  canvas.sidebarEndOpen = isOpen;
  settingsButton.aria = { 'aria-expanded': isOpen };
};

canvas.addEventListener('sidebarStartUpdate', (e) => {
  canvas.sidebarStartOpen = e.detail.open;
});
canvas.addEventListener('sidebarEndDismiss', () => setSettingsOpen(false));
settingsButton.addEventListener('click', () => setSettingsOpen(!canvas.sidebarEndOpen));

// The navigation starts out beside the content where there is room for it, and collapsed below that, where the
// canvas turns it into a flyout on top of the page.
canvas.sidebarStartOpen = window.matchMedia('(min-width: 760px)').matches;

for (const accordion of sidebarNav.querySelectorAll('p-accordion')) {
  accordion.addEventListener('update', (e) => {
    accordion.open = e.detail.open;
  });
}

modelTabs.addEventListener('update', (e) => {
  modelTabs.activeTabIndex = e.detail.activeTabIndex;
});

searchButton.addEventListener('click', () => {
  searchDialog.open = true;
});

// Escape, a click outside or the close button request a close in controlled mode – the component restores focus
// to the element the dialog was opened from itself, so only the state has to be written back.
searchDialog.addEventListener('dismiss', () => {
  searchDialog.open = false;
});

// The color scheme is a class on the document element, so it reaches the sidebars as well – they are rendered on
// top of the page and would not be covered by a scheme set further down. The three class names appear nowhere in
// the markup, which is why they are listed here: Tailwind scans this page too and therefore emits all three.
const schemes = ['scheme-light', 'scheme-dark', 'scheme-light-dark'];

schemeSelect.addEventListener('change', (e) => {
  document.documentElement.classList.remove(...schemes);
  document.documentElement.classList.add(e.detail.value);
});
```
