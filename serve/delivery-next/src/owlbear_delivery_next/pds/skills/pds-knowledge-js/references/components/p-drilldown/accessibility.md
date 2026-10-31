# p-drilldown accessibility integration examples

## Integration examples

### ARIA on trigger button host vs aria prop

#### ❌ Anti-pattern

```html
<p-button aria-haspopup="dialog">
  Menu
</p-button>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Vehicle menu
</p-button>
```

### Drilldown label on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-drilldown open="true" aria-label="Navigation">
  ...
</p-drilldown>
```

#### ✅ Recommended

```html
<p-drilldown open="true" aria="{'aria-label': 'Vehicle navigation'}">
  ...
</p-drilldown>
```

### Trigger without popup semantics or context

#### ❌ Anti-pattern

```html
<p-button>
  Menu
</p-button>

<p-drilldown>
  ...
</p-drilldown>
```

#### ✅ Recommended

```html
<p-button aria="{'aria-haspopup': 'dialog'}">
  Vehicle menu
</p-button>

<p-drilldown aria="{'aria-label': 'Vehicle navigation'}">
  ...
</p-drilldown>
```
