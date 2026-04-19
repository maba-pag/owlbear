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
      "*.config.js",
      "*.config.ts",
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
    },
  },
);
