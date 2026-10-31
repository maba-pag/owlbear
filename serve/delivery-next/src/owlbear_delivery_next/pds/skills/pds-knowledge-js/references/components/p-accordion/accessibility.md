# p-accordion accessibility integration examples

## Integration examples

### Accordion summary without semantic heading

#### ❌ Anti-pattern

```html
<p-accordion>
  <span slot="summary">
    Delivery options
  </span>
  <p-text>
    Content about delivery.
  </p-text>
</p-accordion>
```

#### ✅ Recommended

```html
<p-accordion>
  <p-heading slot="summary" tag="h2" size="sm">
    Delivery options
  </p-heading>
  <p-text>
    Content about delivery.
  </p-text>
</p-accordion>
```

### Skipped heading level

#### ❌ Anti-pattern

```html
<p-heading tag="h1">
  Configure your Porsche
</p-heading>

<p-accordion>
  <p-heading slot="summary" tag="h4" size="sm">
    Delivery options
  </p-heading>
  ...
</p-accordion>
```

#### ✅ Recommended

```html
<p-heading tag="h1">
  Configure your Porsche
</p-heading>

<p-accordion>
  <p-heading slot="summary" tag="h2" size="sm">
    Delivery options
  </p-heading>
  ...
</p-accordion>
```
