# p-divider accessibility integration examples

## Integration examples

### Divider as the only section separator

#### ❌ Anti-pattern

```html
<p-text>
  Delivery details
</p-text>

<p-divider></p-divider>

<p-text>
  Payment details
</p-text>
```

#### ✅ Recommended

```html
<p-heading tag="h2" size="md">
  Delivery details
</p-heading>

<p-text>
  ...
</p-text>

<p-divider></p-divider>

<p-heading tag="h2" size="md">
  Payment details
</p-heading>

<p-text>
  ...
</p-text>
```
