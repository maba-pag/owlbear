# p-textarea accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-textarea name="comment" label="Comment" aria-label="Accessible name" aria-description="Additional context"></p-textarea>
```

#### ✅ Recommended

```html
<p-textarea name="comment" label="Comment" aria="{'aria-label': 'Accessible name', 'aria-description': 'Additional context'}"></p-textarea>
```

### Placeholder-only instructions for open text input

#### ❌ Anti-pattern

```html
<p-textarea name="feedback" placeholder="Tell us what you think"></p-textarea>
```

#### ✅ Recommended

```html
<p-textarea name="feedback" label="Your feedback" description="Describe what worked well and what we should improve (min. 20 characters)."></p-textarea>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-textarea name="feedback" hide-label="true"></p-textarea>
```

#### ✅ Recommended

```html
<p-textarea name="feedback" hide-label="true" label="Your feedback"></p-textarea>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-textarea name="feedback" label="Your feedback" aria-invalid="true" message="Too short"></p-textarea>
```

#### ✅ Recommended

```html
<p-textarea name="feedback" label="Your feedback" state="error" message="Enter at least 20 characters so we can understand your feedback."></p-textarea>
```
