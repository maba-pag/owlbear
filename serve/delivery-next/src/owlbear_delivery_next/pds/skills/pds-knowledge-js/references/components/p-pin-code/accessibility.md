# p-pin-code accessibility integration examples

## Integration examples

### Missing field label

#### ❌ Anti-pattern

```html
<p-pin-code name="verification" length="6"></p-pin-code>
```

#### ✅ Recommended

```html
<p-pin-code name="verification" length="6" label="Verification code" description="Enter the 6-digit code from your email."></p-pin-code>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-pin-code name="verification" length="6" hide-label="true"></p-pin-code>
```

#### ✅ Recommended

```html
<p-pin-code name="verification" length="6" hide-label="true" label="Verification code"></p-pin-code>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-pin-code name="verification" label="Verification code" aria-invalid="true" message="Invalid"></p-pin-code>
```

#### ✅ Recommended

```html
<p-pin-code name="verification" length="6" label="Verification code" state="error" message="Enter the complete 6-digit verification code."></p-pin-code>
```
