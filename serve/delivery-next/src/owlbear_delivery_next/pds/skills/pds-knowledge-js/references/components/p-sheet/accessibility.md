# p-sheet accessibility integration examples

## Integration examples

### ARIA on trigger button host vs aria prop

#### ❌ Anti-pattern

```html
<p-button aria-haspopup="dialog">
  Filter results
</p-button>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Filter results
</p-button>
```

### Dialog label on component host vs header slot

#### ❌ Anti-pattern

```html
<p-sheet aria-label="Filters">
  ...
</p-sheet>
```

#### ✅ Recommended

```html
<p-sheet>
  <p-heading slot="header" tag="h2" size="lg">
    Filter results
  </p-heading>
  ...
</p-sheet>

<!-- or with aria prop when no visible header is shown -->

<p-sheet aria="{'aria-label': 'Filter results'}">
  ...
</p-sheet>
```

### Sheet trigger without popup semantics

#### ❌ Anti-pattern

```html
<p-button>
  Open
</p-button>

<p-sheet>
  <p-heading slot="header" tag="h2" size="lg">
    Filters
  </p-heading>
  ...
</p-sheet>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Filter results
</p-button>

<p-sheet>
  <p-heading slot="header" tag="h2" size="lg">
    Filter results
  </p-heading>
  ...
</p-sheet>
```
