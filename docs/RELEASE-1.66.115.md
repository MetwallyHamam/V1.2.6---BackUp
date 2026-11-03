# Millensys Support Hub 1.66.115

## Knowledge article scope selection and filtering

- Makes product, product-module, and client applicability selectable when creating or editing a Knowledge Base article.
- Keeps all applicability fields optional; an empty selection continues to mean that the article is not restricted by that scope.
- Adds Knowledge Base list filters for category, product, module, and client.
- Narrows module choices by the selected product in the article filter bar.
- Adds backend filtering for structured category, product, product module, and client scope.
- Includes English and Arabic labels for the new module field and filters.
- Retains database compatibility at `0245_knowledge_resolution`; no new migration is required.

## Deployment

Deploy the packaged frontend and backend together. Existing knowledge articles and
their scope links remain compatible. Run the standard smoke test after switching IIS
to this release.
