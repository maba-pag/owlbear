# p-tag-dismissible accessibility integration examples

## Integration examples

### Dismiss button ARIA on host vs aria prop

#### ❌ Anti-pattern

```html
<p-tag-dismissible label="Sport Chrono" aria-label="Remove Sport Chrono filter"></p-tag-dismissible>
```

#### ✅ Recommended

```html
<p-tag-dismissible label="Sport Chrono" aria="{'aria-label': 'Remove Sport Chrono filter'}"></p-tag-dismissible>
```

### Tag without descriptive label

#### ❌ Anti-pattern

```html
<p-tag-dismissible>
  <p-icon name="watch-sport-chrono"></p-icon>
</p-tag-dismissible>
```

#### ✅ Recommended

```html
<p-tag-dismissible label="Sport Chrono Package">
  <p-icon name="watch-sport-chrono"></p-icon>
</p-tag-dismissible>
```
