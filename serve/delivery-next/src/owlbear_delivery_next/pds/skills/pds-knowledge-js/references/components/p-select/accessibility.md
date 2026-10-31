# p-select accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-select name="model" label="Porsche model" aria-label="Accessible name" aria-description="Additional context">
  <p-select-option value="option-a">
    Option A
  </p-select-option>
</p-select>
```

#### ✅ Recommended

```html
<p-select name="model" label="Porsche model" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}">
  <p-select-option value="option-a">
    Option A
  </p-select-option>
</p-select>
```

### Prompt option used instead of a label

#### ❌ Anti-pattern

```html
<p-select name="model">
  <p-select-option value="">
    Select a model
  </p-select-option>
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
  <p-select-option value="carrera-s">
    911 Carrera S
  </p-select-option>
</p-select>
```

#### ✅ Recommended

```html
<p-select label="Porsche model" name="model" description="Choose the model for your configuration.">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
  <p-select-option value="carrera-s">
    911 Carrera S
  </p-select-option>
</p-select>
```

### Ambiguous option labels without field context

#### ❌ Anti-pattern

```html
<p-select label="Model" name="model">
  <p-select-option value="base">
    Base
  </p-select-option>
  <p-select-option value="s">
    S
  </p-select-option>
</p-select>
```

#### ✅ Recommended

```html
<p-select label="Porsche 911 trim" name="model" description="Select the trim level for your configuration.">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
  <p-select-option value="carrera-s">
    911 Carrera S
  </p-select-option>
</p-select>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-select name="model" hide-label="true">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
</p-select>
```

#### ✅ Recommended

```html
<p-select label="Porsche model" name="model" hide-label="true">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
</p-select>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-select label="Porsche model" name="model" aria-invalid="true" message="Required">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
  <p-select-option value="carrera-s">
    911 Carrera S
  </p-select-option>
</p-select>
```

#### ✅ Recommended

```html
<p-select label="Porsche model" name="model" state="error" message="Select a model to continue with your configuration.">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
  <p-select-option value="carrera-s">
    911 Carrera S
  </p-select-option>
</p-select>
```

### Error state without recovery guidance

#### ❌ Anti-pattern

```html
<p-select label="Porsche model" name="model" state="error" message="Invalid">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
  <p-select-option value="carrera-s">
    911 Carrera S
  </p-select-option>
</p-select>
```

#### ✅ Recommended

```html
<p-select label="Porsche model" name="model" required="true" state="error" message="Select a Porsche model. This field is required to continue.">
  <p-select-option value="carrera">
    911 Carrera
  </p-select-option>
  <p-select-option value="carrera-s">
    911 Carrera S
  </p-select-option>
</p-select>
```
