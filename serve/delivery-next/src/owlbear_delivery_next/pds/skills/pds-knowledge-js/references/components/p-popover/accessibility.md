# p-popover accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-popover aria-label="Specification details" description="Additional specification details."></p-popover>
```

#### ✅ Recommended

```html
<p-popover aria="{'aria-label': 'Specification details'}" description="Additional specification details."></p-popover>
```

### Custom slotted trigger without accessible name

#### ❌ Anti-pattern

```html
<p-popover>
  <button slot="button" type="button"></button>
  Additional specification details.
</p-popover>
```

#### ✅ Recommended

```html
<p-popover description="Additional specification details."></p-popover>

<!-- or provide an accessible name on a custom slotted button -->

<p-popover>
  <button slot="button" type="button" aria-label="Specification details">
    i
  </button>
  Additional specification details.
</p-popover>
```

### Custom slotted trigger without aria-expanded

#### ❌ Anti-pattern

```html
<p-popover>
  <button slot="button" type="button"></button>
</p-popover>
```

#### ✅ Recommended

```html
<p-popover>
  <button slot="button" type="button" aria-expanded="false"></button>
</p-popover>
```
