# p-scroller accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-scroller aria-label="Section tags" aria-description="Section tags for the section overview">
  <p-tag>
    Overview
  </p-tag>
  <p-tag>
    Equipment
  </p-tag>
</p-scroller>
```

#### ✅ Recommended

```html
<p-scroller aria="{'aria-label': 'Section tags', 'aria-description': 'Section tags for the section overview'}">
  <p-tag>
    Overview
  </p-tag>
  <p-tag>
    Equipment
  </p-tag>
</p-scroller>
```
