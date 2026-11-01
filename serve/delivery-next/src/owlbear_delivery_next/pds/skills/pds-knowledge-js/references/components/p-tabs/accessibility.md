# p-tabs accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-tabs aria-label="Product details">
  <p-tabs-item label="Overview">
    ...
  </p-tabs-item>
</p-tabs>
```

#### ✅ Recommended

```html
<p-tabs aria="{'aria-label': 'Porsche 911 configuration details'}">
  <p-tabs-item label="Overview">
    ...
  </p-tabs-item>
  <p-tabs-item label="Equipment">
    ...
  </p-tabs-item>
</p-tabs>
```

### Vague tab labels without context

#### ❌ Anti-pattern

```html
<p-tabs aria="{'aria-label': 'Product details'}">
  <p-tabs-item label="Details">
    ...
  </p-tabs-item>
  <p-tabs-item label="More">
    ...
  </p-tabs-item>
</p-tabs>
```

#### ✅ Recommended

```html
<p-tabs aria="{'aria-label': 'Porsche 911 configuration details'}">
  <p-tabs-item label="Overview">
    ...
  </p-tabs-item>
  <p-tabs-item label="Equipment and packages">
    ...
  </p-tabs-item>
</p-tabs>
```
