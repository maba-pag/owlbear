# p-radio-group accessibility integration examples

## Integration examples

### Missing group label

#### ❌ Anti-pattern

```html
<p-radio-group name="fuel">
  <p-radio-group-option value="electric" label="Electric"></p-radio-group-option>
  <p-radio-group-option value="hybrid" label="Hybrid"></p-radio-group-option>
</p-radio-group>
```

#### ✅ Recommended

```html
<p-radio-group label="Powertrain" name="fuel" description="Select your preferred powertrain.">
  <p-radio-group-option value="electric" label="Electric"></p-radio-group-option>
  <p-radio-group-option value="hybrid" label="Hybrid"></p-radio-group-option>
</p-radio-group>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-radio-group name="fuel" hide-label="true">
  <p-radio-group-option value="electric" label="Electric"></p-radio-group-option>
  <p-radio-group-option value="hybrid" label="Hybrid"></p-radio-group-option>
</p-radio-group>
```

#### ✅ Recommended

```html
<p-radio-group label="Powertrain" name="fuel" hide-label="true">
  <p-radio-group-option value="electric" label="Electric"></p-radio-group-option>
  <p-radio-group-option value="hybrid" label="Hybrid"></p-radio-group-option>
</p-radio-group>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-radio-group label="Powertrain" name="fuel" aria-invalid="true" message="Required">
  <p-radio-group-option value="electric" label="Electric"></p-radio-group-option>
  <p-radio-group-option value="hybrid" label="Hybrid"></p-radio-group-option>
</p-radio-group>
```

#### ✅ Recommended

```html
<p-radio-group label="Powertrain" name="fuel" required="true" state="error" message="Select a powertrain to continue.">
  <p-radio-group-option value="electric" label="Electric"></p-radio-group-option>
  <p-radio-group-option value="hybrid" label="Hybrid"></p-radio-group-option>
</p-radio-group>
```
