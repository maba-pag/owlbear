# p-text accessibility integration examples

## Integration examples

### Heading tag used for styling only

#### ❌ Anti-pattern

```html
<p-text tag="p" size="lg" weight="bold">
  Delivery options
</p-text>
```

#### ✅ Recommended

```html
<p-heading tag="h2" size="lg">
  Delivery options
</p-heading>
```
