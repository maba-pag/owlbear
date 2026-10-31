# Deprecated API

Every deprecated Porsche Design System API in `4.10.1`, indexed by what is deprecated rather than by which component owns it. Use it to check an existing codebase; use the component and styling references to build with the current API.

Deprecated APIs still work in this version. Each will be removed in the next major release, so usage is a compatibility risk rather than a present-day defect — except where a message says an API has no effect anymore, which means the behavior is already gone and only the declaration remains.

Every entry is derived from the installed package, never hand-authored, and every source is listed below including those that currently carry no deprecations — so "nothing found" is distinguishable from "not checked".

**Rule ID** is each entry's stable identifier. Copy it verbatim when reporting — never reconstruct it — and read its first segment as the usage kind. It is what makes findings comparable across runs and releases, so an invented one silently breaks that comparison.

## Coverage

| Source | Derived from | Deprecations |
| --- | --- | --- |
| Components | the component API exposed by `@porsche-design-system/components-js` | 229 |
| SCSS | the SCSS API exposed by `@porsche-design-system/components-js/scss` | 122 |
| Emotion | the Emotion API exposed by `@porsche-design-system/components-js/emotion` | 120 |
| vanilla-extract | the vanilla-extract API exposed by `@porsche-design-system/components-js/vanilla-extract` | 120 |
| Tailwind CSS | the Tailwind theme exposed by `@porsche-design-system/components-js/tailwindcss` | 9 |
| Tokens | the design-token API exposed by `@porsche-design-system/components-js/tokens` | none |
| Icons | the `p-icon` `name` values exposed by `@porsche-design-system/components-js` | none |
| Stylesheets | the global CSS exposed by `@porsche-design-system/components-js/index.css`, including `@porsche-design-system/components-js/variables.css` and `@porsche-design-system/components-js/color-scheme.css` | none |

## How to locate deprecated usage

Use the rule ID for context: its first segment is the usage kind, followed by the component or source, the owning prop where applicable, and finally the deprecated identifier.

| Kind | How to locate it |
| --- | --- |
| `component` | Inspect PDS custom-element tags and calls that create the named element. |
| `prop` | Inspect attributes, property assignments and `setAttribute` calls on anchored PDS elements and wrappers. |
| `propValue` | Resolve values assigned through attributes, properties and `setAttribute`, including constants, wrappers and responsive objects. |
| `event` | Inspect event listeners registered for the named PDS event. |
| `slot` | Inspect `slot` attributes and default content placed inside the owning PDS element. |
| `cssCustomProperty` | Inspect declarations and uses of the exact custom property, anchored to its component, stylesheet or imported theme. |
| `cssClass` | Inspect the exact class in usage anchored to the PDS stylesheet or utility source. |
| `scssVariable` | Follow PDS Sass roots through namespaces, aliases and configured global imports to the exact variable. |
| `scssMixin` | Follow PDS Sass roots through namespaces and aliases to inclusions of the exact mixin. |
| `jsExport` | Follow imports from the stated package entry point through aliases, namespace access and re-exports. |

## Components

Derived from the component API exposed by `@porsche-design-system/components-js`.

| Rule ID | Deprecated | Replacement | Note | Reference |
| --- | --- | --- | --- | --- |
| `component/p-display` | `p-display` | `p-heading` | since v4.0.0, will be removed with next major release. Please use `p-heading` instead. | [references/components/p-display/p-display.md](references/components/p-display/p-display.md) |
| `prop/p-accordion/heading` | `heading` | `summary slot` | Will be removed in the next major release. Use the `summary` slot instead. Sets the heading text within the summary section. | [references/components/p-accordion/p-accordion.md](references/components/p-accordion/p-accordion.md) |
| `prop/p-accordion/headingTag` | `headingTag` | `summary slot` | Will be removed in the next major release. Use the `summary` slot instead. Sets the heading tag for proper semantic structure within the page. | [references/components/p-accordion/p-accordion.md](references/components/p-accordion/p-accordion.md) |
| `prop/p-accordion/size` | `size` | `summary slot` | Will be removed in the next major release. Use the `summary` slot instead. Controls the heading size in the summary section (only applies when using the `heading` prop or `heading` slot). | [references/components/p-accordion/p-accordion.md](references/components/p-accordion/p-accordion.md) |
| `prop/p-scroller/alignScrollIndicator` | `alignScrollIndicator` | — | since v4.0.0, will be removed with next major release, has no effect anymore. | [references/components/p-scroller/p-scroller.md](references/components/p-scroller/p-scroller.md) |
| `prop/p-scroller/scrollToPosition` | `scrollToPosition` | `scrollIntoView()` | since v4.0.0, use native `scrollIntoView()` on the slotted element itself. | [references/components/p-scroller/p-scroller.md](references/components/p-scroller/p-scroller.md) |
| `prop/p-tabs-bar/weight` | `weight` | — | Will be removed in the next major release. Has no effect anymore. | [references/components/p-tabs-bar/p-tabs-bar.md](references/components/p-tabs-bar/p-tabs-bar.md) |
| `prop/p-tabs/weight` | `weight` | — | Will be removed in the next major release. Has no effect anymore. | [references/components/p-tabs/p-tabs.md](references/components/p-tabs/p-tabs.md) |
| `propValue/p-ai-tag/locale/ar_BH` | `ar_BH` | `ar-BH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ar_KW` | `ar_KW` | `ar-KW` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ar_QA` | `ar_QA` | `ar-QA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ar_SA` | `ar_SA` | `ar-SA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/az_AZ` | `az_AZ` | `az-AZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/bg_BG` | `bg_BG` | `bg-BG` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/bs_BA` | `bs_BA` | `bs-BA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/cs_CZ` | `cs_CZ` | `cs-CZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/cs_SK` | `cs_SK` | `cs-SK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/da_DK` | `da_DK` | `da-DK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/de_AT` | `de_AT` | `de-AT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/de_CH` | `de_CH` | `de-CH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/de_DE` | `de_DE` | `de-DE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/de_LI` | `de_LI` | `de-LI` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/de_LU` | `de_LU` | `de-LU` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/el_GR` | `el_GR` | `el-GR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_AE` | `en_AE` | `en-AE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_AE_x_abu_dhabi` | `en_AE_x_abu_dhabi` | `en-AE-x-abu-dhabi` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_AE_x_abudhabi` | `en_AE_x_abudhabi` | `en-AE-x-abudhabi` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_AE_x_dubai` | `en_AE_x_dubai` | `en-AE-x-dubai` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_AL` | `en_AL` | `en-AL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_AU` | `en_AU` | `en-AU` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_BA` | `en_BA` | `en-BA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_BG` | `en_BG` | `en-BG` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_BH` | `en_BH` | `en-BH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_BN` | `en_BN` | `en-BN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_CA` | `en_CA` | `en-CA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_CH` | `en_CH` | `en-CH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_CN` | `en_CN` | `en-CN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_CW` | `en_CW` | `en-CW` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_CY` | `en_CY` | `en-CY` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_CZ` | `en_CZ` | `en-CZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_DK` | `en_DK` | `en-DK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_EE` | `en_EE` | `en-EE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_EG` | `en_EG` | `en-EG` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_FI` | `en_FI` | `en-FI` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_GB` | `en_GB` | `en-GB` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_GE` | `en_GE` | `en-GE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_GH` | `en_GH` | `en-GH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_GI` | `en_GI` | `en-GI` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_GR` | `en_GR` | `en-GR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_HK` | `en_HK` | `en-HK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_HR` | `en_HR` | `en-HR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_HT` | `en_HT` | `en-HT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_ID` | `en_ID` | `en-ID` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_IE` | `en_IE` | `en-IE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_IL` | `en_IL` | `en-IL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_IN` | `en_IN` | `en-IN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_IS` | `en_IS` | `en-IS` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_JM` | `en_JM` | `en-JM` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_JO` | `en_JO` | `en-JO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_KH` | `en_KH` | `en-KH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_KR` | `en_KR` | `en-KR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_KW` | `en_KW` | `en-KW` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_KZ` | `en_KZ` | `en-KZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_LB` | `en_LB` | `en-LB` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_LK` | `en_LK` | `en-LK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_LT` | `en_LT` | `en-LT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_LV` | `en_LV` | `en-LV` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_ME` | `en_ME` | `en-ME` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_MK` | `en_MK` | `en-MK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_MN` | `en_MN` | `en-MN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_MT` | `en_MT` | `en-MT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_MU` | `en_MU` | `en-MU` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_MY` | `en_MY` | `en-MY` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_NC` | `en_NC` | `en-NC` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_NL` | `en_NL` | `en-NL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_NO` | `en_NO` | `en-NO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_NZ` | `en_NZ` | `en-NZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_OM` | `en_OM` | `en-OM` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_PF` | `en_PF` | `en-PF` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_PH` | `en_PH` | `en-PH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_PL` | `en_PL` | `en-PL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_PR` | `en_PR` | `en-PR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_QA` | `en_QA` | `en-QA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_RO` | `en_RO` | `en-RO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_RS` | `en_RS` | `en-RS` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_SA` | `en_SA` | `en-SA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_SE` | `en_SE` | `en-SE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_SG` | `en_SG` | `en-SG` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_SI` | `en_SI` | `en-SI` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_SK` | `en_SK` | `en-SK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_TH` | `en_TH` | `en-TH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_TR` | `en_TR` | `en-TR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_TT` | `en_TT` | `en-TT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_TW` | `en_TW` | `en-TW` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_UA` | `en_UA` | `en-UA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_US` | `en_US` | `en-US` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_VE` | `en_VE` | `en-VE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_VN` | `en_VN` | `en-VN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_XA` | `en_XA` | `en-XA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_YE` | `en_YE` | `en-YE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/en_ZA` | `en_ZA` | `en-ZA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_AD` | `es_AD` | `es-AD` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_AR` | `es_AR` | `es-AR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_BO` | `es_BO` | `es-BO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_CL` | `es_CL` | `es-CL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_CO` | `es_CO` | `es-CO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_CR` | `es_CR` | `es-CR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_DO` | `es_DO` | `es-DO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_EC` | `es_EC` | `es-EC` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_ES` | `es_ES` | `es-ES` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_GT` | `es_GT` | `es-GT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_HN` | `es_HN` | `es-HN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_MX` | `es_MX` | `es-MX` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_PA` | `es_PA` | `es-PA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_PE` | `es_PE` | `es-PE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_PR` | `es_PR` | `es-PR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_PY` | `es_PY` | `es-PY` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_SV` | `es_SV` | `es-SV` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_TT` | `es_TT` | `es-TT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_UY` | `es_UY` | `es-UY` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/es_VE` | `es_VE` | `es-VE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/et_EE` | `et_EE` | `et-EE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fi_FI` | `fi_FI` | `fi-FI` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_BE` | `fr_BE` | `fr-BE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_CA` | `fr_CA` | `fr-CA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_CH` | `fr_CH` | `fr-CH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_DZ` | `fr_DZ` | `fr-DZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_FR` | `fr_FR` | `fr-FR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_GP` | `fr_GP` | `fr-GP` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_LI` | `fr_LI` | `fr-LI` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_LU` | `fr_LU` | `fr-LU` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_MA` | `fr_MA` | `fr-MA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_MC` | `fr_MC` | `fr-MC` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_MQ` | `fr_MQ` | `fr-MQ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_MU` | `fr_MU` | `fr-MU` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_NC` | `fr_NC` | `fr-NC` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_PF` | `fr_PF` | `fr-PF` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_RE` | `fr_RE` | `fr-RE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/fr_TN` | `fr_TN` | `fr-TN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/he_IL` | `he_IL` | `he-IL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/hr_HR` | `hr_HR` | `hr-HR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/hu_HU` | `hu_HU` | `hu-HU` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/hy_AM` | `hy_AM` | `hy-AM` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/is_IS` | `is_IS` | `is-IS` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/it_CH` | `it_CH` | `it-CH` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/it_IT` | `it_IT` | `it-IT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ja_JP` | `ja_JP` | `ja-JP` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ka_GE` | `ka_GE` | `ka-GE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ko_KR` | `ko_KR` | `ko-KR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/lt_LT` | `lt_LT` | `lt-LT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/lv_LV` | `lv_LV` | `lv-LV` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/me_ME` | `me_ME` | `me-ME` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/mk_MK` | `mk_MK` | `mk-MK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/mt_MT` | `mt_MT` | `mt-MT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/nb_NO` | `nb_NO` | `nb-NO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/nl_BE` | `nl_BE` | `nl-BE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/nl_NL` | `nl_NL` | `nl-NL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/no_NO` | `no_NO` | `no-NO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/pl_PL` | `pl_PL` | `pl-PL` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/pt_BR` | `pt_BR` | `pt-BR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/pt_PT` | `pt_PT` | `pt-PT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ro_MD` | `ro_MD` | `ro-MD` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ro_RO` | `ro_RO` | `ro-RO` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_AZ` | `ru_AZ` | `ru-AZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_BY` | `ru_BY` | `ru-BY` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_CY` | `ru_CY` | `ru-CY` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_EE` | `ru_EE` | `ru-EE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_KZ` | `ru_KZ` | `ru-KZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_LT` | `ru_LT` | `ru-LT` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_LV` | `ru_LV` | `ru-LV` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_RU` | `ru_RU` | `ru-RU` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_UK` | `ru_UK` | `ru-UK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/ru_UZ` | `ru_UZ` | `ru-UZ` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/sk_SK` | `sk_SK` | `sk-SK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/sl_SI` | `sl_SI` | `sl-SI` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/sr_ME` | `sr_ME` | `sr-ME` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/sr_RS` | `sr_RS` | `sr-RS` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/sv_SE` | `sv_SE` | `sv-SE` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/tr_TR` | `tr_TR` | `tr-TR` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/uk_UA` | `uk_UA` | `uk-UA` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/zh_CN` | `zh_CN` | `zh-CN` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/zh_HK` | `zh_HK` | `zh-HK` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-ai-tag/locale/zh_TW` | `zh_TW` | `zh-TW` | — | [references/components/p-ai-tag/p-ai-tag.md](references/components/p-ai-tag/p-ai-tag.md) |
| `propValue/p-button-pure/size/large` | `large` | `lg` | — | [references/components/p-button-pure/p-button-pure.md](references/components/p-button-pure/p-button-pure.md) |
| `propValue/p-button-pure/size/medium` | `medium` | `md` | — | [references/components/p-button-pure/p-button-pure.md](references/components/p-button-pure/p-button-pure.md) |
| `propValue/p-button-pure/size/small` | `small` | `sm` | — | [references/components/p-button-pure/p-button-pure.md](references/components/p-button-pure/p-button-pure.md) |
| `propValue/p-button-pure/size/x-large` | `x-large` | `xl` | — | [references/components/p-button-pure/p-button-pure.md](references/components/p-button-pure/p-button-pure.md) |
| `propValue/p-button-pure/size/x-small` | `x-small` | `xs` | — | [references/components/p-button-pure/p-button-pure.md](references/components/p-button-pure/p-button-pure.md) |
| `propValue/p-button-pure/size/xx-small` | `xx-small` | `2xs` | — | [references/components/p-button-pure/p-button-pure.md](references/components/p-button-pure/p-button-pure.md) |
| `propValue/p-flag/size/large` | `large` | `lg` | — | [references/components/p-flag/p-flag.md](references/components/p-flag/p-flag.md) |
| `propValue/p-flag/size/medium` | `medium` | `md` | — | [references/components/p-flag/p-flag.md](references/components/p-flag/p-flag.md) |
| `propValue/p-flag/size/small` | `small` | `sm` | — | [references/components/p-flag/p-flag.md](references/components/p-flag/p-flag.md) |
| `propValue/p-flag/size/x-large` | `x-large` | `xl` | — | [references/components/p-flag/p-flag.md](references/components/p-flag/p-flag.md) |
| `propValue/p-flag/size/x-small` | `x-small` | `xs` | — | [references/components/p-flag/p-flag.md](references/components/p-flag/p-flag.md) |
| `propValue/p-flag/size/xx-large` | `xx-large` | `2xl` | — | [references/components/p-flag/p-flag.md](references/components/p-flag/p-flag.md) |
| `propValue/p-flag/size/xx-small` | `xx-small` | `2xs` | — | [references/components/p-flag/p-flag.md](references/components/p-flag/p-flag.md) |
| `propValue/p-heading/size/large` | `large` | `lg` | — | [references/components/p-heading/p-heading.md](references/components/p-heading/p-heading.md) |
| `propValue/p-heading/size/medium` | `medium` | `md` | — | [references/components/p-heading/p-heading.md](references/components/p-heading/p-heading.md) |
| `propValue/p-heading/size/small` | `small` | `sm` | — | [references/components/p-heading/p-heading.md](references/components/p-heading/p-heading.md) |
| `propValue/p-heading/size/x-large` | `x-large` | `xl` | — | [references/components/p-heading/p-heading.md](references/components/p-heading/p-heading.md) |
| `propValue/p-heading/size/xx-large` | `xx-large` | `2xl` | — | [references/components/p-heading/p-heading.md](references/components/p-heading/p-heading.md) |
| `propValue/p-heading/weight/regular` | `regular` | `normal` | — | [references/components/p-heading/p-heading.md](references/components/p-heading/p-heading.md) |
| `propValue/p-heading/weight/semi-bold` | `semi-bold` | `semibold` | — | [references/components/p-heading/p-heading.md](references/components/p-heading/p-heading.md) |
| `propValue/p-icon/size/large` | `large` | `lg` | — | [references/components/p-icon/p-icon.md](references/components/p-icon/p-icon.md) |
| `propValue/p-icon/size/medium` | `medium` | `md` | — | [references/components/p-icon/p-icon.md](references/components/p-icon/p-icon.md) |
| `propValue/p-icon/size/small` | `small` | `sm` | — | [references/components/p-icon/p-icon.md](references/components/p-icon/p-icon.md) |
| `propValue/p-icon/size/x-large` | `x-large` | `xl` | — | [references/components/p-icon/p-icon.md](references/components/p-icon/p-icon.md) |
| `propValue/p-icon/size/x-small` | `x-small` | `xs` | — | [references/components/p-icon/p-icon.md](references/components/p-icon/p-icon.md) |
| `propValue/p-icon/size/xx-large` | `xx-large` | `2xl` | — | [references/components/p-icon/p-icon.md](references/components/p-icon/p-icon.md) |
| `propValue/p-icon/size/xx-small` | `xx-small` | `2xs` | — | [references/components/p-icon/p-icon.md](references/components/p-icon/p-icon.md) |
| `propValue/p-link-pure/size/large` | `large` | `lg` | — | [references/components/p-link-pure/p-link-pure.md](references/components/p-link-pure/p-link-pure.md) |
| `propValue/p-link-pure/size/medium` | `medium` | `md` | — | [references/components/p-link-pure/p-link-pure.md](references/components/p-link-pure/p-link-pure.md) |
| `propValue/p-link-pure/size/small` | `small` | `sm` | — | [references/components/p-link-pure/p-link-pure.md](references/components/p-link-pure/p-link-pure.md) |
| `propValue/p-link-pure/size/x-large` | `x-large` | `xl` | — | [references/components/p-link-pure/p-link-pure.md](references/components/p-link-pure/p-link-pure.md) |
| `propValue/p-link-pure/size/x-small` | `x-small` | `xs` | — | [references/components/p-link-pure/p-link-pure.md](references/components/p-link-pure/p-link-pure.md) |
| `propValue/p-link-pure/size/xx-small` | `xx-small` | `2xs` | — | [references/components/p-link-pure/p-link-pure.md](references/components/p-link-pure/p-link-pure.md) |
| `propValue/p-spinner/size/large` | `large` | `lg` | — | [references/components/p-spinner/p-spinner.md](references/components/p-spinner/p-spinner.md) |
| `propValue/p-spinner/size/medium` | `medium` | `md` | — | [references/components/p-spinner/p-spinner.md](references/components/p-spinner/p-spinner.md) |
| `propValue/p-spinner/size/small` | `small` | `sm` | — | [references/components/p-spinner/p-spinner.md](references/components/p-spinner/p-spinner.md) |
| `propValue/p-text/size/large` | `large` | `lg` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `propValue/p-text/size/medium` | `medium` | `md` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `propValue/p-text/size/small` | `small` | `sm` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `propValue/p-text/size/x-large` | `x-large` | `xl` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `propValue/p-text/size/x-small` | `x-small` | `xs` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `propValue/p-text/size/xx-small` | `xx-small` | `2xs` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `propValue/p-text/weight/regular` | `regular` | `normal` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `propValue/p-text/weight/semi-bold` | `semi-bold` | `semibold` | — | [references/components/p-text/p-text.md](references/components/p-text/p-text.md) |
| `slot/p-accordion/heading` | `heading` | — | Content for the accordion's heading section. Clicking toggles the accordion open and closed. | [references/components/p-accordion/p-accordion.md](references/components/p-accordion/p-accordion.md) |
| `slot/p-banner/description` | `description` | `default slot` | Deprecated: Use the default slot instead. | [references/components/p-banner/p-banner.md](references/components/p-banner/p-banner.md) |

## SCSS

Derived from the SCSS API exposed by `@porsche-design-system/components-js/scss`.

| Rule ID | Deprecated | Replacement | Note | Reference |
| --- | --- | --- | --- | --- |
| `scssVariable/scss/$pds-border-radius-small` | `$pds-border-radius-small` | `$radius-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-border-radius-medium` | `$pds-border-radius-medium` | `$radius-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-border-radius-large` | `$pds-border-radius-large` | `$radius-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-border-width-base` | `$pds-border-width-base` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-border-width-thin` | `$pds-border-width-thin` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-frosted-glass()` | `pds-frosted-glass()` | `$blur-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-breakpoint-base` | `$pds-breakpoint-base` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-breakpoint-xs` | `$pds-breakpoint-xs` | `$breakpoint-xs` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-breakpoint-s` | `$pds-breakpoint-s` | `$breakpoint-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-breakpoint-m` | `$pds-breakpoint-m` | `$breakpoint-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-breakpoint-l` | `$pds-breakpoint-l` | `$breakpoint-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-breakpoint-xl` | `$pds-breakpoint-xl` | `$breakpoint-xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-breakpoint-xxl` | `$pds-breakpoint-xxl` | `$breakpoint-2xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-primary` | `$pds-theme-light-primary` | `$color-primary` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-background-base` | `$pds-theme-light-background-base` | `$color-canvas` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-background-surface` | `$pds-theme-light-background-surface` | `$color-surface` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-background-shading` | `$pds-theme-light-background-shading` | `$color-backdrop` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-background-frosted` | `$pds-theme-light-background-frosted` | `$color-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-contrast-low` | `$pds-theme-light-contrast-low` | `$color-contrast-low` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-contrast-medium` | `$pds-theme-light-contrast-medium` | `$color-contrast-medium` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-contrast-high` | `$pds-theme-light-contrast-high` | `$color-contrast-high` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-success` | `$pds-theme-light-notification-success` | `$color-success` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-success-soft` | `$pds-theme-light-notification-success-soft` | `$color-success-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-warning` | `$pds-theme-light-notification-warning` | `$color-warning` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-warning-soft` | `$pds-theme-light-notification-warning-soft` | `$color-warning-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-error` | `$pds-theme-light-notification-error` | `$color-error` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-error-soft` | `$pds-theme-light-notification-error-soft` | `$color-error-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-info` | `$pds-theme-light-notification-info` | `$color-info` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-notification-info-soft` | `$pds-theme-light-notification-info-soft` | `$color-info-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-state-hover` | `$pds-theme-light-state-hover` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-state-active` | `$pds-theme-light-state-active` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-state-focus` | `$pds-theme-light-state-focus` | `$color-focus` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-light-state-disabled` | `$pds-theme-light-state-disabled` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-primary` | `$pds-theme-dark-primary` | `$color-primary` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-background-base` | `$pds-theme-dark-background-base` | `$color-canvas` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-background-surface` | `$pds-theme-dark-background-surface` | `$color-surface` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-background-shading` | `$pds-theme-dark-background-shading` | `$color-backdrop` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-background-frosted` | `$pds-theme-dark-background-frosted` | `$color-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-contrast-low` | `$pds-theme-dark-contrast-low` | `$color-contrast-low` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-contrast-medium` | `$pds-theme-dark-contrast-medium` | `$color-contrast-medium` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-contrast-high` | `$pds-theme-dark-contrast-high` | `$color-contrast-high` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-success` | `$pds-theme-dark-notification-success` | `$color-success` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-success-soft` | `$pds-theme-dark-notification-success-soft` | `$color-success-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-warning` | `$pds-theme-dark-notification-warning` | `$color-warning` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-warning-soft` | `$pds-theme-dark-notification-warning-soft` | `$color-warning-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-error` | `$pds-theme-dark-notification-error` | `$color-error` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-error-soft` | `$pds-theme-dark-notification-error-soft` | `$color-error-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-info` | `$pds-theme-dark-notification-info` | `$color-info` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-notification-info-soft` | `$pds-theme-dark-notification-info-soft` | `$color-info-frosted` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-state-hover` | `$pds-theme-dark-state-hover` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-state-active` | `$pds-theme-dark-state-active` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-state-focus` | `$pds-theme-dark-state-focus` | `$color-focus` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-theme-dark-state-disabled` | `$pds-theme-dark-state-disabled` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-family` | `$pds-font-family` | `$font-porsche-next` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-weight-regular` | `$pds-font-weight-regular` | `$font-weight-normal` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-weight-semi-bold` | `$pds-font-weight-semi-bold` | `$font-weight-semibold` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-weight-bold` | `$pds-font-weight-bold` | `$font-weight-bold` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-line-height` | `$pds-font-line-height` | `$leading-normal` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-text-xx-small` | `$pds-font-size-text-xx-small` | `$typescale-2xs` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-text-x-small` | `$pds-font-size-text-x-small` | `$typescale-xs` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-text-small` | `$pds-font-size-text-small` | `$typescale-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-text-medium` | `$pds-font-size-text-medium` | `$typescale-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-text-large` | `$pds-font-size-text-large` | `$typescale-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-text-x-large` | `$pds-font-size-text-x-large` | `$typescale-xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-heading-small` | `$pds-font-size-heading-small` | `$typescale-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-heading-medium` | `$pds-font-size-heading-medium` | `$typescale-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-heading-large` | `$pds-font-size-heading-large` | `$typescale-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-heading-x-large` | `$pds-font-size-heading-x-large` | `$typescale-xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-heading-xx-large` | `$pds-font-size-heading-xx-large` | `$typescale-2xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-display-small` | `$pds-font-size-display-small` | `$typescale-3xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-display-medium` | `$pds-font-size-display-medium` | `$typescale-4xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-size-display-large` | `$pds-font-size-display-large` | `$typescale-5xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-hyphenation-style-overflow-wrap` | `$pds-font-hyphenation-style-overflow-wrap` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-hyphenation-style-hyphens` | `$pds-font-hyphenation-style-hyphens` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-style-normal` | `$pds-font-style-normal` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-style-italic` | `$pds-font-style-italic` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-font-variant` | `$pds-font-variant` | — | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-drop-shadow-low()` | `pds-drop-shadow-low()` | `$shadow-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-drop-shadow-medium()` | `pds-drop-shadow-medium()` | `$shadow-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-drop-shadow-high()` | `pds-drop-shadow-high()` | `$shadow-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-fluid-x-small` | `$pds-spacing-fluid-x-small` | `$spacing-fluid-xs` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-fluid-small` | `$pds-spacing-fluid-small` | `$spacing-fluid-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-fluid-medium` | `$pds-spacing-fluid-medium` | `$spacing-fluid-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-fluid-large` | `$pds-spacing-fluid-large` | `$spacing-fluid-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-fluid-x-large` | `$pds-spacing-fluid-x-large` | `$spacing-fluid-xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-fluid-xx-large` | `$pds-spacing-fluid-xx-large` | `$spacing-fluid-2xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-static-x-small` | `$pds-spacing-static-x-small` | `$spacing-static-xs` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-static-small` | `$pds-spacing-static-small` | `$spacing-static-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-static-medium` | `$pds-spacing-static-medium` | `$spacing-static-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-static-large` | `$pds-spacing-static-large` | `$spacing-static-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-static-x-large` | `$pds-spacing-static-x-large` | `$spacing-static-xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-spacing-static-xx-large` | `$pds-spacing-static-xx-large` | `$spacing-static-2xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-motion-duration-short` | `$pds-motion-duration-short` | `$duration-sm` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-motion-duration-moderate` | `$pds-motion-duration-moderate` | `$duration-md` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-motion-duration-long` | `$pds-motion-duration-long` | `$duration-lg` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-motion-duration-very-long` | `$pds-motion-duration-very-long` | `$duration-xl` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-motion-easing-base` | `$pds-motion-easing-base` | `$ease-in-out` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-motion-easing-in` | `$pds-motion-easing-in` | `$ease-in` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssVariable/scss/$pds-motion-easing-out` | `$pds-motion-easing-out` | `$ease-out` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-gradient-to-bottom()` | `pds-gradient-to-bottom()` | `$gradient-stops-fade-dark` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-gradient-to-left()` | `pds-gradient-to-left()` | `$gradient-stops-fade-dark` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-gradient-to-right()` | `pds-gradient-to-right()` | `$gradient-stops-fade-dark` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-gradient-to-top()` | `pds-gradient-to-top()` | `$gradient-stops-fade-dark` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-heading-xx-large()` | `pds-heading-xx-large()` | `prose-heading-2xl()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-heading-x-large()` | `pds-heading-x-large()` | `prose-heading-xl()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-heading-large()` | `pds-heading-large()` | `prose-heading-lg()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-heading-medium()` | `pds-heading-medium()` | `prose-heading-md()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-heading-small()` | `pds-heading-small()` | `prose-heading-sm()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-text-x-large()` | `pds-text-x-large()` | `prose-text-xl()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-text-large()` | `pds-text-large()` | `prose-text-lg()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-text-medium()` | `pds-text-medium()` | `prose-text-md()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-text-small()` | `pds-text-small()` | `prose-text-sm()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-text-x-small()` | `pds-text-x-small()` | `prose-text-xs()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-text-xx-small()` | `pds-text-xx-small()` | `prose-text-2xs()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-display-large()` | `pds-display-large()` | `prose-heading-5xl()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-display-medium()` | `pds-display-medium()` | `prose-heading-4xl()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-display-small()` | `pds-display-small()` | `prose-heading-3xl()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-skeleton()` | `pds-skeleton()` | `skeleton()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-focus()` | `pds-focus()` | `focus-visible()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-media-query-min()` | `pds-media-query-min()` | `media-query-min()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-media-query-max()` | `pds-media-query-max()` | `media-query-max()` | — | [references/styles/scss.md](references/styles/scss.md) |
| `scssMixin/scss/pds-media-query-min-max()` | `pds-media-query-min-max()` | `media-query-min-max()` | — | [references/styles/scss.md](references/styles/scss.md) |

## Emotion

Derived from the Emotion API exposed by `@porsche-design-system/components-js/emotion`.

| Rule ID | Deprecated | Replacement | Note | Reference |
| --- | --- | --- | --- | --- |
| `jsExport/emotion/border` | `border` | — | Use variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/borderRadius` | `borderRadius` | — | Use variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/borderRadiusLarge` | `borderRadiusLarge` | `radiusLg` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/borderRadiusMedium` | `borderRadiusMedium` | `radiusMd` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/borderRadiusSmall` | `borderRadiusSmall` | `radiusSm` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/borderWidth` | `borderWidth` | — | Use variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/borderWidthBase` | `borderWidthBase` | — | Use 2px instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/borderWidthThin` | `borderWidthThin` | — | Use 1px instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/frostedGlassStyle` | `frostedGlassStyle` | — | Use backdropFilter: blurFrosted instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/theme` | `theme` | — | Use individual variables instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDark` | `themeDark` | — | Use individual variables instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkBackgroundBase` | `themeDarkBackgroundBase` | `colorCanvas` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkBackgroundFrosted` | `themeDarkBackgroundFrosted` | `colorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkBackgroundShading` | `themeDarkBackgroundShading` | `colorBackdrop` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkBackgroundSurface` | `themeDarkBackgroundSurface` | `colorSurface` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkContrastHigh` | `themeDarkContrastHigh` | `colorContrastHigh` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkContrastLow` | `themeDarkContrastLow` | `colorContrastLow` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkContrastMedium` | `themeDarkContrastMedium` | `colorContrastMedium` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationError` | `themeDarkNotificationError` | `colorError` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationErrorSoft` | `themeDarkNotificationErrorSoft` | `colorErrorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationInfo` | `themeDarkNotificationInfo` | `colorInfo` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationInfoSoft` | `themeDarkNotificationInfoSoft` | `colorInfoFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationSuccess` | `themeDarkNotificationSuccess` | `colorSuccess` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationSuccessSoft` | `themeDarkNotificationSuccessSoft` | `colorSuccessFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationWarning` | `themeDarkNotificationWarning` | `colorWarning` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkNotificationWarningSoft` | `themeDarkNotificationWarningSoft` | `colorWarningFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkPrimary` | `themeDarkPrimary` | `colorPrimary` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkStateActive` | `themeDarkStateActive` | `colorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkStateDisabled` | `themeDarkStateDisabled` | — | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkStateFocus` | `themeDarkStateFocus` | `colorFocus` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeDarkStateHover` | `themeDarkStateHover` | `colorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLight` | `themeLight` | — | Use individual variables instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightBackgroundBase` | `themeLightBackgroundBase` | `colorCanvas` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightBackgroundFrosted` | `themeLightBackgroundFrosted` | `colorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightBackgroundShading` | `themeLightBackgroundShading` | `colorBackdrop` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightBackgroundSurface` | `themeLightBackgroundSurface` | `colorSurface` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightContrastHigh` | `themeLightContrastHigh` | `colorContrastHigh` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightContrastLow` | `themeLightContrastLow` | `colorContrastLow` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightContrastMedium` | `themeLightContrastMedium` | `colorContrastMedium` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationError` | `themeLightNotificationError` | `colorError` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationErrorSoft` | `themeLightNotificationErrorSoft` | `colorErrorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationInfo` | `themeLightNotificationInfo` | `colorInfo` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationInfoSoft` | `themeLightNotificationInfoSoft` | `colorInfoFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationSuccess` | `themeLightNotificationSuccess` | `colorSuccess` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationSuccessSoft` | `themeLightNotificationSuccessSoft` | `colorSuccessFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationWarning` | `themeLightNotificationWarning` | `colorWarning` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightNotificationWarningSoft` | `themeLightNotificationWarningSoft` | `colorWarningFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightPrimary` | `themeLightPrimary` | `colorPrimary` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightStateActive` | `themeLightStateActive` | `colorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightStateDisabled` | `themeLightStateDisabled` | — | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightStateFocus` | `themeLightStateFocus` | `colorFocus` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/themeLightStateHover` | `themeLightStateHover` | `colorFrosted` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontFamily` | `fontFamily` | `fontPorscheNext` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontLineHeight` | `fontLineHeight` | `leadingNormal` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSize` | `fontSize` | — | Use typescale variables instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeDisplay` | `fontSizeDisplay` | — | Use variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeHeading` | `fontSizeHeading` | — | Use typescale variables instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeHeadingLarge` | `fontSizeHeadingLarge` | `typescaleLg` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeHeadingMedium` | `fontSizeHeadingMedium` | `typescaleMd` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeHeadingSmall` | `fontSizeHeadingSmall` | `typescaleSm` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeHeadingXLarge` | `fontSizeHeadingXLarge` | `typescaleXl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeHeadingXXLarge` | `fontSizeHeadingXXLarge` | `typescale2Xl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeText` | `fontSizeText` | — | Use typescale variables instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeTextLarge` | `fontSizeTextLarge` | `typescaleLg` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeTextMedium` | `fontSizeTextMedium` | `typescaleMd` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeTextSmall` | `fontSizeTextSmall` | `typescaleSm` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeTextXLarge` | `fontSizeTextXLarge` | `typescaleXl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeTextXSmall` | `fontSizeTextXSmall` | `typescaleXs` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontSizeTextXXSmall` | `fontSizeTextXXSmall` | `typescale2Xs` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontStyle` | `fontStyle` | — | Use 'normal' \| 'italic' instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontStyleItalic` | `fontStyleItalic` | — | Use 'italic' instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontStyleNormal` | `fontStyleNormal` | — | Use 'normal' instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontVariant` | `fontVariant` | — | Use 'normal' instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontWeight` | `fontWeight` | — | Use variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontWeightRegular` | `fontWeightRegular` | `fontWeightNormal` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/fontWeightSemiBold` | `fontWeightSemiBold` | `fontWeightSemibold` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/dropShadowHighStyle` | `dropShadowHighStyle` | — | Use boxShadow: shadowLg instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/dropShadowLowStyle` | `dropShadowLowStyle` | — | Use boxShadow: shadowSm instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/dropShadowMediumStyle` | `dropShadowMediumStyle` | — | Use boxShadow: shadowMd instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacing` | `spacing` | — | Use spacing variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingFluid` | `spacingFluid` | — | Use spacing variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingFluidLarge` | `spacingFluidLarge` | `spacingFluidLg` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingFluidMedium` | `spacingFluidMedium` | `spacingFluidMd` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingFluidSmall` | `spacingFluidSmall` | `spacingFluidSm` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingFluidXLarge` | `spacingFluidXLarge` | `spacingFluidXl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingFluidXSmall` | `spacingFluidXSmall` | `spacingFluidXs` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingFluidXXLarge` | `spacingFluidXXLarge` | `spacingFluid2Xl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingStatic` | `spacingStatic` | — | Use spacing variables directly instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingStaticLarge` | `spacingStaticLarge` | `spacingStaticLg` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingStaticMedium` | `spacingStaticMedium` | `spacingStaticMd` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingStaticSmall` | `spacingStaticSmall` | `spacingStaticSm` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingStaticXLarge` | `spacingStaticXLarge` | `spacingStaticXl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingStaticXSmall` | `spacingStaticXSmall` | `spacingStaticXs` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/spacingStaticXXLarge` | `spacingStaticXXLarge` | `spacingStatic2Xl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/motionDurationLong` | `motionDurationLong` | `durationLg` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/motionDurationModerate` | `motionDurationModerate` | `durationMd` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/motionDurationShort` | `motionDurationShort` | `durationSm` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/motionDurationVeryLong` | `motionDurationVeryLong` | `durationXl` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/motionEasingBase` | `motionEasingBase` | `easeInOut` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/motionEasingIn` | `motionEasingIn` | `easeIn` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/motionEasingOut` | `motionEasingOut` | `easeOut` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/gradientToBottomStyle` | `gradientToBottomStyle` | — | Use background: `linear-gradient(to bottom, ${gradientStopsFadeDark});` instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/gradientToLeftStyle` | `gradientToLeftStyle` | — | Use background: `linear-gradient(to left, ${gradientStopsFadeDark});` instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/gradientToRightStyle` | `gradientToRightStyle` | — | background: `linear-gradient(to right, ${gradientStopsFadeDark});` instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/gradientToTopStyle` | `gradientToTopStyle` | — | background: `linear-gradient(to top, ${gradientStopsFadeDark});` instead. | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/displaySmallStyle` | `displaySmallStyle` | `proseHeading3XlStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/displayMediumStyle` | `displayMediumStyle` | `proseHeading4XlStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/displayLargeStyle` | `displayLargeStyle` | `proseHeading5XlStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/headingSmallStyle` | `headingSmallStyle` | `proseHeadingSmStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/headingMediumStyle` | `headingMediumStyle` | `proseHeadingMdStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/headingLargeStyle` | `headingLargeStyle` | `proseHeadingLgStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/headingXLargeStyle` | `headingXLargeStyle` | `proseHeadingXlStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/headingXXLargeStyle` | `headingXXLargeStyle` | `proseHeading2XlStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/textXXSmallStyle` | `textXXSmallStyle` | `proseText2XsStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/textXSmallStyle` | `textXSmallStyle` | `proseTextXsStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/textSmallStyle` | `textSmallStyle` | `proseTextSmStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/textMediumStyle` | `textMediumStyle` | `proseTextMdStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/textLargeStyle` | `textLargeStyle` | `proseTextLgStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/textXLargeStyle` | `textXLargeStyle` | `proseTextXlStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |
| `jsExport/emotion/getFocusStyle` | `getFocusStyle` | `getFocusVisibleStyle` | — | [references/styles/emotion.md](references/styles/emotion.md) |

## vanilla-extract

Derived from the vanilla-extract API exposed by `@porsche-design-system/components-js/vanilla-extract`.

| Rule ID | Deprecated | Replacement | Note | Reference |
| --- | --- | --- | --- | --- |
| `jsExport/vanillaExtract/border` | `border` | — | Use variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/borderRadius` | `borderRadius` | — | Use variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/borderRadiusLarge` | `borderRadiusLarge` | `radiusLg` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/borderRadiusMedium` | `borderRadiusMedium` | `radiusMd` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/borderRadiusSmall` | `borderRadiusSmall` | `radiusSm` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/borderWidth` | `borderWidth` | — | Use variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/borderWidthBase` | `borderWidthBase` | — | Use 2px instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/borderWidthThin` | `borderWidthThin` | — | Use 1px instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/frostedGlassStyle` | `frostedGlassStyle` | — | Use backdropFilter: blurFrosted instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/theme` | `theme` | — | Use individual variables instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDark` | `themeDark` | — | Use individual variables instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkBackgroundBase` | `themeDarkBackgroundBase` | `colorCanvas` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkBackgroundFrosted` | `themeDarkBackgroundFrosted` | `colorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkBackgroundShading` | `themeDarkBackgroundShading` | `colorBackdrop` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkBackgroundSurface` | `themeDarkBackgroundSurface` | `colorSurface` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkContrastHigh` | `themeDarkContrastHigh` | `colorContrastHigh` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkContrastLow` | `themeDarkContrastLow` | `colorContrastLow` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkContrastMedium` | `themeDarkContrastMedium` | `colorContrastMedium` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationError` | `themeDarkNotificationError` | `colorError` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationErrorSoft` | `themeDarkNotificationErrorSoft` | `colorErrorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationInfo` | `themeDarkNotificationInfo` | `colorInfo` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationInfoSoft` | `themeDarkNotificationInfoSoft` | `colorInfoFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationSuccess` | `themeDarkNotificationSuccess` | `colorSuccess` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationSuccessSoft` | `themeDarkNotificationSuccessSoft` | `colorSuccessFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationWarning` | `themeDarkNotificationWarning` | `colorWarning` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkNotificationWarningSoft` | `themeDarkNotificationWarningSoft` | `colorWarningFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkPrimary` | `themeDarkPrimary` | `colorPrimary` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkStateActive` | `themeDarkStateActive` | `colorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkStateDisabled` | `themeDarkStateDisabled` | — | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkStateFocus` | `themeDarkStateFocus` | `colorFocus` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeDarkStateHover` | `themeDarkStateHover` | `colorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLight` | `themeLight` | — | Use individual variables instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightBackgroundBase` | `themeLightBackgroundBase` | `colorCanvas` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightBackgroundFrosted` | `themeLightBackgroundFrosted` | `colorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightBackgroundShading` | `themeLightBackgroundShading` | `colorBackdrop` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightBackgroundSurface` | `themeLightBackgroundSurface` | `colorSurface` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightContrastHigh` | `themeLightContrastHigh` | `colorContrastHigh` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightContrastLow` | `themeLightContrastLow` | `colorContrastLow` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightContrastMedium` | `themeLightContrastMedium` | `colorContrastMedium` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationError` | `themeLightNotificationError` | `colorError` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationErrorSoft` | `themeLightNotificationErrorSoft` | `colorErrorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationInfo` | `themeLightNotificationInfo` | `colorInfo` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationInfoSoft` | `themeLightNotificationInfoSoft` | `colorInfoFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationSuccess` | `themeLightNotificationSuccess` | `colorSuccess` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationSuccessSoft` | `themeLightNotificationSuccessSoft` | `colorSuccessFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationWarning` | `themeLightNotificationWarning` | `colorWarning` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightNotificationWarningSoft` | `themeLightNotificationWarningSoft` | `colorWarningFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightPrimary` | `themeLightPrimary` | `colorPrimary` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightStateActive` | `themeLightStateActive` | `colorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightStateDisabled` | `themeLightStateDisabled` | — | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightStateFocus` | `themeLightStateFocus` | `colorFocus` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/themeLightStateHover` | `themeLightStateHover` | `colorFrosted` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontFamily` | `fontFamily` | `fontPorscheNext` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontLineHeight` | `fontLineHeight` | `leadingNormal` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSize` | `fontSize` | — | Use typescale variables instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeDisplay` | `fontSizeDisplay` | — | Use variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeHeading` | `fontSizeHeading` | — | Use typescale variables instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeHeadingLarge` | `fontSizeHeadingLarge` | `typescaleLg` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeHeadingMedium` | `fontSizeHeadingMedium` | `typescaleMd` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeHeadingSmall` | `fontSizeHeadingSmall` | `typescaleSm` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeHeadingXLarge` | `fontSizeHeadingXLarge` | `typescaleXl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeHeadingXXLarge` | `fontSizeHeadingXXLarge` | `typescale2Xl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeText` | `fontSizeText` | — | Use typescale variables instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeTextLarge` | `fontSizeTextLarge` | `typescaleLg` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeTextMedium` | `fontSizeTextMedium` | `typescaleMd` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeTextSmall` | `fontSizeTextSmall` | `typescaleSm` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeTextXLarge` | `fontSizeTextXLarge` | `typescaleXl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeTextXSmall` | `fontSizeTextXSmall` | `typescaleXs` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontSizeTextXXSmall` | `fontSizeTextXXSmall` | `typescale2Xs` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontStyle` | `fontStyle` | — | Use 'normal' \| 'italic' instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontStyleItalic` | `fontStyleItalic` | — | Use 'italic' instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontStyleNormal` | `fontStyleNormal` | — | Use 'normal' instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontVariant` | `fontVariant` | — | Use 'normal' instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontWeight` | `fontWeight` | — | Use variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontWeightRegular` | `fontWeightRegular` | `fontWeightNormal` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/fontWeightSemiBold` | `fontWeightSemiBold` | `fontWeightSemibold` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/dropShadowHighStyle` | `dropShadowHighStyle` | — | Use boxShadow: shadowLg instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/dropShadowLowStyle` | `dropShadowLowStyle` | — | Use boxShadow: shadowSm instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/dropShadowMediumStyle` | `dropShadowMediumStyle` | — | Use boxShadow: shadowMd instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacing` | `spacing` | — | Use spacing variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingFluid` | `spacingFluid` | — | Use spacing variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingFluidLarge` | `spacingFluidLarge` | `spacingFluidLg` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingFluidMedium` | `spacingFluidMedium` | `spacingFluidMd` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingFluidSmall` | `spacingFluidSmall` | `spacingFluidSm` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingFluidXLarge` | `spacingFluidXLarge` | `spacingFluidXl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingFluidXSmall` | `spacingFluidXSmall` | `spacingFluidXs` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingFluidXXLarge` | `spacingFluidXXLarge` | `spacingFluid2Xl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingStatic` | `spacingStatic` | — | Use spacing variables directly instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingStaticLarge` | `spacingStaticLarge` | `spacingStaticLg` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingStaticMedium` | `spacingStaticMedium` | `spacingStaticMd` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingStaticSmall` | `spacingStaticSmall` | `spacingStaticSm` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingStaticXLarge` | `spacingStaticXLarge` | `spacingStaticXl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingStaticXSmall` | `spacingStaticXSmall` | `spacingStaticXs` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/spacingStaticXXLarge` | `spacingStaticXXLarge` | `spacingStatic2Xl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/motionDurationLong` | `motionDurationLong` | `durationLg` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/motionDurationModerate` | `motionDurationModerate` | `durationMd` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/motionDurationShort` | `motionDurationShort` | `durationSm` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/motionDurationVeryLong` | `motionDurationVeryLong` | `durationXl` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/motionEasingBase` | `motionEasingBase` | `easeInOut` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/motionEasingIn` | `motionEasingIn` | `easeIn` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/motionEasingOut` | `motionEasingOut` | `easeOut` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/gradientToBottomStyle` | `gradientToBottomStyle` | — | Use background: `linear-gradient(to bottom, ${gradientStopsFadeDark});` instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/gradientToLeftStyle` | `gradientToLeftStyle` | — | Use background: `linear-gradient(to left, ${gradientStopsFadeDark});` instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/gradientToRightStyle` | `gradientToRightStyle` | — | background: `linear-gradient(to right, ${gradientStopsFadeDark});` instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/gradientToTopStyle` | `gradientToTopStyle` | — | background: `linear-gradient(to top, ${gradientStopsFadeDark});` instead. | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/displaySmallStyle` | `displaySmallStyle` | `proseHeading3XlStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/displayMediumStyle` | `displayMediumStyle` | `proseHeading4XlStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/displayLargeStyle` | `displayLargeStyle` | `proseHeading5XlStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/headingSmallStyle` | `headingSmallStyle` | `proseHeadingSmStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/headingMediumStyle` | `headingMediumStyle` | `proseHeadingMdStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/headingLargeStyle` | `headingLargeStyle` | `proseHeadingLgStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/headingXLargeStyle` | `headingXLargeStyle` | `proseHeadingXlStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/headingXXLargeStyle` | `headingXXLargeStyle` | `proseHeading2XlStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/textXXSmallStyle` | `textXXSmallStyle` | `proseText2XsStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/textXSmallStyle` | `textXSmallStyle` | `proseTextXsStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/textSmallStyle` | `textSmallStyle` | `proseTextSmStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/textMediumStyle` | `textMediumStyle` | `proseTextMdStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/textLargeStyle` | `textLargeStyle` | `proseTextLgStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/textXLargeStyle` | `textXLargeStyle` | `proseTextXlStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |
| `jsExport/vanillaExtract/getFocusStyle` | `getFocusStyle` | `getFocusVisibleStyle` | — | [references/styles/vanilla-extract.md](references/styles/vanilla-extract.md) |

## Tailwind CSS

Derived from the Tailwind theme exposed by `@porsche-design-system/components-js/tailwindcss`.

| Rule ID | Deprecated | Replacement | Note | Reference |
| --- | --- | --- | --- | --- |
| `cssCustomProperty/tailwindcss/--border-width-regular` | `--border-width-regular` | `--default-border-width` | The default border width is now 1px. | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--border-width-thin` | `--border-width-thin` | `--default-border-width` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--shadow-low` | `--shadow-low` | `--shadow-sm` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--shadow-medium` | `--shadow-medium` | `--shadow-md` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--shadow-high` | `--shadow-high` | `--shadow-lg` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--transition-duration-short` | `--transition-duration-short` | `--transition-duration-sm` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--transition-duration-moderate` | `--transition-duration-moderate` | `--transition-duration-md` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--transition-duration-long` | `--transition-duration-long` | `--transition-duration-lg` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |
| `cssCustomProperty/tailwindcss/--transition-duration-very-long` | `--transition-duration-very-long` | `--transition-duration-xl` | — | [references/styles/tailwindcss.md](references/styles/tailwindcss.md) |

## Tokens

No deprecations in `4.10.1`. Derived from the design-token API exposed by `@porsche-design-system/components-js/tokens`, which was checked and found to carry none — this is a verified result, not an omission.

## Icons

No deprecations in `4.10.1`. Derived from the `p-icon` `name` values exposed by `@porsche-design-system/components-js`, which was checked and found to carry none — this is a verified result, not an omission.

## Stylesheets

No deprecations in `4.10.1`. Derived from the global CSS exposed by `@porsche-design-system/components-js/index.css`, including `@porsche-design-system/components-js/variables.css` and `@porsche-design-system/components-js/color-scheme.css`, which was checked and found to carry none — this is a verified result, not an omission.
