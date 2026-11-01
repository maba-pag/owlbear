# p-wordmark accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-wordmark href="/" aria-label="Porsche home"></p-wordmark>
```

#### ✅ Recommended

```html
<p-wordmark href="/" aria="{'aria-label': 'Porsche home'}"></p-wordmark>
```

### Linked wordmark without accessible name

#### ❌ Anti-pattern

```html
<p-wordmark href="/"></p-wordmark>
```

#### ✅ Recommended

```html
<p-wordmark href="/" aria="{'aria-label': 'Porsche home'}"></p-wordmark>
```
