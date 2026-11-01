# p-pagination accessibility integration examples

## Integration examples

### Default English labels on a localized page

#### ❌ Anti-pattern

```html
<html lang="de_DE">
  ...
  <p-pagination total-items-count="120" items-per-page="10" active-page="1"></p-pagination>
</html>
```

#### ✅ Recommended

```html
<html lang="de_DE">
  ...
  <p-pagination total-items-count="120" items-per-page="10" active-page="1" intl="{'root': 'Seitennavigation', 'prev': 'Vorherige Seite', 'next': 'Nächste Seite', 'page': 'Seite'}"></p-pagination>
</html>
```
