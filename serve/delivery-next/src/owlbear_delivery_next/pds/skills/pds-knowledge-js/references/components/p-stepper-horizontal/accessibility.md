# p-stepper-horizontal accessibility integration examples

## Integration examples

### Generic step labels without context

#### ❌ Anti-pattern

```html
<p-stepper-horizontal>
  <p-stepper-horizontal-item state="complete">
    Step 1
  </p-stepper-horizontal-item>
  <p-stepper-horizontal-item state="current">
    Step 2
  </p-stepper-horizontal-item>
</p-stepper-horizontal>
```

#### ✅ Recommended

```html
<p-stepper-horizontal>
  <p-stepper-horizontal-item state="complete">
    Configure vehicle
  </p-stepper-horizontal-item>
  <p-stepper-horizontal-item state="current">
    Choose delivery date
  </p-stepper-horizontal-item>
  <p-stepper-horizontal-item>
    Review and confirm
  </p-stepper-horizontal-item>
</p-stepper-horizontal>
```
