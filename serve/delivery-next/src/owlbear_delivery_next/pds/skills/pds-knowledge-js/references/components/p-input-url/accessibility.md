# p-input-url accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-url name="website" label="Website" aria-label="Accessible name" aria-description="Additional context"></p-input-url>
```

#### ✅ Recommended

```html
<p-input-url name="website" label="Website" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-url>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-url name="website" placeholder="https://"></p-input-url>
```

#### ✅ Recommended

```html
<p-input-url name="website" label="Website URL" description="Include https:// at the beginning."></p-input-url>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-url name="website" hide-label="true"></p-input-url>
```

#### ✅ Recommended

```html
<p-input-url name="website" hide-label="true" label="Website URL"></p-input-url>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-url name="website" label="Website URL" aria-invalid="true" message="Invalid"></p-input-url>
```

#### ✅ Recommended

```html
<p-input-url name="website" label="Website URL" state="error" message="Enter a valid URL, for example https://www.porsche.com."></p-input-url>
```
