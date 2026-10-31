# p-input-date accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-date name="date" label="Date of birth" aria-label="Accessible name" aria-description="Additional context"></p-input-date>
```

#### ✅ Recommended

```html
<p-input-date name="date" label="Date of birth" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-date>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-date name="birthdate" placeholder="Date of birth"></p-input-date>
```

#### ✅ Recommended

```html
<p-input-date name="birthdate" label="Date of birth" description="Enter day, month, and year."></p-input-date>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-date name="birthdate" hide-label="true"></p-input-date>
```

#### ✅ Recommended

```html
<p-input-date name="birthdate" hide-label="true" label="Date of birth"></p-input-date>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-date name="birthdate" label="Date of birth" aria-invalid="true" message="Invalid"></p-input-date>
```

#### ✅ Recommended

```html
<p-input-date name="birthdate" label="Date of birth" state="error" message="Enter a valid date of birth."></p-input-date>
```
