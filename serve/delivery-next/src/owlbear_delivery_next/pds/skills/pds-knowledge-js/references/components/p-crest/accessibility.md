# p-crest accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-crest href="/" aria-label="Porsche home"></p-crest>
```

#### ✅ Recommended

```html
<p-crest href="/" aria="{'aria-label': 'Porsche home'}"></p-crest>
```
