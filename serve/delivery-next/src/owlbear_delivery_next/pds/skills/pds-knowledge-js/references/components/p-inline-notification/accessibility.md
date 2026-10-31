# p-inline-notification accessibility integration examples

## Integration examples

### Notification mounted only when needed

#### ❌ Anti-pattern

```html
// Component is created only when a warning appears — live region may not announce.
if (hasWarning) {
  container.innerHTML = '<p-inline-notification state="warning" description="Warning"></p-inline-notification>';
}
```

#### ✅ Recommended

```html
<p-inline-notification
  id="account-warning"
  state="warning"
  heading="Verify your email address"
  description="Confirm your email to receive order updates."
></p-inline-notification>
```

### Warning without descriptive heading

#### ❌ Anti-pattern

```html
<p-inline-notification state="warning" description="Something went wrong"></p-inline-notification>
```

#### ✅ Recommended

```html
<p-inline-notification state="warning" heading="Delivery date unavailable" description="Choose another date or contact your Porsche Centre."></p-inline-notification>
```
