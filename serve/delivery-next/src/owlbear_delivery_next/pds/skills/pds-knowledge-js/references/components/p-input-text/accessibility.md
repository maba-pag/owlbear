# p-input-text accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-text name="email" label="Email address" aria-label="Accessible name" aria-description="Additional context"></p-input-text>
```

#### ✅ Recommended

```html
<p-input-text name="email" label="Email address" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-text>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-text name="email" placeholder="Email"></p-input-text>
```

#### ✅ Recommended

```html
<p-input-text name="email" label="Email address" description="We use this to send your confirmation."></p-input-text>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-text name="reference" hide-label="true"></p-input-text>
```

#### ✅ Recommended

```html
<p-input-text name="reference" hide-label="true" label="Order reference"></p-input-text>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-text name="email" label="Email" aria-invalid="true" message="Invalid"></p-input-text>
```

#### ✅ Recommended

```html
<p-input-text name="email" label="Email address" state="error" message="Enter a valid email address, for example name@example.com."></p-input-text>
```
