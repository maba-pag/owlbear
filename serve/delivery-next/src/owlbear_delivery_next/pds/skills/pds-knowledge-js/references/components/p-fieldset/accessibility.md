# p-fieldset accessibility integration examples

## Integration examples

### Unlabeled field group

#### ❌ Anti-pattern

```html
<p-fieldset>
  <p-input-text name="street" label="Street"></p-input-text>
  <p-input-text name="city" label="City"></p-input-text>
</p-fieldset>
```

#### ✅ Recommended

```html
<p-fieldset label="Delivery address">
  <p-input-text name="street" label="Street"></p-input-text>
  <p-input-text name="city" label="City"></p-input-text>
</p-fieldset>
```

### Error state without recovery guidance

#### ❌ Anti-pattern

```html
<p-fieldset label="Delivery address" state="error" message="Invalid"></p-fieldset>
```

#### ✅ Recommended

```html
<p-fieldset label="Delivery address" required="true" state="error" message="Complete all required address fields to continue."></p-fieldset>
```
