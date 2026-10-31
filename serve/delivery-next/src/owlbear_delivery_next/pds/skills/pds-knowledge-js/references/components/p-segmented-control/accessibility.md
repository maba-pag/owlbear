# p-segmented-control accessibility integration examples

## Integration examples

### Missing group label

#### ❌ Anti-pattern

```html
<p-segmented-control name="size">
  <p-segmented-control-item value="s">
    S
  </p-segmented-control-item>
  <p-segmented-control-item value="m">
    M
  </p-segmented-control-item>
</p-segmented-control>
```

#### ✅ Recommended

```html
<p-segmented-control label="T-shirt size" name="size" description="Select your preferred size.">
  <p-segmented-control-item value="s">
    S
  </p-segmented-control-item>
  <p-segmented-control-item value="m">
    M
  </p-segmented-control-item>
</p-segmented-control>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-segmented-control name="size" hide-label="true">
  <p-segmented-control-item value="s">
    S
  </p-segmented-control-item>
</p-segmented-control>
```

#### ✅ Recommended

```html
<p-segmented-control label="T-shirt size" name="size" hide-label="true">
  <p-segmented-control-item value="s">
    S
  </p-segmented-control-item>
</p-segmented-control>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-segmented-control label="T-shirt size" name="size" aria-invalid="true" message="Required"></p-segmented-control>
```

#### ✅ Recommended

```html
<p-segmented-control label="T-shirt size" name="size" required="true" state="error" message="Select a size to continue."></p-segmented-control>
```
