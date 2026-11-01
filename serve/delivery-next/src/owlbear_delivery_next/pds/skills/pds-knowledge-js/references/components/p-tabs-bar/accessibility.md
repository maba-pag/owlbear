# p-tabs-bar accessibility integration examples

## Integration examples

### Tabbed interface without tablist label

#### ❌ Anti-pattern

```html
<p-tabs-bar active-tab-index="0">
  <button type="button" id="tab-0" aria-controls="panel-0">
    Overview
  </button>
  <button type="button" id="tab-1" aria-controls="panel-1">
    Equipment
  </button>
</p-tabs-bar>
```

#### ✅ Recommended

```html
<p-tabs-bar aria="{'aria-label': 'Porsche 911 configuration sections'}" active-tab-index="0">
  <button type="button" id="tab-0" aria-controls="panel-0">
    Overview
  </button>
  <button type="button" id="tab-1" aria-controls="panel-1">
    Equipment
  </button>
</p-tabs-bar>
```

### Route navigation without landmark label

#### ❌ Anti-pattern

```html
<p-tabs-bar>
  <a href="/models/911">
    911
  </a>
  <a href="/models/taycan">
    Taycan
  </a>
</p-tabs-bar>
```

#### ✅ Recommended

```html
<nav aria-label="Porsche model range">
  <p-tabs-bar>
    <a href="/models/911" aria-current="page">
      911
    </a>
    <a href="/models/taycan">
      Taycan
    </a>
  </p-tabs-bar>
</nav>
```
