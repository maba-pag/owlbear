// Minimal ESLint flat config for Cockpit web (React 19 + TypeScript 5 + Vite 6).
// Required for MegaLinter's TYPESCRIPT_ES linter to run.
// Extend with React/JSX rules (eslint-plugin-react, eslint-plugin-react-hooks)
// when contributor needs justify the additional dev-dep weight.

import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "coverage/**",
      "playwright-report/**",
      "node_modules/**",
      "public/porsche-design-system/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        fetch: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
      },
    },
    rules: {
      // Project-wide overrides intentionally minimal.
      // Add React/Hook rules in a follow-up if/when needed.
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Ban raw PDS custom elements — use React wrappers from
      // @porsche-design-system/components-react instead.
      // Raw custom elements + React 19 SyntheticEvent = broken event.detail.
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXOpeningElement[name.name='p-select']",
          message: "Use <PSelect> from @porsche-design-system/components-react instead of raw <p-select>.",
        },
        {
          selector: "JSXOpeningElement[name.name='p-button']",
          message: "Use <PButton> from @porsche-design-system/components-react instead of raw <p-button>.",
        },
        {
          selector: "JSXOpeningElement[name.name='p-input-search']",
          message: "Use <PInputSearch> from @porsche-design-system/components-react instead of raw <p-input-search>.",
        },
        {
          selector: "JSXOpeningElement[name.name='p-input-text']",
          message: "Use <PInputText> from @porsche-design-system/components-react instead of raw <p-input-text>.",
        },
        {
          selector: "JSXOpeningElement[name.name='p-tag']",
          message: "Use <PTag> from @porsche-design-system/components-react instead of raw <p-tag>.",
        },
      ],
    },
  },
  {
    files: ["scripts/**/*.mjs", "e2e/support/**/*.mjs"],
    languageOptions: {
      globals: {
        process: "readonly",
        Buffer: "readonly",
        console: "readonly",
      },
    },
  },
);
