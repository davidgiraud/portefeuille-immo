# CLAUDE.md — Portefeuille Immobilier

## Project overview

A Streamlit simulator for modelling a commercial real estate (office) portfolio.
Single-file app: `portefeuille_immo.py`.

## How to run

```bash
pip install -r requirements.txt
streamlit run portefeuille_immo.py
```

## User profile

The owner of this project is a **beginner programmer**. When making changes or
explaining code:
- Prefer clear, simple solutions over clever or terse ones
- Add brief inline comments when introducing new logic
- Explain *why* a change is made, not just what was changed
- Suggest next learning steps when relevant
- Never assume prior knowledge of Python, finance, or software concepts

## Learning-oriented features

When adding new features, favour approaches that help the user understand:
- What a financial metric means and how it is calculated (tooltips, expanders,
  or inline markdown explanations in the UI)
- How changing an input affects outputs (sensitivity analysis, "what-if" views)
- Industry-standard terminology alongside the French labels already in the UI

## Regulatory context — European AIFM (AIFMD)

This tool is intended for use in an **Alternative Investment Fund Manager**
context governed by the **EU AIFMD** (Directive 2011/61/EU) and its successor
**AIFMD II**. Always respect the following rules when adding or modifying
financial logic:

### Leverage
- Leverage must be expressible using both the **Commitment Method** and the
  **Gross Method** as defined by ESMA (AIFMD Annex I). Do not conflate the two.
- For real estate AIFs, indicative regulatory leverage limits are typically
  **3× NAV** (gross method). Flag in the UI if modelled leverage exceeds this.
- LTV (Loan-to-Value) is an asset-level metric; fund-level leverage is separate.

### Valuation
- Asset values must be derived from an **independent valuation** process in a
  real AIFM setting. The cap-rate-based valuation in this simulator is a
  simplified proxy — label it clearly as an *estimate*, not a formal valuation.
- Valuation frequency for closed-ended real estate AIFs is typically annual or
  semi-annual.

### Return metrics
- Prefer **IRR** (Internal Rate of Return) and **equity multiple (MOIC)** as
  primary return metrics — these are the INREV and ILPA standards for European
  real estate funds.
- **Cash-on-cash yield** and **NOI yield** are acceptable secondary metrics.
- Avoid presenting gross returns without a net-of-fees equivalent when fees are
  modelled.

### Fees & costs
- When modelling fees, distinguish between **management fees** (on NAV or
  committed capital), **acquisition fees**, and **performance fees** (carried
  interest). European market norm for carried interest is 20% above an 8%
  preferred return hurdle.
- Operating costs (frais d'exploitation) should include property management,
  insurance, maintenance, and non-recoverable capex — not just a flat percentage.

### Reporting
- AIFMD Annex IV reporting requires disclosure of principal markets, instruments
  traded, principal exposures, and leverage. Keep data structures compatible
  with these categories.

### ESG / SFDR
- Under the **Sustainable Finance Disclosure Regulation (SFDR)**, real estate
  funds are increasingly classified as Article 6, 8, or 9. When adding
  reporting or scoring features, allow the user to tag each asset with an SFDR
  category.
- Energy efficiency (DPE/EPC ratings) is a relevant ESG data point for office
  assets.

## Current financial model — known simplifications

These are intentional simplifications to keep the tool learnable; note them
before changing the underlying logic:
- Cap-rate valuation: `asset value = annual rent / cap rate`
- Debt service: standard French amortisation (mensualités constantes)
- Occupancy evolution: logistic growth curve with a fixed growth constant `k=0.1`
- NOI: `revenue - operating costs - annual debt service` (i.e. net of financing,
  which is non-standard — pure NOI excludes financing costs)

## Dependencies

Keep the dependency footprint minimal. Existing libraries:
`streamlit`, `pandas`, `numpy`, `matplotlib`, `seaborn`

Do not add new libraries without a clear reason.

## Language

UI labels and user-facing text are in **French**. Code identifiers and comments
may be in English or French — consistency within a function is preferred.
