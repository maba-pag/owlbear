# p-ai-tag

`p-ai-tag` is used to indicate AI-generated or AI-modified content. It displays a localized and legally compliant AI label text (abbreviated or as long-form) combined with an icon.

## Usage

Use the AI tag to indicate that content has been generated or assisted by artificial intelligence.

The following segment provides instructions for designers and developers regarding the appropriate utilization of this component in various situations.

### Do:

- Use to indicate AI-generated or AI-assisted content.
- Prefer BCP47 `locale` values (e.g. `de-DE`, `en-US`, or language-only `en`). POSIX forms (e.g. `de_DE`) are deprecated but still accepted. Copy is resolved by language; markets without a translation fall back to English.
- Use the `abbreviation` variant for compact contexts where space is limited.
- Use the `generated` or `modified` variant when a full label improves clarity.

### Don't:

- Don't use as a general-purpose tag — use `p-tag` instead.
- Don't use for non-AI-related labeling or categorization.

## Accessibility support

For the `abbreviation` variant, the component uses an `<abbr>` element so the full “artificial intelligence” term is available as the expansion.

## API

### Properties

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `locale` | `'ar-BH'` `'ar-KW'` `'ar-QA'` `'ar-SA'` `'az-AZ'` `'bg-BG'` `'bs-BA'` `'cs-CZ'` `'cs-SK'` `'da-DK'` `'de-AT'` `'de-CH'` `'de-DE'` `'de-LI'` `'de-LU'` `'el-GR'` `'en'` `'en-AE'` `'en-AE-x-abu-dhabi'` `'en-AE-x-abudhabi'` `'en-AE-x-dubai'` `'en-AL'` `'en-AU'` `'en-BA'` `'en-BG'` `'en-BH'` `'en-BN'` `'en-CA'` `'en-CH'` `'en-CN'` `'en-CW'` `'en-CY'` `'en-CZ'` `'en-DK'` `'en-EE'` `'en-EG'` `'en-FI'` `'en-GB'` `'en-GE'` `'en-GH'` `'en-GI'` `'en-GR'` `'en-HK'` `'en-HR'` `'en-HT'` `'en-ID'` `'en-IE'` `'en-IL'` `'en-IN'` `'en-IS'` `'en-JM'` `'en-JO'` `'en-KH'` `'en-KR'` `'en-KW'` `'en-KZ'` `'en-LB'` `'en-LK'` `'en-LT'` `'en-LV'` `'en-ME'` `'en-MK'` `'en-MN'` `'en-MT'` `'en-MU'` `'en-MY'` `'en-NC'` `'en-NL'` `'en-NO'` `'en-NZ'` `'en-OM'` `'en-PF'` `'en-PH'` `'en-PL'` `'en-PR'` `'en-QA'` `'en-RO'` `'en-RS'` `'en-SA'` `'en-SE'` `'en-SG'` `'en-SI'` `'en-SK'` `'en-TH'` `'en-TR'` `'en-TT'` `'en-TW'` `'en-UA'` `'en-US'` `'en-VE'` `'en-VN'` `'en-XA'` `'en-YE'` `'en-ZA'` `'es-AD'` `'es-AR'` `'es-BO'` `'es-CL'` `'es-CO'` `'es-CR'` `'es-DO'` `'es-EC'` `'es-ES'` `'es-GT'` `'es-HN'` `'es-MX'` `'es-PA'` `'es-PE'` `'es-PR'` `'es-PY'` `'es-SV'` `'es-TT'` `'es-UY'` `'es-VE'` `'et-EE'` `'fi-FI'` `'fr-BE'` `'fr-CA'` `'fr-CH'` `'fr-DZ'` `'fr-FR'` `'fr-GP'` `'fr-LI'` `'fr-LU'` `'fr-MA'` `'fr-MC'` `'fr-MQ'` `'fr-MU'` `'fr-NC'` `'fr-PF'` `'fr-RE'` `'fr-TN'` `'he-IL'` `'hr-HR'` `'hu-HU'` `'hy-AM'` `'is-IS'` `'it-CH'` `'it-IT'` `'ja-JP'` `'ka-GE'` `'ko-KR'` `'lt-LT'` `'lv-LV'` `'me-ME'` `'mk-MK'` `'mt-MT'` `'nb-NO'` `'nl-BE'` `'nl-NL'` `'no-NO'` `'pl-PL'` `'pt-BR'` `'pt-PT'` `'ro-MD'` `'ro-RO'` `'ru-AZ'` `'ru-BY'` `'ru-CY'` `'ru-EE'` `'ru-KZ'` `'ru-LT'` `'ru-LV'` `'ru-RU'` `'ru-UK'` `'ru-UZ'` `'sk-SK'` `'sl-SI'` `'sr-ME'` `'sr-RS'` `'sv-SE'` `'tr-TR'` `'uk-UA'` `'zh-CN'` `'zh-HK'` `'zh-TW'`<br>_deprecated:_ `'ar_BH'` `'ar_KW'` `'ar_QA'` `'ar_SA'` `'az_AZ'` `'bg_BG'` `'bs_BA'` `'cs_CZ'` `'cs_SK'` `'da_DK'` `'de_AT'` `'de_CH'` `'de_DE'` `'de_LI'` `'de_LU'` `'el_GR'` `'en_AE'` `'en_AE_x_abu_dhabi'` `'en_AE_x_abudhabi'` `'en_AE_x_dubai'` `'en_AL'` `'en_AU'` `'en_BA'` `'en_BG'` `'en_BH'` `'en_BN'` `'en_CA'` `'en_CH'` `'en_CN'` `'en_CW'` `'en_CY'` `'en_CZ'` `'en_DK'` `'en_EE'` `'en_EG'` `'en_FI'` `'en_GB'` `'en_GE'` `'en_GH'` `'en_GI'` `'en_GR'` `'en_HK'` `'en_HR'` `'en_HT'` `'en_ID'` `'en_IE'` `'en_IL'` `'en_IN'` `'en_IS'` `'en_JM'` `'en_JO'` `'en_KH'` `'en_KR'` `'en_KW'` `'en_KZ'` `'en_LB'` `'en_LK'` `'en_LT'` `'en_LV'` `'en_ME'` `'en_MK'` `'en_MN'` `'en_MT'` `'en_MU'` `'en_MY'` `'en_NC'` `'en_NL'` `'en_NO'` `'en_NZ'` `'en_OM'` `'en_PF'` `'en_PH'` `'en_PL'` `'en_PR'` `'en_QA'` `'en_RO'` `'en_RS'` `'en_SA'` `'en_SE'` `'en_SG'` `'en_SI'` `'en_SK'` `'en_TH'` `'en_TR'` `'en_TT'` `'en_TW'` `'en_UA'` `'en_US'` `'en_VE'` `'en_VN'` `'en_XA'` `'en_YE'` `'en_ZA'` `'es_AD'` `'es_AR'` `'es_BO'` `'es_CL'` `'es_CO'` `'es_CR'` `'es_DO'` `'es_EC'` `'es_ES'` `'es_GT'` `'es_HN'` `'es_MX'` `'es_PA'` `'es_PE'` `'es_PR'` `'es_PY'` `'es_SV'` `'es_TT'` `'es_UY'` `'es_VE'` `'et_EE'` `'fi_FI'` `'fr_BE'` `'fr_CA'` `'fr_CH'` `'fr_DZ'` `'fr_FR'` `'fr_GP'` `'fr_LI'` `'fr_LU'` `'fr_MA'` `'fr_MC'` `'fr_MQ'` `'fr_MU'` `'fr_NC'` `'fr_PF'` `'fr_RE'` `'fr_TN'` `'he_IL'` `'hr_HR'` `'hu_HU'` `'hy_AM'` `'is_IS'` `'it_CH'` `'it_IT'` `'ja_JP'` `'ka_GE'` `'ko_KR'` `'lt_LT'` `'lv_LV'` `'me_ME'` `'mk_MK'` `'mt_MT'` `'nb_NO'` `'nl_BE'` `'nl_NL'` `'no_NO'` `'pl_PL'` `'pt_BR'` `'pt_PT'` `'ro_MD'` `'ro_RO'` `'ru_AZ'` `'ru_BY'` `'ru_CY'` `'ru_EE'` `'ru_KZ'` `'ru_LT'` `'ru_LV'` `'ru_RU'` `'ru_UK'` `'ru_UZ'` `'sk_SK'` `'sl_SI'` `'sr_ME'` `'sr_RS'` `'sv_SE'` `'tr_TR'` `'uk_UA'` `'zh_CN'` `'zh_HK'` `'zh_TW'` | `'en-US'` | Market locale for the AI text (BCP47, e.g. `en-US`). Language-only `en` is supported for international markets. POSIX forms (e.g. `en_US`) are deprecated but still accepted. Copy is resolved by language; unknown languages fall back to English. |
| `variant` | `'abbreviation'` `'generated'` `'modified'` | `'generated'` | Variant to display: 'abbreviation' (e.g. "AI"), 'generated' (e.g. "AI-generated"), or 'modified' (e.g. "AI-modified"). |

## Examples

| Example | When to use | File |
| --- | --- | --- |
| Default | Minimal default configuration. | [./examples/Default.html](./examples/Default.html) |
| Within Checkbox | The `p-ai-tag` can be used inline with other form components. | [./examples/WithinCheckbox.html](./examples/WithinCheckbox.html) |
| Within Radio Group | The `p-ai-tag` can also be placed within the slotted label of a `p-radio-button-wrapper` to indicate AI-related content for individual radio options. | [./examples/WithinRadioGroup.html](./examples/WithinRadioGroup.html) |
| Within Form Label | The `p-ai-tag` can be placed within a `label` of a `p-select` (or any other form component) to indicate AI-related content for selected options. | [./examples/WithinFormLabel.html](./examples/WithinFormLabel.html) |
| Within Input Search | The `p-ai-tag` can be placed in the `end` slot of a `p-input-search` to indicate that the search results are AI-powered. | [./examples/WithinInputSearch.html](./examples/WithinInputSearch.html) |
| Within Text | The `p-ai-tag` can be placed inline within a `p-text` to indicate that the surrounding text content is AI-related. | [./examples/WithinText.html](./examples/WithinText.html) |
| Within Image | The `p-ai-tag` can be positioned as an overlay on images to indicate that the image content has been generated or modified by AI. | [./examples/WithinImage.html](./examples/WithinImage.html) |
| Within Table | The `p-ai-tag` can sit inline in a `p-table-head-cell` next to the column title — for example on a **Status** column when that data is AI-assisted. | [./examples/WithinTable.html](./examples/WithinTable.html) |
