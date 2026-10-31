# p-table accessibility integration examples

## Integration examples

### Data table without caption

#### ❌ Anti-pattern

```html
<p-table>
  <p-table-head>
    ...
  </p-table-head>
  <p-table-body>
    ...
  </p-table-body>
</p-table>
```

#### ✅ Recommended

```html
<p-table caption="Available Porsche 911 models and starting prices">
  <p-table-head>
    ...
  </p-table-head>
  <p-table-body>
    ...
  </p-table-body>
</p-table>
```

### Column with hidden label

#### ❌ Anti-pattern

```html
<p-table-head-cell hide-label="true"></p-table-head-cell>
```

#### ✅ Recommended

```html
<p-table-head-cell hide-label="true">
  Model
</p-table-head-cell>
```
