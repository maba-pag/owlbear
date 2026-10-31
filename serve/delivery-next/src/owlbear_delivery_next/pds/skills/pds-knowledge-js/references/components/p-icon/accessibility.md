# p-icon accessibility integration examples

## Integration examples

### Meaningful icon without accessible name

#### ❌ Anti-pattern

```html
<p-icon name="warning"></p-icon>
```

#### ✅ Recommended

```html
<p-icon name="warning" aria="{'aria-label': 'Warning'}"></p-icon>
```

### Decorative icon with redundant label

#### ❌ Anti-pattern

```html
<p-icon name="phone" aria="{'aria-label': 'Phone'}"></p-icon>

<p-text>
  +49 711 911 0
</p-text>
```

#### ✅ Recommended

```html
<p-icon aria-hidden="true" name="phone"></p-icon>

<p-text>
  +49 711 911 0
</p-text>
```
