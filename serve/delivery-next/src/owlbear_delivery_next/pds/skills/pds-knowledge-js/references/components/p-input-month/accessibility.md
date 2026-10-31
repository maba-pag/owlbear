# p-input-month accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-month name="month" label="Start month" aria-label="Accessible name" aria-description="Additional context"></p-input-month>
```

#### ✅ Recommended

```html
<p-input-month name="month" label="Start month" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-month>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-month name="month" placeholder="Month"></p-input-month>
```

#### ✅ Recommended

```html
<p-input-month name="month" label="Delivery month" description="Select the month for your delivery."></p-input-month>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-month name="month" hide-label="true"></p-input-month>
```

#### ✅ Recommended

```html
<p-input-month name="month" hide-label="true" label="Delivery month"></p-input-month>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-month name="month" label="Delivery month" aria-invalid="true" message="Required"></p-input-month>
```

#### ✅ Recommended

```html
<p-input-month name="month" label="Delivery month" state="error" message="Select a delivery month to continue."></p-input-month>
```
