# p-input-time accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-time name="time" label="Appointment time" aria-label="Accessible name" aria-description="Additional context"></p-input-time>
```

#### ✅ Recommended

```html
<p-input-time name="time" label="Appointment time" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-time>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-time name="time" placeholder="Time"></p-input-time>
```

#### ✅ Recommended

```html
<p-input-time name="time" label="Appointment time" description="Use 24-hour format, for example 14:30."></p-input-time>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-time name="time" hide-label="true"></p-input-time>
```

#### ✅ Recommended

```html
<p-input-time name="time" hide-label="true" label="Appointment time"></p-input-time>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-time name="time" label="Appointment time" aria-invalid="true" message="Invalid"></p-input-time>
```

#### ✅ Recommended

```html
<p-input-time name="time" label="Appointment time" state="error" message="Enter a valid appointment time."></p-input-time>
```
