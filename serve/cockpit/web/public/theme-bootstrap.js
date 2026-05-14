(function () {
  var THEME_STORAGE_KEY = 'owlbear-theme'
  var stored = window.localStorage.getItem(THEME_STORAGE_KEY)
  var isValid = stored === 'dark' || stored === 'light'
  var resolved = isValid
    ? stored
    : window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'

  window.document.documentElement.dataset.theme = resolved
})()
