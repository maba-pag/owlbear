# p-link-tile accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-link-tile label="Details" href="#" aria-label="Details of Porsche Taycan"></p-link-tile>
```

#### ✅ Recommended

```html
<p-link-tile label="Details" href="#" aria="{'aria-label': 'Details of Porsche Taycan'}"></p-link-tile>
```

### Vague link label without context

#### ❌ Anti-pattern

```html
<p-link-tile label="Details" href="#"></p-link-tile>
```

#### ✅ Recommended

```html
<p-link-tile label="Porsche Taycan details" href="#"></p-link-tile>
```
