# p-input-week accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-week name="week" label="Calendar week" aria-label="Accessible name" aria-description="Additional context"></p-input-week>
```

#### ✅ Recommended

```html
<p-input-week name="week" label="Calendar week" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-week>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-week name="week" placeholder="Week"></p-input-week>
```

#### ✅ Recommended

```html
<p-input-week name="week" label="Calendar week" description="Select the week for your test drive."></p-input-week>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-week name="week" hide-label="true"></p-input-week>
```

#### ✅ Recommended

```html
<p-input-week name="week" hide-label="true" label="Calendar week"></p-input-week>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-week name="week" label="Calendar week" aria-invalid="true" message="Required"></p-input-week>
```

#### ✅ Recommended

```html
<p-input-week name="week" label="Calendar week" state="error" message="Select a calendar week to continue."></p-input-week>
```
