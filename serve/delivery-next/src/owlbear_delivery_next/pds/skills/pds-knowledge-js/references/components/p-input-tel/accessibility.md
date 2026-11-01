# p-input-tel accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-tel name="phone" label="Phone number" aria-label="Accessible name" aria-description="Additional context"></p-input-tel>
```

#### ✅ Recommended

```html
<p-input-tel name="phone" label="Phone number" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-tel>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-tel name="phone" placeholder="Phone"></p-input-tel>
```

#### ✅ Recommended

```html
<p-input-tel name="phone" label="Phone number" description="Include your country code, for example +49."></p-input-tel>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-tel name="phone" hide-label="true"></p-input-tel>
```

#### ✅ Recommended

```html
<p-input-tel name="phone" hide-label="true" label="Phone number"></p-input-tel>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-tel name="phone" label="Phone number" aria-invalid="true" message="Invalid"></p-input-tel>
```

#### ✅ Recommended

```html
<p-input-tel name="phone" label="Phone number" state="error" message="Enter a valid phone number including your country code."></p-input-tel>
```
