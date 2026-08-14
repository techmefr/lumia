# Self-hosted fonts

Four serif/sans pairs, selectable in Réglages. They are served by the instance rather than fetched
from a CDN: a reader that promises your reading never leaves your machine cannot call Google on every
page load.

| Pair | Titles | Body |
| --- | --- | --- |
| Éditorial | Source Serif 4 | Inter |
| Magazine | Playfair Display | Source Sans 3 |
| Humaniste | Lora | Work Sans |
| Technique | IBM Plex Serif | IBM Plex Sans |

All eight families are licensed under the [SIL Open Font License 1.1](https://openfontlicense.org/),
which allows redistribution alongside this project. `fonts.css` carries the `@font-face` rules with
relative `src` urls, so the directory can be served from any base path; only the latin and latin-ext
subsets are included, and the browser downloads only the faces the active pair uses.

`fonts.css` is generated from the Google Fonts css2 API. To refresh it or add a pair, re-run the
generator with the family list and drop the result here — the `data-font-pair` values in
`src/app.css` and the presets in `technical/theme/theme-store.svelte.ts` have to agree with the
family names.
