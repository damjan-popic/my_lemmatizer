# my_lemmatizer

FastAPI lemmatizer service for Slovene and Italian with LORIS rule checking.

## MWU / span-layer update

See `MWU_CHANGES.md` for the full bilingual Slovene/English description.

Important endpoints:

- `POST /analyze` — unchanged token-only analysis.
- `POST /analyze-full` — token analysis plus `spans` for multi-word/rule matches.
- `POST /loris/check` — existing LORIS response plus a new `spans` field.

Frontend catch point for MWUs:

```js
const spans = response.spans ?? [];
```
