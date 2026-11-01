# p-link-pure accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-link-pure href="https://porsche.com" aria-label="Details of product XYZ">
  Details
</p-link-pure>
```

#### ✅ Recommended

```html
<p-link-pure href="https://porsche.com" aria="{'aria-label': 'Details of product XYZ'}">
  Details
</p-link-pure>
```

### Icon-only link without accessible name

#### ❌ Anti-pattern

```html
<p-link-pure icon="arrow-right" href="https://porsche.com"></p-link-pure>
```

#### ✅ Recommended

```html
<p-link-pure icon="arrow-right" hide-label="true" href="https://porsche.com">
  Product details
</p-link-pure>
```

### Indicating the current page

#### ❌ Anti-pattern

```html
<p-link-pure href="/models/911" aria-current="page">
  911
</p-link-pure>
```

#### ✅ Recommended

```html
<p-link-pure href="/models/911" aria="{'aria-current': 'page'}">
  911 Carrera
</p-link-pure>
```

### Vague link label without context

#### ❌ Anti-pattern

```html
<p-link-pure href="https://porsche.com">
  Show
</p-link-pure>
```

#### ✅ Recommended

```html
<p-link-pure href="https://porsche.com" aria="{'aria-label': 'Show details of product XYZ'}">
  Show details
</p-link-pure>
```
