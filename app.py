
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DEKRA = "#007A3E"
MOPAR = "#0A65C2"
LIGHT = "#F5F7FA"

st.set_page_config(page_title="DEKRA × Mopar — Executive KPI Dashboard", layout="wide")

# ======== Assets & Styles ========
def brand_header():
    cols = st.columns([1,1,5])
    cols[0].image("dekra.svg")
    cols[1].image("mopar.svg")
    with cols[2]:
        st.markdown(f"<h2 style='margin-bottom:0'>Executive KPI Dashboard</h2><div style='color:#444'>Network view with drill-down to shop level</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <style>
    .block-container {{padding-top: 1rem; padding-bottom: 1rem;}}
    .metric-card {{
        background: {LIGHT}; border: 1px solid #e6e9ef; border-radius: 12px; padding: 14px 16px;
    }}
    .brand-hr {{height: 4px; background: linear-gradient(90deg,{DEKRA}, {MOPAR}); border:0; margin: 8px 0 16px 0;}}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div class='brand-hr'></div>", unsafe_allow_html=True)

@st.cache_data
def load():
    dealers = pd.read_csv("dealers.csv")
    kpi = pd.read_csv("kpi_timeseries.csv", parse_dates=["date"])
    shops = pd.read_csv("shops.csv")
    shop_kpis = pd.read_csv("shop_kpis.csv", parse_dates=["date"])
    return dealers, kpi, shops, shop_kpis

dealers, kpi, shops, shop_kpis = load()
brand_header()

# ======== Sidebar (Exec + Drill-down toggle) ========
view = st.sidebar.radio("View", ["Executive Overview", "Dealer Drill-down"], index=0)
region = st.sidebar.selectbox("Region", ["All"] + sorted(dealers["region"].unique()))
stage = st.sidebar.selectbox("Journey Stage", ["All"] + sorted(dealers["journey_stage"].unique()))
compliance_band = st.sidebar.selectbox("Compliance Band", ["All","<70%","70–85%","85%+"])

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

# ======== Helper: network-weighted aggregation ========
sub = kpi[kpi["dealer_id"].isin(filtered_dealers["dealer_id"])]
if sub.empty:
    st.warning("No data for the current filter selection.")
    st.stop()

latest = sub.sort_values("date").groupby("dealer_id").tail(1)
weights = latest.set_index("dealer_id")["express_lane_ros"]

def wavg(col):
    v = latest.set_index("dealer_id")[col].reindex(weights.index)
    return float(np.average(v, weights=weights))

# ======== Executive Overview ========
if view == "Executive Overview":
    # KPI Cards (two rows)
    r1 = st.columns(6)
    r1[0].markdown("<div class='metric-card'>Parts Loyalty<br><h3 style='color:"+DEKRA+"'>"+f"{wavg('parts_loyalty'):.1%}"+"</h3></div>", unsafe_allow_html=True)
    r1[1].markdown("<div class='metric-card'>Auto Repl.<br><h3 style='color:"+DEKRA+"'>"+f"{wavg('auto_replenishment'):.1%}"+"</h3></div>", unsafe_allow_html=True)
    r1[2].markdown("<div class='metric-card'>Maint. Penetration<br><h3 style='color:"+MOPAR+"'>"+f"{wavg('maintenance_penetration'):.1%}"+"</h3></div>", unsafe_allow_html=True)
    r1[3].markdown("<div class='metric-card'>Bulk Oil Penetration<br><h3 style='color:"+MOPAR+"'>"+f"{wavg('bulk_oil_penetration'):.1%}"+"</h3></div>", unsafe_allow_html=True)
    r1[4].markdown("<div class='metric-card'>Service Lane Utilization<br><h3 style='color:"+DEKRA+"'>"+f"{wavg('service_lane_utilization'):.1%}"+"</h3></div>", unsafe_allow_html=True)
    r1[5].markdown("<div class='metric-card'>Express Lane ROs (wk)<br><h3 style='color:"+DEKRA+"'>"+f"{int(weights.sum()):,}"+"</h3></div>", unsafe_allow_html=True)

    r2 = st.columns(4)
    r2[0].markdown("<div class='metric-card'>Time‑in‑Bay (Maint.)<br><h3 style='color:"+MOPAR+"'>"+f"{wavg('time_in_bay_maint_min'):.1f} min"+"</h3></div>", unsafe_allow_html=True)
    r2[1].markdown("<div class='metric-card'>Time‑in‑Bay (Advanced)<br><h3 style='color:"+MOPAR+"'>"+f"{wavg('time_in_bay_adv_min'):.1f} min"+"</h3></div>", unsafe_allow_html=True)
    r2[2].markdown("<div class='metric-card'>Total Wait Time<br><h3 style='color:"+MOPAR+"'>"+f"{wavg('total_wait_min'):.1f} min"+"</h3></div>", unsafe_allow_html=True)
    r2[3].markdown("<div class='metric-card'>Retention Rate<br><h3 style='color:"+DEKRA+"'>"+f"{wavg('retention_rate'):.1%}"+"</h3></div>", unsafe_allow_html=True)

    st.markdown("### Customer Service Journey Mix")
    counts = filtered_dealers["journey_stage"].value_counts().reindex(sorted(dealers["journey_stage"].unique()), fill_value=0)
    fig0, ax0 = plt.subplots(figsize=(6,3))
    ax0.bar(counts.index, counts.values, color=MOPAR); ax0.set_ylabel("Dealers"); ax0.set_xlabel("Stage")
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

    c = st.columns(3)
    f1,a1 = plt.subplots(); a1.plot(network["date"], network["parts_loyalty"], color=DEKRA); a1.set_title("Parts Loyalty"); c[0].pyplot(f1)
    f2,a2 = plt.subplots(); a2.plot(network["date"], network["maintenance_penetration"], color=MOPAR); a2.set_title("Maint. Penetration"); c[1].pyplot(f2)
    f3,a3 = plt.subplots(); a3.plot(network["date"], network["service_lane_utilization"], color=DEKRA); a3.set_title("Service Lane Utilization"); c[2].pyplot(f3)
    c = st.columns(3)
    f4,a4 = plt.subplots(); a4.plot(network["date"], network["time_in_bay_maint_min"], color=MOPAR); a4.set_title("Time-in-Bay (Maint.)"); c[0].pyplot(f4)
    f5,a5 = plt.subplots(); a5.plot(network["date"], network["total_wait_min"], color=MOPAR); a5.set_title("Total Wait"); c[1].pyplot(f5)
    f6,a6 = plt.subplots(); a6.plot(network["date"], network["retention_rate"], color=DEKRA); a6.set_title("Retention"); c[2].pyplot(f6)

    st.markdown("### Top Dealers — Composite Score")
    latest2 = sub.sort_values("date").groupby("dealer_id").tail(1)
    rank = latest2.merge(dealers[["dealer_id","dealer_name","region","journey_stage"]], on="dealer_id", how="left")
    def normalize(s, invert=False):
        v = s.astype(float)
        if invert: v = -v
        return (v - v.min())/(v.max()-v.min()+1e-9)
    rank["score"] = (
        normalize(rank["parts_loyalty"]) + normalize(rank["auto_replenishment"]) + normalize(rank["maintenance_penetration"]) +
        normalize(rank["bulk_oil_penetration"]) + normalize(rank["service_lane_utilization"]) +
        normalize(rank["time_in_bay_maint_min"], True) + normalize(rank["total_wait_min"], True) +
        normalize(rank["retention_rate"]) + normalize(rank["compliance_score"])
    ) / 9.0
    st.dataframe(rank.sort_values("score", ascending=False)[["dealer_id","dealer_name","region","journey_stage","score"]].head(25))

# ======== Dealer Drill-down ========
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
        shop_hist = pd.read_csv("shop_kpis.csv", parse_dates=["date"])
        shop_hist = shop_hist[shop_hist["dealer_id"]==sel].sort_values("date")
        f5,a5 = plt.subplots(); a5.plot(shop_hist["date"], shop_hist["utilization"], color=DEKRA); a5.set_ylabel("Bay Utilization"); st.pyplot(f5)
        f6,a6 = plt.subplots(); a6.plot(shop_hist["date"], shop_hist["ro_per_bay_hour"], color=MOPAR); a6.set_ylabel("RO per Bay Hour"); st.pyplot(f6)
