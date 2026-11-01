# p-banner accessibility integration examples

## Integration examples

### Banner mounted only when shown

#### ❌ Anti-pattern

```html
// Banner is created only when an error occurs — live region may not announce.
if (hasError) {
  document.body.insertAdjacentHTML('beforeend', '<p-banner open heading="Error">Something went wrong.</p-banner>');
}
```

#### ✅ Recommended

```html
<!-- Pre-render the banner and update content when needed. -->

<p-banner id="form-banner" heading="Error" description="Check the highlighted fields and try again." state="error"></p-banner>
```

### Error feedback without descriptive content

#### ❌ Anti-pattern

```html
<p-banner open="true" state="error" description="Error"></p-banner>
```

#### ✅ Recommended

```html
<p-banner open="true" state="error" heading="Payment could not be processed" description="Check your card details or try another payment method."></p-banner>
```
