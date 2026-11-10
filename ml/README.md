# AgriNuru machine-learning workspace

This directory is the home for future data preparation, analysis, model evaluation, and model-serving work related to AgriNuru. No models or training pipelines are implemented yet.

## Planned capabilities

- **Crop recommendation:** use crop-recommendation observations and suitable soil and environmental inputs to support crop choice.
- **Crop-yield prediction:** explore historical yields alongside rainfall, temperature, and pesticide-use context. The supplied yield data is largely global and does not replace Kenyan farm-level outcome data.
- **Market-price prediction:** explore historical Kenyan wholesale commodity prices by month, county, and market.
- **Agricultural production analysis:** build on the existing production records in AgriNuru; the downloaded files do not provide farm-level activity, input-cost, or harvest records for this purpose.

## Layout

- `data/raw/` — unchanged source datasets copied from Downloads or extracted from the named archives. Keep these files immutable.
- `data/processed/` — generated data prepared for analysis or model work; ignored by Git.
- `notebooks/` — exploratory, reproducible analysis notebooks.
- `src/` — future reusable data and model code.
- `models/` — generated model artifacts; selected binary formats are ignored by Git.
- `reports/` — future analysis and evaluation outputs.
- `data/README.md` — dataset inventory, provenance, schemas, record counts, and known limitations.

## Integration direction

The existing Django REST API and React frontend remain the application boundary. Future models should be integrated through explicit backend services/API endpoints and consume authorized AgriNuru data where appropriate. Existing crop and production-management functionality remains authoritative; a model must not replace farmer-entered production records. Model features, validation, permissions, evaluation, and serving behavior need a separate design and implementation phase.

No machine-learning dependencies have been added, and no training or inference code is present.
