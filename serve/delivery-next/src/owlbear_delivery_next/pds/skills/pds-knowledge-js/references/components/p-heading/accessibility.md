# p-heading accessibility integration examples

## Integration examples

### Skipped heading level

#### ❌ Anti-pattern

```html
<p-heading tag="h1" size="xl">
  Configure your Porsche
</p-heading>

<p-heading tag="h4" size="md">
  Delivery options
</p-heading>
```

#### ✅ Recommended

```html
<p-heading tag="h1" size="xl">
  Configure your Porsche
</p-heading>

<p-heading tag="h2" size="md">
  Delivery options
</p-heading>
```
