# p-carousel accessibility integration examples

## Integration examples

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-carousel aria-label="Slider">
  <!-- slides -->
</p-carousel>
```

#### ✅ Recommended

```html
<p-carousel aria="{'aria-label': 'Featured Porsche models'}">
  <!-- slides -->
</p-carousel>
```

### Carousel without skip path for keyboard users

#### ❌ Anti-pattern

```html
<p-carousel>
  <!-- many slides (>6 items) -->
</p-carousel>
```

#### ✅ Recommended

```html
<p-carousel skip-link-target="#after-carousel" aria="{'aria-label': 'Highlights'}">
  <!-- many slides (>6 items) -->
</p-carousel>

<p-heading tag="h2" id="after-carousel">
  Next section
</p-heading>
```

### Vague carousel label

#### ❌ Anti-pattern

```html
<p-carousel aria="{'aria-label': 'Slider'}">
  <!-- slides -->
</p-carousel>
```

#### ✅ Recommended

```html
<p-carousel aria="{'aria-label': 'Featured Porsche models'}">
  <!-- slides -->
</p-carousel>
```
