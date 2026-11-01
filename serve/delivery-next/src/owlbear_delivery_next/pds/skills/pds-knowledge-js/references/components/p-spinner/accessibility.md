# p-spinner accessibility integration examples

## Integration examples

### Spinner mounted only when loading starts

#### ❌ Anti-pattern

```html
if (isLoading) {
  container.innerHTML = '<p-spinner></p-spinner>';
}
```

#### ✅ Recommended

```html
<p-spinner aria="{'aria-label': 'Loading vehicle configuration'}"></p-spinner>
```

### Spinner without loading message

#### ❌ Anti-pattern

```html
<p-spinner></p-spinner>
```

#### ✅ Recommended

```html
<p-spinner aria="{'aria-label': 'Loading vehicle configuration'}"></p-spinner>
```
