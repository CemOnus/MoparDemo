
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

DEKRA = "#007A3E"; MOPAR = "#0A65C2"; LIGHT = "#F7F9FC"
RED = "#E65248"; AMBER = "#FFA620"; GREEN = "#2E7D32"

st.set_page_config(page_title="DEKRA × Mopar — Executive KPI Dashboard", layout="wide")

st.markdown(f"""
<style>
.block-container {{padding-top: 2.5rem; padding-bottom: 1rem;}}
.metric-card {{ border-radius: 14px; padding: 14px 16px; border: 1px solid #e7eaf0; background: {LIGHT}; }}
.kpi-green {{background: rgba(46,125,50,.08);}}
.kpi-amber {{background: rgba(255,166,32,.12);}}
.kpi-red {{background: rgba(230,82,72,.12);}}
.kpi-title {{font-weight:600; font-size:0.9rem; color:#334155}}
.kpi-body {{display:flex; gap:10px; align-items:baseline; justify-content:space-between}}
.kpi-value {{font-size:1.6rem; font-weight:700;}}
.kpi-goal {{font-size:0.9rem; color:#475569; opacity:0.9;}}
.brand-hr {{height: 4px; background: linear-gradient(90deg,{DEKRA}, {MOPAR}); border:0; margin: 6px 0 16px 0;}}
</style>
""", unsafe_allow_html=True)

# Header logos (lower on page)
cols = st.columns([2,2,6])
with cols[0]:
    if os.path.exists("dekra_logo.png"): st.image("dekra_logo.png")
with cols[1]:
    if os.path.exists("mopar_logo.png"): st.image("mopar_logo.png")
with cols[2]:
    st.markdown("### Executive KPI Dashboard")
    st.caption("Network overview with goals & RAG status • Drill down to shop (bay) level")
st.markdown("<div class='brand-hr'></div>", unsafe_allow_html=True)

@st.cache_data
def load():
    dealers = pd.read_csv("dealers.csv")
    kpi = pd.read_csv("kpi_timeseries.csv", parse_dates=["date"])
    shops = pd.read_csv("shops.csv")
    shop_kpis = pd.read_csv("shop_kpis.csv", parse_dates=["date"])
    return dealers, kpi, shops, shop_kpis

dealers, kpi, shops, shop_kpis = load()

view = st.sidebar.radio("View", ["Executive Overview", "Dealer Drill-down"], index=0)
region = st.sidebar.selectbox("Region", ["All"] + sorted(dealers["region"].unique()))
stage = st.sidebar.selectbox("Journey Stage", ["All"] + sorted(dealers["journey_stage"].unique()))
compliance_band = st.sidebar.selectbox("Compliance Band", ["All","<70%","70–85%","85%+"])
st.sidebar.markdown("---")
st.sidebar.subheader("Targets (Goals)")

goals = {
    "parts_loyalty": st.sidebar.slider("Parts Loyalty Goal", 0.3, 0.95, 0.70, 0.01),
    "auto_replenishment": st.sidebar.slider("Auto Replenishment Goal", 0.3, 0.95, 0.75, 0.01),
    "maintenance_penetration": st.sidebar.slider("Maintenance Penetration Goal", 0.2, 0.9, 0.50, 0.01),
    "bulk_oil_penetration": st.sidebar.slider("Bulk Oil Penetration Goal", 0.2, 0.95, 0.60, 0.01),
    "service_lane_utilization": st.sidebar.slider("Service Lane Utilization Goal", 0.3, 0.98, 0.75, 0.01),
    "time_in_bay_maint_min": st.sidebar.slider("Time-in-Bay (Maint.) Goal (min)", 15, 90, 30, 1),
    "time_in_bay_adv_min": st.sidebar.slider("Time-in-Bay (Advanced) Goal (min)", 30, 150, 70, 1),
    "total_wait_min": st.sidebar.slider("Total Wait Time Goal (min)", 30, 150, 70, 1),
    "retention_rate": st.sidebar.slider("Retention Rate Goal", 0.3, 0.95, 0.68, 0.01),
    "compliance_score": st.sidebar.slider("Compliance Goal", 0.5, 1.0, 0.85, 0.01),
    "express_ro_growth": st.sidebar.slider("Express RO Growth Goal (last 4w vs first 4w)", 0.0, 0.5, 0.10, 0.01)
}

def filter_dealers():
    mask = pd.Series(True, index=dealers.index)
    if region != "All": mask &= dealers["region"].eq(region)
    if stage != "All": mask &= dealers["journey_stage"].eq(stage)
    latest = kpi.sort_values("date").groupby("dealer_id").tail(1)[["dealer_id","compliance_score"]]
    tmp = dealers[mask].merge(latest, on="dealer_id", how="left")
    if compliance_band != "All":
        if compliance_band == "<70%": tmp = tmp[tmp["compliance_score"]<0.70]
        elif compliance_band == "70–85%": tmp = tmp[(tmp["compliance_score"]>=0.70)&(tmp["compliance_score"]<0.85)]
        else: tmp = tmp[tmp["compliance_score"]>=0.85]
    return tmp.drop(columns=["compliance_score"])

filtered_dealers = filter_dealers()
st.caption(f"Filtered: {len(filtered_dealers):,} of {len(dealers):,} dealerships")

sub = kpi[kpi["dealer_id"].isin(filtered_dealers["dealer_id"])]
if sub.empty:
    st.warning("No data for the current filter selection."); st.stop()

latest = sub.sort_values("date").groupby("dealer_id").tail(1)
weights = latest.set_index("dealer_id")["express_lane_ros"]

def wavg(col):
    v = latest.set_index("dealer_id")[col].reindex(weights.index)
    return float(np.average(v, weights=weights))

def fmt_pct(x): return f"{x:.1%}"
def fmt_min(x): return f"{x:.1f} min"
def fmt_int(x): return f"{int(x):,}"

ts = sub.groupby("date")["express_lane_ros"].sum().reset_index()
if len(ts)>=8:
    base = ts["express_lane_ros"].head(4).sum()
    recent = ts["express_lane_ros"].tail(4).sum()
    growth = (recent - base) / max(base, 1)
else:
    growth = 0.0

def rag_class(value, goal, higher_is_better=True, amber_tol=0.9):
    if higher_is_better:
        if value >= goal: return "kpi-green", "#2E7D32"
        elif value >= amber_tol * goal: return "kpi-amber", "#FFA620"
        else: return "kpi-red", "#E65248"
    else:
        if value <= goal: return "kpi-green", "#2E7D32"
        elif value <= goal * (1/amber_tol): return "kpi-amber", "#FFA620"
        else: return "kpi-red", "#E65248"

def kpi_card(title, value, goal, formatter, higher_is_better=True):
    klass, color = rag_class(value, goal, higher_is_better)
    st.markdown(f"""
    <div class="metric-card {klass}">
      <div class="kpi-title">{title}</div>
      <div class="kpi-body">
        <div class="kpi-value" style="color:{color}">{formatter(value)}</div>
        <div class="kpi-goal">Goal: <b>{formatter(goal)}</b></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

if view == "Executive Overview":
    c = st.columns(6)
    with c[0]: kpi_card("Parts Loyalty", wavg("parts_loyalty"), goals["parts_loyalty"], fmt_pct, True)
    with c[1]: kpi_card("Auto Replenishment", wavg("auto_replenishment"), goals["auto_replenishment"], fmt_pct, True)
    with c[2]: kpi_card("Maint. Penetration", wavg("maintenance_penetration"), goals["maintenance_penetration"], fmt_pct, True)
    with c[3]: kpi_card("Bulk Oil Penetration", wavg("bulk_oil_penetration"), goals["bulk_oil_penetration"], fmt_pct, True)
    with c[4]: kpi_card("Service Lane Utilization", wavg("service_lane_utilization"), goals["service_lane_utilization"], fmt_pct, True)
    with c[5]: kpi_card("Express Lane ROs (wk)", weights.sum(), max(weights.sum(),1), fmt_int, True)

    c2 = st.columns(5)
    with c2[0]: kpi_card("Time‑in‑Bay (Maint.)", wavg("time_in_bay_maint_min"), goals["time_in_bay_maint_min"], fmt_min, False)
    with c2[1]: kpi_card("Time‑in‑Bay (Advanced)", wavg("time_in_bay_adv_min"), goals["time_in_bay_adv_min"], fmt_min, False)
    with c2[2]: kpi_card("Total Wait Time", wavg("total_wait_min"), goals["total_wait_min"], fmt_min, False)
    with c2[3]: kpi_card("Retention Rate", wavg("retention_rate"), goals["retention_rate"], fmt_pct, True)
    with c2[4]: kpi_card("Compliance", wavg("compliance_score"), goals["compliance_score"], fmt_pct, True)

    st.markdown("")
    c3 = st.columns(2)
    with c3[0]:
        klass, color = rag_class(growth, goals["express_ro_growth"], True)
        st.markdown(f"""
        <div class="metric-card {klass}">
          <div class="kpi-title">Express RO Growth (last 4w vs first 4w)</div>
          <div class="kpi-body">
            <div class="kpi-value" style="color:{color}">{growth:.1%}</div>
            <div class="kpi-goal">Goal: <b>{goals['express_ro_growth']:.0%}</b></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c3[1]:
        counts = filtered_dealers["journey_stage"].value_counts().reindex(sorted(dealers["journey_stage"].unique()), fill_value=0)
        fig0, ax0 = plt.subplots(figsize=(5,3)); ax0.bar(counts.index, counts.values, color=MOPAR); ax0.set_ylabel("Dealers"); ax0.set_xlabel("Stage")
        st.pyplot(fig0)

    st.markdown("### Network Trends (weighted)")
    network = sub.groupby("date").apply(
        lambda x: pd.Series({
            "parts_loyalty": np.average(x["parts_loyalty"], weights=x["express_lane_ros"]),
            "maintenance_penetration": np.average(x["maintenance_penetration"], weights=x["express_lane_ros"]),
            "service_lane_utilization": np.average(x["service_lane_utilization"], weights=x["express_lane_ros"]),
            "time_in_bay_maint_min": np.average(x["time_in_bay_maint_min"], weights=x["express_lane_ros"]),
            "total_wait_min": np.average(x["total_wait_min"], weights=x["express_lane_ros"]),
            "retention_rate": np.average(x["retention_rate"], weights=x["express_lane_ros"]),
        })
    ).reset_index()
    row = st.columns(3)
    f1,a1 = plt.subplots(); a1.plot(network["date"], network["parts_loyalty"], color=DEKRA); a1.set_title("Parts Loyalty"); row[0].pyplot(f1)
    f2,a2 = plt.subplots(); a2.plot(network["date"], network["maintenance_penetration"], color=MOPAR); a2.set_title("Maint. Penetration"); row[1].pyplot(f2)
    f3,a3 = plt.subplots(); a3.plot(network["date"], network["service_lane_utilization"], color=DEKRA); a3.set_title("Service Lane Utilization"); row[2].pyplot(f3)
    row = st.columns(3)
    f4,a4 = plt.subplots(); a4.plot(network["date"], network["time_in_bay_maint_min"], color=MOPAR); a4.set_title("Time-in-Bay (Maint.)"); row[0].pyplot(f4)
    f5,a5 = plt.subplots(); a5.plot(network["date"], network["total_wait_min"], color=MOPAR); a5.set_title("Total Wait"); row[1].pyplot(f5)
    f6,a6 = plt.subplots(); a6.plot(network["date"], network["retention_rate"], color=DEKRA); a6.set_title("Retention"); row[2].pyplot(f6)

    st.markdown("### Top Dealers — Composite Score")
    latest2 = sub.sort_values("date").groupby("dealer_id").tail(1)
    rank = latest2.merge(dealers[["dealer_id","dealer_name","region","journey_stage"]], on="dealer_id", how="left")
    def normalize(s, invert=False):
        v = s.astype(float); v = -v if invert else v
        return (v - v.min())/(v.max()-v.min()+1e-9)
    rank["score"] = (
        normalize(rank["parts_loyalty"]) + normalize(rank["auto_replenishment"]) + normalize(rank["maintenance_penetration"]) +
        normalize(rank["bulk_oil_penetration"]) + normalize(rank["service_lane_utilization"]) +
        normalize(rank["time_in_bay_maint_min"], True) + normalize(rank["total_wait_min"], True) +
        normalize(rank["retention_rate"]) + normalize(rank["compliance_score"])
    ) / 9.0
    st.dataframe(rank.sort_values("score", ascending=False)[["dealer_id","dealer_name","region","journey_stage","score"]].head(25))

else:
    left, right = st.columns([2,1])
    with left:
        sel = st.selectbox("Select Dealer", sorted(filtered_dealers["dealer_id"].tolist()))
        info = dealers[dealers["dealer_id"]==sel].iloc[0]
        st.subheader(f"{info['dealer_name']} • {info['region']}, {info['state']} • Stage: {info['journey_stage']}")
        hist = kpi[kpi["dealer_id"]==sel].sort_values("date")
        f1,a1 = plt.subplots(); a1.plot(hist["date"], hist["parts_loyalty"], color=DEKRA); a1.set_ylabel("Parts Loyalty"); st.pyplot(f1)
        f2,a2 = plt.subplots(); a2.plot(hist["date"], hist["service_lane_utilization"], color=DEKRA); a2.set_ylabel("Service Lane Utilization"); st.pyplot(f2)
        f3,a3 = plt.subplots(); a3.plot(hist["date"], hist["time_in_bay_maint_min"], color=MOPAR); a3.set_ylabel("Time-in-Bay (Maint.)"); st.pyplot(f3)
        f4,a4 = plt.subplots(); a4.plot(hist["date"], hist["total_wait_min"], color=MOPAR); a4.set_ylabel("Total Wait"); st.pyplot(f4)
    with right:
        st.subheader("Shop (Bay) Snapshot")
        shop = shops[shops["dealer_id"]==sel].iloc[0]
        st.metric("Express Bays", int(shop["bays_express"]))
        st.metric("Total Bays", int(shop["bays_total"]))
        st.metric("Hours Open (weekly)", int(shop["hours_open_weekly"]))
        shop_hist = shop_kpis[shop_kpis["dealer_id"]==sel].sort_values("date")
        f5,a5 = plt.subplots(); a5.plot(shop_hist["date"], shop_hist["utilization"], color=DEKRA); a5.set_ylabel("Bay Utilization"); st.pyplot(f5)
        f6,a6 = plt.subplots(); a6.plot(shop_hist["date"], shop_hist["ro_per_bay_hour"], color=MOPAR); a6.set_ylabel("RO per Bay Hour"); st.pyplot(f6)
