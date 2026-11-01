# p-button accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-button aria-haspopup="dialog" aria-label="Open details of product XYZ">
  Open details
</p-button>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog', 'aria-label': 'Open details of product XYZ'}">
  Open details
</p-button>
```

### Icon-only button without accessible name

#### ❌ Anti-pattern

```html
<p-button icon="plus"></p-button>
```

#### ✅ Recommended

```html
<p-button icon="plus" hide-label="true">
  Add item XYZ to shopping cart
</p-button>
```

### Vague button label without context

#### ❌ Anti-pattern

```html
<p-button icon="plus">
  Add
</p-button>
```

#### ✅ Recommended

```html
<p-button icon="plus" aria="{'aria-label': 'Add item XYZ to shopping cart'}">
  Add
</p-button>

<!-- or use descriptive visible text -->

<p-button icon="plus">
  Add item XYZ to cart
</p-button>
```
