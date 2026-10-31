# p-button-pure accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-button-pure aria-haspopup="dialog" aria-label="Open details of product XYZ">
  Open details
</p-button-pure>
```

#### ✅ Recommended

```html
<p-button-pure aria="{'aria-haspopup': 'dialog', 'aria-label': 'Open details of product XYZ'}">
  Open details
</p-button-pure>
```

### Icon-only button without accessible name

#### ❌ Anti-pattern

```html
<p-button-pure icon="plus"></p-button-pure>
```

#### ✅ Recommended

```html
<p-button-pure icon="plus" hide-label="true">
  Add item XYZ to shopping cart
</p-button-pure>
```

### Vague button label without context

#### ❌ Anti-pattern

```html
<p-button-pure icon="plus">
  Add
</p-button-pure>
```

#### ✅ Recommended

```html
<p-button-pure icon="plus" aria="{'aria-label': 'Add item XYZ to shopping cart'}">
  Add
</p-button-pure>

<!-- or use descriptive visible text -->

<p-button-pure icon="plus">
  Add item XYZ to cart
</p-button-pure>
```
