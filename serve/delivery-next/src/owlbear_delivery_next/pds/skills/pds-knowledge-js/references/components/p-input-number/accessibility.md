# p-input-number accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-number name="quantity" label="Quantity" aria-label="Accessible name" aria-description="Additional context"></p-input-number>
```

#### ✅ Recommended

```html
<p-input-number name="quantity" label="Quantity" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-input-number>
```

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-number name="speed" placeholder="Top speed" unit="kmh"></p-input-number>
```

#### ✅ Recommended

```html
<p-input-number name="speed" label="Top speed" unit="kmh" description="Enter the maximum speed in kilometers per hour."></p-input-number>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-number name="speed" hide-label="true"></p-input-number>
```

#### ✅ Recommended

```html
<p-input-number name="speed" hide-label="true" label="Top speed"></p-input-number>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-number name="speed" label="Top speed" aria-invalid="true" message="Invalid"></p-input-number>
```

#### ✅ Recommended

```html
<p-input-number name="speed" label="Top speed" unit="kmh" description="Enter the maximum speed in kilometers per hour." state="error" message="Enter a speed between 0 and 350 kilometers per hour."></p-input-number>
```
