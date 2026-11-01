# p-link accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-link href="https://porsche.com" aria-label="Details of product XYZ">
  Details
</p-link>
```

#### ✅ Recommended

```html
<p-link href="https://porsche.com" aria="{'aria-label': 'Details of product XYZ'}">
  Details
</p-link>
```

### Icon-only link without accessible name

#### ❌ Anti-pattern

```html
<p-link icon="arrow-right" href="https://porsche.com"></p-link>
```

#### ✅ Recommended

```html
<p-link icon="arrow-right" hide-label="true" href="https://porsche.com">
  Product details
</p-link>
```

### Indicating the current page

#### ❌ Anti-pattern

```html
<p-link href="/models/911" aria-current="page">
  911
</p-link>
```

#### ✅ Recommended

```html
<p-link href="/models/911" aria="{'aria-current': 'page'}">
  911 Carrera
</p-link>
```

### Vague link label without context

#### ❌ Anti-pattern

```html
<p-link href="https://porsche.com">
  Show
</p-link>
```

#### ✅ Recommended

```html
<p-link href="https://porsche.com" aria="{'aria-label': 'Show details of product XYZ'}">
  Show details
</p-link>
```
