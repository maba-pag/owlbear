# p-text-list accessibility integration examples

## Integration examples

### Numbered list for non-sequential items

#### ❌ Anti-pattern

```html
<p-text-list type="numbered">
  <p-text-list-item>
    Sport Chrono Package
  </p-text-list-item>
  <p-text-list-item>
    BOSE Surround Sound
  </p-text-list-item>
</p-text-list>
```

#### ✅ Recommended

```html
<p-text-list type="unordered">
  <p-text-list-item>
    Sport Chrono Package
  </p-text-list-item>
  <p-text-list-item>
    BOSE Surround Sound
  </p-text-list-item>
</p-text-list>
```
