# p-input-email accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-email name="email" label="Email address" aria-label="Accessible name" aria-description="Additional context"></p-input-email>
```

#### ✅ Recommended

```html
<p-input-email name="email" label="Email address" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-email>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-email name="email" placeholder="Email"></p-input-email>
```

#### ✅ Recommended

```html
<p-input-email name="email" label="Email address" description="We use this to send your confirmation."></p-input-email>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-email name="email" hide-label="true"></p-input-email>
```

#### ✅ Recommended

```html
<p-input-email name="email" hide-label="true" label="Email address"></p-input-email>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-email name="email" label="Email" aria-invalid="true" message="Invalid"></p-input-email>
```

#### ✅ Recommended

```html
<p-input-email name="email" label="Email address" state="error" message="Enter a valid email address, for example name@example.com."></p-input-email>
```
