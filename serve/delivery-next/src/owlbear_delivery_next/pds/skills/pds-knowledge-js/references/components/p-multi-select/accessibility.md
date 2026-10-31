# p-multi-select accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-multi-select name="options" label="Optional extras" aria-label="Accessible name" aria-description="Additional context">
  <p-multi-select-option value="option-a">
    Option A
  </p-multi-select-option>
</p-multi-select>
```

#### ✅ Recommended

```html
<p-multi-select name="options" label="Optional extras" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}">
  <p-multi-select-option value="option-a">
    Option A
  </p-multi-select-option>
</p-multi-select>
```

### Prompt option used instead of a label

#### ❌ Anti-pattern

```html
<p-multi-select name="features">
  <p-multi-select-option value="">
    Select features
  </p-multi-select-option>
  <p-multi-select-option value="sport">
    Sport Chrono Package
  </p-multi-select-option>
</p-multi-select>
```

#### ✅ Recommended

```html
<p-multi-select label="Optional features" name="features" description="Select all features for your configuration.">
  <p-multi-select-option value="sport">
    Sport Chrono Package
  </p-multi-select-option>
  <p-multi-select-option value="audio">
    BOSE Surround Sound
  </p-multi-select-option>
</p-multi-select>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-multi-select name="features" hide-label="true">
  <p-multi-select-option value="sport">
    Sport Chrono Package
  </p-multi-select-option>
</p-multi-select>
```

#### ✅ Recommended

```html
<p-multi-select label="Optional features" name="features" hide-label="true">
  <p-multi-select-option value="sport">
    Sport Chrono Package
  </p-multi-select-option>
</p-multi-select>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-multi-select label="Optional features" name="features" aria-invalid="true" message="Required">
  <p-multi-select-option value="sport">
    Sport Chrono Package
  </p-multi-select-option>
</p-multi-select>
```

#### ✅ Recommended

```html
<p-multi-select label="Optional features" name="features" required="true" state="error" message="Select at least one feature to continue.">
  <p-multi-select-option value="sport">
    Sport Chrono Package
  </p-multi-select-option>
  <p-multi-select-option value="audio">
    BOSE Surround Sound
  </p-multi-select-option>
</p-multi-select>
```
