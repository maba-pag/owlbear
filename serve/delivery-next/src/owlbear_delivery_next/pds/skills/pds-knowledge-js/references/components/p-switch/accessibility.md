# p-switch accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-switch aria-label="Dark mode" aria-description="Toggles the color theme">
  Dark mode
</p-switch>
```

#### ✅ Recommended

```html
<p-switch aria="{'aria-label': 'Dark mode', 'aria-description': 'Toggles the color theme'}">
  Dark mode
</p-switch>
```

### Switch without descriptive label

#### ❌ Anti-pattern

```html
<p-switch name="notifications"></p-switch>
```

#### ✅ Recommended

```html
<p-switch name="notifications">
  Email notifications for order updates
</p-switch>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-switch name="notifications" hide-label="true"></p-switch>
```

#### ✅ Recommended

```html
<p-switch name="notifications" hide-label="true">
  Email notifications for order updates
</p-switch>
```
