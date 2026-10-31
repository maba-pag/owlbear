# p-flag accessibility integration examples

## Integration examples

### Informative flag without accessible name

#### ❌ Anti-pattern

```html
<p-flag name="germany"></p-flag>
```

#### ✅ Recommended

```html
<p-flag name="germany" aria="{'aria-label': 'Germany'}"></p-flag>
```

### Decorative flag with redundant label

#### ❌ Anti-pattern

```html
<p-flag name="germany" aria="{'aria-label': 'Germany'}"></p-flag>

<p-text>
  Germany
</p-text>
```

#### ✅ Recommended

```html
<p-flag name="germany" aria-hidden="true"></p-flag>

<p-text>
  Germany
</p-text>
```
