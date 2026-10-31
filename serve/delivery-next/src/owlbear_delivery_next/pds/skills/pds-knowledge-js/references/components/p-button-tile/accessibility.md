# p-button-tile accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-button-tile label="Open" aria-label="Open details of Porsche Taycan" aria-haspopup="dialog"></p-button-tile>
```

#### ✅ Recommended

```html
<p-button-tile label="Open" aria="{'aria-haspopup': 'dialog', 'aria-label': 'Open details of Porsche Taycan'}"></p-button-tile>
```

### Vague tile label without context

#### ❌ Anti-pattern

```html
<p-button-tile label="Open"></p-button-tile>
```

#### ✅ Recommended

```html
<p-button-tile label="Configure Porsche Taycan"></p-button-tile>
```
