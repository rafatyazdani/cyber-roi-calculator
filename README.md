# Cyber Investment ROI Calculator

Translate security controls into expected financial impact.

A Streamlit application that helps security leaders quantify the return on cyber investments. It models the dollar value of risk reduction from common security controls — MFA, EDR, IAM hardening, awareness training, CSPM, DLP — using industry-sourced effectiveness estimates and a decay curve that reflects how control effectiveness degrades over time.

## What it does

Given a baseline organizational risk profile (asset value, threat frequency, vulnerability), the tool computes:

- **Annual Loss Expectancy (ALE)** before any controls are applied
- **Residual ALE** after each candidate control's risk reduction
- **Effective reduction over 5 years**, applying exponential decay to model erosion of control effectiveness
- **5-year ROI %** per control, comparing cumulative ALE reduction to cumulative cost
- **Payback period** — the year cumulative reduction first exceeds cumulative cost
- **Portfolio summary** ranking selected controls and recommending a first investment

The output is designed for executive prioritization: a ranked table, decay curves, cumulative cost-vs-reduction charts, and a blended portfolio ROI.

## Methodology

| Step | Formula |
| --- | --- |
| Baseline ALE | `asset_value × threat_frequency × vulnerability_score` |
| Residual ALE | `ALE × (1 − reduction_pct)` |
| Effective reduction at year *t* | `reduction_pct × exp(−decay_rate × t)` |
| 5-year ROI | `(Σ annual_reduction − Σ annual_cost) / Σ annual_cost × 100` |
| Payback period | First year cumulative reduction exceeds cumulative cost |

Default decay rate is 0.08 (≈8% effectiveness loss per year). Per-control decay rates in `data/controls.json` vary based on how quickly each control type typically erodes (training fades faster than MFA mechanisms).

## Controls modeled

| Control | Default reduction | $/user/yr | Decay |
| --- | --- | --- | --- |
| Multi-Factor Authentication | 99% | $6 | 0.05 |
| Endpoint Detection & Response | 35% | $75 | 0.10 |
| IAM Hardening (PAM, JIT, least privilege) | 45% | $40 | 0.07 |
| Security Awareness Training | 30% | $18 | 0.15 |
| Cloud Security Posture Management | 50% | $30 | 0.08 |
| Data Loss Prevention | 30% | $35 | 0.10 |

Reduction estimates are sourced from Microsoft Identity Security Report, Verizon DBIR, Ponemon/IBM Cost of a Data Breach, Mandiant M-Trends, Gartner, NIST SP 800-53, and vendor benchmarks. See `data/controls.json` for per-control citations.

## Quickstart

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens at http://localhost:8501. Adjust the sidebar inputs (employees, asset value, threat frequency, vulnerability score), select controls to evaluate, and review the ranked output.

## Project structure

```
cyber-roi-calculator/
├── app.py                  # Streamlit UI
├── models/
│   └── roi_engine.py       # ALE, decay, ROI, payback functions
├── data/
│   └── controls.json       # Control catalog with effectiveness + cost defaults
├── requirements.txt
└── README.md
```

## Caveats

- **Independent reductions.** Per-control reductions are computed against the same baseline ALE. Real-world controls overlap (MFA and IAM both reduce credential-attack risk), so summed portfolio reductions can exceed baseline ALE. The model is fit for relative prioritization, not absolute loss-prevention forecasting.
- **Sourced defaults are illustrative.** Industry benchmarks shift year to year. Verify reduction percentages against current source publications before using this tool for vendor-facing decisions.
- **No discounting.** Cumulative figures are nominal — no NPV / cost-of-capital adjustment.
