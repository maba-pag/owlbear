# p-input-password accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-password name="password" label="Password" aria-label="Accessible name" aria-description="Additional context"></p-input-password>
```

#### ✅ Recommended

```html
<p-input-password name="password" label="Password" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-password>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-password name="password" placeholder="Password"></p-input-password>
```

#### ✅ Recommended

```html
<p-input-password name="password" label="Password" description="Use at least 8 characters with one number."></p-input-password>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-password name="password" hide-label="true"></p-input-password>
```

#### ✅ Recommended

```html
<p-input-password name="password" hide-label="true" label="Password"></p-input-password>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-password name="password" label="Password" aria-invalid="true" message="Invalid"></p-input-password>
```

#### ✅ Recommended

```html
<p-input-password name="password" label="Password" state="error" message="Enter a password with at least 8 characters and one number."></p-input-password>
```
