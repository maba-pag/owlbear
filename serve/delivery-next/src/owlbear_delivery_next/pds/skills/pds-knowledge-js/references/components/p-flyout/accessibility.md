# p-flyout accessibility integration examples

## Integration examples

### ARIA on trigger button host vs aria prop

#### ❌ Anti-pattern

```html
<p-button aria-haspopup="dialog">
  Open dialog
</p-button>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Open dialog
</p-button>
```

### Dialog label on component host vs header slot

#### ❌ Anti-pattern

```html
<p-flyout aria-label="Navigation">
  ...
</p-flyout>
```

#### ✅ Recommended

```html
<p-flyout>
  <p-heading slot="header" tag="h2" size="lg">
    Main navigation
  </p-heading>
  ...
</p-flyout>

<!-- or with aria prop when no visible header is shown -->

<p-flyout aria="{'aria-label': 'Main navigation'}">
  ...
</p-flyout>
```

### Flyout trigger without popup semantics

#### ❌ Anti-pattern

```html
<p-button>
  Open dialog
</p-button>

<p-flyout>
  <p-heading slot="header" tag="h2" size="lg">
    Dialog heading
  </p-heading>
  ...
</p-flyout>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Open dialog
</p-button>

<p-flyout>
  <p-heading slot="header" tag="h2" size="lg">
    Dialog heading
  </p-heading>
  ...
</p-flyout>
```
