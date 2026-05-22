import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from models.roi_engine import (
    annual_ale_reductions,
    annual_costs,
    calculate_ale,
    calculate_payback_period,
    calculate_residual_ale,
    calculate_roi,
)

DATA_PATH = Path(__file__).parent / "data" / "controls.json"
HORIZON_YEARS = 5
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]


st.set_page_config(
    page_title="Cyber Investment ROI Calculator",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_controls():
    with open(DATA_PATH) as fp:
        return json.load(fp)["controls"]


controls = load_controls()


st.title("Cyber Investment ROI Calculator")
st.caption("Translate security controls into expected financial impact.")


with st.sidebar:
    st.header("Organization profile")
    org_name = st.text_input("Organization name", value="Acme Corp")
    employees = st.slider(
        "Number of employees", min_value=50, max_value=10_000, value=1_000, step=50
    )
    asset_value = st.slider(
        "Asset value at risk ($)",
        min_value=100_000,
        max_value=50_000_000,
        value=5_000_000,
        step=100_000,
    )
    threat_frequency = st.slider(
        "Annual threat frequency (credible attacks / yr)",
        min_value=1,
        max_value=50,
        value=12,
    )
    vulnerability_score = st.slider(
        "Vulnerability score (likelihood of success without controls)",
        min_value=0.1,
        max_value=1.0,
        value=0.40,
        step=0.05,
    )


ale = calculate_ale(asset_value, threat_frequency, vulnerability_score)


st.subheader(f"Baseline annual loss expectancy — {org_name}")
b1, b2, b3, b4 = st.columns(4)
b1.metric("Baseline ALE", f"${ale:,.0f}")
b2.metric("Asset value at risk", f"${asset_value:,.0f}")
b3.metric("Threat frequency", f"{threat_frequency} / yr")
b4.metric("Vulnerability score", f"{vulnerability_score:.2f}")

st.divider()


st.subheader("Select controls to evaluate")
selected = []
checkbox_cols = st.columns(3)
for idx, ctrl in enumerate(controls):
    with checkbox_cols[idx % 3]:
        if st.checkbox(ctrl["name"], value=True, key=f"chk_{ctrl['id']}"):
            selected.append(ctrl)

if not selected:
    st.info("Select at least one control to model ROI.")
    st.stop()


rows = []
per_control_reductions = {}
per_control_costs = {}

for ctrl in selected:
    annual_cost_total = ctrl["default_annual_cost_per_user"] * employees
    reductions = annual_ale_reductions(
        ale=ale,
        reduction_pct=ctrl["default_reduction_pct"],
        years=HORIZON_YEARS,
        decay_rate=ctrl["decay_rate"],
    )
    costs = annual_costs(annual_cost_total, HORIZON_YEARS)
    roi_pct = calculate_roi(reductions, costs)
    payback = calculate_payback_period(reductions, costs)
    residual = calculate_residual_ale(ale, ctrl["default_reduction_pct"])

    per_control_reductions[ctrl["id"]] = reductions
    per_control_costs[ctrl["id"]] = costs

    rows.append(
        {
            "id": ctrl["id"],
            "Control": ctrl["name"],
            "Category": ctrl["category"],
            "Annual cost": annual_cost_total,
            "ALE reduction %": ctrl["default_reduction_pct"] * 100,
            "Residual ALE (yr 1)": residual,
            "5-yr ROI %": roi_pct,
            "Payback (yr)": payback,
            "5-yr reduction": sum(reductions),
            "5-yr cost": sum(costs),
        }
    )

df = (
    pd.DataFrame(rows)
    .sort_values("5-yr ROI %", ascending=False)
    .reset_index(drop=True)
)

st.subheader("Per-control economics")
for _, row in df.iterrows():
    with st.container(border=True):
        st.markdown(f"**{row['Control']}**  ·  *{row['Category']}*")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Annual cost", f"${row['Annual cost']:,.0f}")
        m2.metric("ALE reduction", f"{row['ALE reduction %']:.0f}%")
        m3.metric("Residual ALE", f"${row['Residual ALE (yr 1)']:,.0f}")
        m4.metric("5-yr ROI", f"{row['5-yr ROI %']:,.0f}%")

st.divider()


st.subheader("Executive prioritization — ranked by 5-yr ROI")
display_df = df[
    [
        "Control",
        "Category",
        "Annual cost",
        "ALE reduction %",
        "Residual ALE (yr 1)",
        "5-yr ROI %",
        "Payback (yr)",
    ]
].copy()
display_df["Annual cost"] = display_df["Annual cost"].map(lambda v: f"${v:,.0f}")
display_df["Residual ALE (yr 1)"] = display_df["Residual ALE (yr 1)"].map(
    lambda v: f"${v:,.0f}"
)
display_df["ALE reduction %"] = display_df["ALE reduction %"].map(lambda v: f"{v:.0f}%")
display_df["5-yr ROI %"] = display_df["5-yr ROI %"].map(lambda v: f"{v:,.0f}%")
display_df["Payback (yr)"] = display_df["Payback (yr)"].map(
    lambda v: "—" if v is None or pd.isna(v) else f"Yr {int(v)}"
)
st.dataframe(display_df, use_container_width=True, hide_index=True)


years = list(range(1, HORIZON_YEARS + 1))

st.subheader("Effective ALE reduction over 5 years")
decay_fig = go.Figure()
for i, ctrl in enumerate(selected):
    decay_fig.add_trace(
        go.Scatter(
            x=years,
            y=per_control_reductions[ctrl["id"]],
            mode="lines+markers",
            name=ctrl["name"],
            line=dict(color=PALETTE[i % len(PALETTE)], width=2.5),
        )
    )
decay_fig.update_layout(
    template="plotly_white",
    xaxis_title="Year",
    yaxis_title="Annual ALE reduction ($)",
    yaxis_tickformat="$,.0f",
    height=440,
    legend=dict(orientation="h", y=-0.2),
    margin=dict(l=10, r=10, t=20, b=10),
)
st.plotly_chart(decay_fig, use_container_width=True)


st.subheader("Cumulative cost vs. cumulative ALE reduction")
payback_fig = go.Figure()
for i, ctrl in enumerate(selected):
    cum_red, cum_cost = [], []
    running_r = running_c = 0.0
    for r, c in zip(per_control_reductions[ctrl["id"]], per_control_costs[ctrl["id"]]):
        running_r += r
        running_c += c
        cum_red.append(running_r)
        cum_cost.append(running_c)
    color = PALETTE[i % len(PALETTE)]
    payback_fig.add_trace(
        go.Scatter(
            x=years,
            y=cum_red,
            mode="lines+markers",
            name=f"{ctrl['name']} — cumulative reduction",
            line=dict(color=color, width=2.5),
        )
    )
    payback_fig.add_trace(
        go.Scatter(
            x=years,
            y=cum_cost,
            mode="lines+markers",
            name=f"{ctrl['name']} — cumulative cost",
            line=dict(color=color, width=2, dash="dot"),
        )
    )
payback_fig.update_layout(
    template="plotly_white",
    xaxis_title="Year",
    yaxis_title="Cumulative $",
    yaxis_tickformat="$,.0f",
    height=500,
    legend=dict(orientation="h", y=-0.28),
    margin=dict(l=10, r=10, t=20, b=10),
)
st.plotly_chart(payback_fig, use_container_width=True)


total_reduction = df["5-yr reduction"].sum()
total_cost = df["5-yr cost"].sum()
portfolio_roi = (
    (total_reduction - total_cost) / total_cost * 100 if total_cost else 0.0
)
top_pick = df.iloc[0]["Control"]

st.divider()
st.subheader("Portfolio summary")
with st.container(border=True):
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total 5-yr ALE reduction", f"${total_reduction:,.0f}")
    s2.metric("Total 5-yr cost", f"${total_cost:,.0f}")
    s3.metric("Blended portfolio ROI", f"{portfolio_roi:,.0f}%")
    s4.metric("Recommended first investment", top_pick)
    st.success(
        f"**Recommendation for {org_name}:** prioritize **{top_pick}** — highest 5-yr "
        f"ROI per dollar invested. Sequence remaining investments in the ranked order above."
    )
    st.caption(
        "Portfolio totals sum each control's reduction independently against the same baseline ALE "
        "and do not model overlapping coverage between controls."
    )
