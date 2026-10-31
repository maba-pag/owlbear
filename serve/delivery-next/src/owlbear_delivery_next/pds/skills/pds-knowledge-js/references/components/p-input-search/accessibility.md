# p-input-search accessibility integration examples

## Integration examples

### Placeholder used as the only label

#### ❌ Anti-pattern

```html
<p-input-search name="search" placeholder="Search"></p-input-search>
```

#### ✅ Recommended

```html
<p-input-search name="search" label="Search vehicles" description="Search by model name or VIN."></p-input-search>
```

### ARIA on component host vs aria prop

#### ❌ Anti-pattern

```html
<p-input-search name="search" label="Search vehicles" role="combobox" aria-expanded="false" aria-haspopup="listbox"></p-input-search>
```

#### ✅ Recommended

```html
<p-input-search name="search" label="Search vehicles" aria="{'role': 'combobox', 'aria-expanded': 'false', 'aria-haspopup': 'listbox'}"></p-input-search>
```

### Hidden label without accessible name

#### ❌ Anti-pattern

```html
<p-input-search name="search" hide-label="true"></p-input-search>
```

#### ✅ Recommended

```html
<p-input-search name="search" hide-label="true" label="Search vehicles"></p-input-search>
```

### Validation feedback via state and message API

#### ❌ Anti-pattern

```html
<p-input-search name="search" label="Search vehicles" aria-invalid="true" message="Invalid"></p-input-search>
```

#### ✅ Recommended

```html
<p-input-search name="search" label="Search vehicles" state="error" message="Enter at least 3 characters to search."></p-input-search>
```
