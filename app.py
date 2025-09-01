
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Mopar KPI Dashboard — Demo", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("kpi_series.csv", parse_dates=["date"])

df = load_data()

st.title("📊 Mopar KPI Dashboard — Demo")

st.sidebar.header("Targets")
target_conv = st.sidebar.slider("Service Conversion Target", 0.3, 0.95, 0.70, 0.01)
target_pvr = st.sidebar.slider("Accessory PVR Target ($)", 0, 1500, 450, 10)
target_csi = st.sidebar.slider("CSI Target", 60, 100, 90, 1)

# KPI Metrics
latest = df.iloc[-1]
cols = st.columns(3)
cols[0].metric("Service Conversion", f"{latest['service_conv']:.1%}", delta=f"{(latest['service_conv']-0.6):+.1%}")
cols[1].metric("Accessory PVR", f"${latest['pvr']:.0f}", delta=f"${(latest['pvr']-350):+.0f}")
cols[2].metric("CSI", f"{latest['csi']:.1f}", delta=f"{(latest['csi']-85):+.1f}")

# Charts
st.subheader("Service Conversion Trend")
fig1, ax1 = plt.subplots()
ax1.plot(df["date"], df["service_conv"])
ax1.axhline(target_conv, linestyle="--", color="red")
ax1.set_ylabel("Conversion Rate")
st.pyplot(fig1)

st.subheader("Accessory PVR Trend")
fig2, ax2 = plt.subplots()
ax2.plot(df["date"], df["pvr"])
ax2.axhline(target_pvr, linestyle="--", color="red")
ax2.set_ylabel("Accessory $ per Vehicle")
st.pyplot(fig2)

st.subheader("CSI Trend")
fig3, ax3 = plt.subplots()
ax3.plot(df["date"], df["csi"])
ax3.axhline(target_csi, linestyle="--", color="red")
ax3.set_ylabel("CSI")
st.pyplot(fig3)

st.subheader("What-if ROI Estimator")
conv_uplift = st.slider("Expected Conv. Uplift (pp)", 0.0, 0.20, 0.05, 0.01)
pvr_uplift = st.slider("Expected PVR Uplift ($)", 0, 500, 75, 5)
gross_per_ro = st.slider("Gross per Approved RO ($)", 20, 400, 120, 5)

base_ros = 1000
approved_ros = latest["service_conv"] * base_ros
approved_ros_uplift = (latest["service_conv"] + conv_uplift) * base_ros - approved_ros
incremental_gross_service = approved_ros_uplift * gross_per_ro
incremental_gross_accessory = pvr_uplift * 200

st.write(f"**Incremental Gross (Service):** ${incremental_gross_service:,.0f}")
st.write(f"**Incremental Gross (Accessory):** ${incremental_gross_accessory:,.0f}")
st.success(f"**Total Estimated Incremental Gross:** ${incremental_gross_service + incremental_gross_accessory:,.0f} (demo only).")
