
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Mopar KPI Network Dashboard — Demo", layout="wide")

@st.cache_data
def load_data():
    dealers = pd.read_csv("dealers.csv")
    kpi = pd.read_csv("kpi_timeseries.csv", parse_dates=["date"])
    return dealers, kpi

dealers, kpi = load_data()

st.sidebar.title("Filters")
regions = ["All"] + sorted(dealers["region"].unique().tolist())
region = st.sidebar.selectbox("Region", regions, index=0)

stages = ["All"] + sorted(dealers["journey_stage"].unique().tolist())
stage = st.sidebar.selectbox("Customer Journey Stage", stages, index=0)

compliance_band = st.sidebar.selectbox("Compliance Band", ["All","<70%","70-85%","85%+"], index=0)

dealer_search = st.sidebar.text_input("Search Dealer Name / ID")

mask = pd.Series(True, index=dealers.index)
if region != "All":
    mask &= dealers["region"].eq(region)
if stage != "All":
    mask &= dealers["journey_stage"].eq(stage)
if dealer_search:
    s = dealer_search.lower()
    mask &= dealers["dealer_name"].str.lower().str.contains(s) | dealers["dealer_id"].str.lower().str.contains(s)
filtered_dealers = dealers[mask].copy()

latest = kpi.sort_values("date").groupby("dealer_id").tail(1)[["dealer_id","compliance_score"]]
tmp = filtered_dealers.merge(latest, on="dealer_id", how="left")
if compliance_band != "All":
    if compliance_band == "<70%":
        tmp = tmp[tmp["compliance_score"] < 0.70]
    elif compliance_band == "70-85%":
        tmp = tmp[(tmp["compliance_score"] >= 0.70) & (tmp["compliance_score"] < 0.85)]
    else:
        tmp = tmp[tmp["compliance_score"] >= 0.85]
filtered_dealers = tmp.drop(columns=["compliance_score"])

st.sidebar.write(f"Showing {len(filtered_dealers)} of {len(dealers)} dealerships")

sub = kpi[kpi["dealer_id"].isin(filtered_dealers["dealer_id"])]
if sub.empty:
    st.warning("No data for the current filter selection.")
    st.stop()

grp_latest = sub.sort_values("date").groupby("dealer_id").tail(1)
weights = grp_latest.set_index("dealer_id")["express_lane_ros"]

def agg(col):
    vals = grp_latest.set_index("dealer_id")[col].reindex(weights.index)
    return float(np.average(vals, weights=weights))

parts_loyalty = agg("parts_loyalty")
auto_repl = agg("auto_replenishment")
maint_pen = agg("maintenance_penetration")
bulk_oil = agg("bulk_oil_penetration")
express_ros = weights.sum()
util = agg("service_lane_utilization")
tib_maint = agg("time_in_bay_maint_min")
wait_total = agg("total_wait_min")
retention = agg("retention_rate")
compliance = agg("compliance_score")

st.title("Mopar KPI Network Dashboard — Demo")
st.caption(f"Dealerships: {len(filtered_dealers)} | Region: {region} | Stage: {stage} | Compliance: {compliance_band}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Parts Loyalty", f"{parts_loyalty:.1%}")
c1.metric("Auto Replenishment", f"{auto_repl:.1%}")
c2.metric("Maintenance Penetration", f"{maint_pen:.1%}")
c2.metric("Bulk Oil Penetration", f"{bulk_oil:.1%}")
c3.metric("Express Lane ROs (weekly)", f"{express_ros:,.0f}")
c3.metric("Service Lane Utilization", f"{util:.1%}")
c4.metric("Time-in-Bay (Maint.)", f"{tib_maint:.1f} min")
c4.metric("Total Customer Wait", f"{wait_total:.1f} min")

st.markdown("---")

st.subheader("Customer Service Journey — Dealer Distribution")
counts = filtered_dealers["journey_stage"].value_counts().reindex(sorted(dealers["journey_stage"].unique()), fill_value=0)
fig0, ax0 = plt.subplots()
ax0.bar(counts.index, counts.values)
ax0.set_ylabel("Dealerships")
ax0.set_xlabel("Journey Stage")
st.pyplot(fig0)

st.subheader("Network Trends (weighted by Express Lane ROs)")
network = sub.groupby("date").apply(
    lambda x: pd.Series({
        "parts_loyalty": np.average(x["parts_loyalty"], weights=x["express_lane_ros"]),
        "auto_replenishment": np.average(x["auto_replenishment"], weights=x["express_lane_ros"]),
        "maintenance_penetration": np.average(x["maintenance_penetration"], weights=x["express_lane_ros"]),
        "bulk_oil_penetration": np.average(x["bulk_oil_penetration"], weights=x["express_lane_ros"]),
        "service_lane_utilization": np.average(x["service_lane_utilization"], weights=x["express_lane_ros"]),
        "time_in_bay_maint_min": np.average(x["time_in_bay_maint_min"], weights=x["express_lane_ros"]),
        "total_wait_min": np.average(x["total_wait_min"], weights=x["express_lane_ros"]),
        "retention_rate": np.average(x["retention_rate"], weights=x["express_lane_ros"]),
        "compliance_score": np.average(x["compliance_score"], weights=x["express_lane_ros"]),
        "express_lane_ros": x["express_lane_ros"].sum()
    })
).reset_index()

cols = st.columns(3)
fig1, ax1 = plt.subplots()
ax1.plot(network["date"], network["parts_loyalty"])
ax1.set_ylabel("Parts Loyalty"); ax1.set_xlabel("Date")
cols[0].pyplot(fig1)

fig2, ax2 = plt.subplots()
ax2.plot(network["date"], network["service_lane_utilization"])
ax2.set_ylabel("Service Lane Utilization"); ax2.set_xlabel("Date")
cols[1].pyplot(fig2)

fig3, ax3 = plt.subplots()
ax3.plot(network["date"], network["time_in_bay_maint_min"])
ax3.set_ylabel("Time-in-Bay (Maint.)"); ax3.set_xlabel("Date")
cols[2].pyplot(fig3)

cols = st.columns(3)
fig4, ax4 = plt.subplots()
ax4.plot(network["date"], network["maintenance_penetration"])
ax4.set_ylabel("Maintenance Penetration"); ax4.set_xlabel("Date")
cols[0].pyplot(fig4)

fig5, ax5 = plt.subplots()
ax5.plot(network["date"], network["bulk_oil_penetration"])
ax5.set_ylabel("Bulk Oil Penetration"); ax5.set_xlabel("Date")
cols[1].pyplot(fig5)

fig6, ax6 = plt.subplots()
ax6.plot(network["date"], network["retention_rate"])
ax6.set_ylabel("Retention Rate"); ax6.set_xlabel("Date")
cols[2].pyplot(fig6)

st.markdown("---")

st.subheader("Dealer Ranking (latest week)")
latest = sub.sort_values("date").groupby("dealer_id").tail(1)
rank = latest.merge(dealers[["dealer_id","dealer_name","region","journey_stage"]], on="dealer_id", how="left")
def normalize(s, invert=False):
    v = s.astype(float)
    if invert:
        v = -v
    v = (v - v.min())/(v.max()-v.min() + 1e-9)
    return v
rank["score"] = (
    normalize(rank["parts_loyalty"]) + normalize(rank["auto_replenishment"]) + normalize(rank["maintenance_penetration"]) +
    normalize(rank["bulk_oil_penetration"]) + normalize(rank["service_lane_utilization"]) +
    normalize(rank["time_in_bay_maint_min"], invert=True) + normalize(rank["total_wait_min"], invert=True) +
    normalize(rank["retention_rate"]) + normalize(rank["compliance_score"])
) / 9.0
rank = rank.sort_values("score", ascending=False)
show_cols = ["dealer_id","dealer_name","region","journey_stage","score","parts_loyalty","auto_replenishment","maintenance_penetration","bulk_oil_penetration","service_lane_utilization","time_in_bay_maint_min","total_wait_min","retention_rate","compliance_score","express_lane_ros"]
st.dataframe(rank[show_cols].head(50))

st.caption("Synthetic data for demo. KPIs include Mopar Core Four, Express Lane RO growth/utilization, time-in-bay, wait time, retention, and compliance.")

st.markdown("---")
st.subheader("Single Dealer Deep Dive")
sel_dealer = st.selectbox("Select Dealer", sorted(filtered_dealers["dealer_id"].tolist()))
hist = kpi[kpi["dealer_id"]==sel_dealer].sort_values("date")
info = dealers[dealers["dealer_id"]==sel_dealer].iloc[0]
st.write(f"**{info['dealer_name']}** — {info['region']}, {info['state']} • Stage: {info['journey_stage']}")
cA, cB, cC = st.columns(3)
figA, axA = plt.subplots(); axA.plot(hist["date"], hist["parts_loyalty"]); axA.set_ylabel("Parts Loyalty"); axA.set_xlabel("Date"); cA.pyplot(figA)
figB, axB = plt.subplots(); axB.plot(hist["date"], hist["service_lane_utilization"]); axB.set_ylabel("Service Lane Utilization"); axB.set_xlabel("Date"); cB.pyplot(figB)
figC, axC = plt.subplots(); axC.plot(hist["date"], hist["time_in_bay_maint_min"]); axC.set_ylabel("Time-in-Bay (Maint.)"); axC.set_xlabel("Date"); cC.pyplot(figC)
