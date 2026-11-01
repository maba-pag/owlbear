# p-modal accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-button aria-haspopup="dialog">
  Details of product XYZ
</p-button>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Details of product XYZ
</p-button>
```

### Dialog label on component host vs header slot

#### ❌ Anti-pattern

```html
<p-modal aria-label="Details">
  ...
</p-modal>
```

#### ✅ Recommended

```html
<p-modal>
  <p-heading slot="header" tag="h2" size="lg">
    Details of product XYZ
  </p-heading>
  ...
</p-modal>

<!-- or with aria prop when no visible header is shown -->

<p-modal aria="{'aria-label': 'Details of product XYZ'}">
  ...
</p-modal>
```

### Modal trigger without popup semantics or context

#### ❌ Anti-pattern

```html
<p-button>
  Open
</p-button>

<p-modal>
  <p-heading slot="header" tag="h2" size="lg">
    Details
  </p-heading>
  ...
</p-modal>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Details of product XYZ
</p-button>

<p-modal>
  <p-heading slot="header" tag="h2" size="lg">
    Details of product XYZ
  </p-heading>
  ...
</p-modal>
```
