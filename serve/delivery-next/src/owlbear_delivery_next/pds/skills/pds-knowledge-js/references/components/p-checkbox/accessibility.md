# p-checkbox accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-checkbox name="terms" label="I accept the terms" aria-label="Accessible name" aria-description="Additional context"></p-checkbox>
```

#### ✅ Recommended

```html
<p-checkbox name="terms" label="I accept the terms" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-checkbox>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-checkbox name="terms" hide-label="true"></p-checkbox>
```

#### ✅ Recommended

```html
<p-checkbox name="terms" hide-label="true" label="I accept the terms and conditions"></p-checkbox>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-checkbox name="terms" label="I accept the terms and conditions" aria-invalid="true" message="Required"></p-checkbox>
```

#### ✅ Recommended

```html
<p-checkbox name="terms" label="I accept the terms and conditions" required="true" state="error" message="Accept the terms and conditions to continue."></p-checkbox>
```
