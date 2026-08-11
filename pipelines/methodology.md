# Illustrative Mortgage Delinquency Model — Methodology

## Purpose
Educational and quick-scenario sensitivity tool for systemic housing credit risk.  
**Not** a production econometric forecast. Always prioritize official MBA National Delinquency Survey and ICE First Look data.

## Model Form (Total Delinquency Rate)

Predicted Total Delinquency (30+ DPD, %) ≈  
**1.8 + 0.55 × Unemployment Rate (%) + 0.22 × 30yr Mortgage Rate (%) − 0.12 × Home Price Appreciation YoY (%)**

- **Intercept (1.8)**: Baseline when macros are near neutral levels.
- **Unemployment beta (0.55)**: Positive and material. Historical sensitivity often in the 0.4–0.8 range.
- **Mortgage rate beta (0.22)**: Positive. Higher rates increase payment burden.
- **HPA beta (−0.12)**: Negative and protective. Rising prices reduce negative equity risk.

## Serious Delinquency Mapping
Serious delinquency (90+ DPD or in foreclosure) estimated as ~46% of total delinquency in base regime, with a stress multiplier (1.0–1.3×) applied in downside scenarios.

## Design Choices
- Intentionally parsimonious (3 variables) for transparency and speed.
- No interaction terms, lags, or autoregressive components in v1.
- Coefficients calibrated approximately against recent quarterly observations for illustration.

## Limitations (Important)
- Not calibrated for extreme tails (e.g. 2008-style events will under-predict).
- Ignores loan composition, credit score distribution, forbearance effects, regional variation.
- Lags and dynamics are simplified away.
- Policy and structural changes are not captured.

## Primary Official Sources
- MBA National Delinquency Survey (quarterly)
- ICE Mortgage Technology First Look (monthly)
- FRED, BLS, Freddie Mac PMMS, FHFA / Case-Shiller

This model exists to provide quantitative scaffolding for “what-if” questions while remaining grounded in official reported figures.
