# =====================================================
# AUCTION INTELLIGENCE PLATFORM V1
# Developed by Zakaria Milki
# =====================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from io import BytesIO

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Auction Intelligence System", layout="wide")

st.title("📊 Auction Intelligence Platform v1")

# =====================================================
# LOAD DATA (shared)
# =====================================================
file_path = "https://raw.githubusercontent.com/zakariamilki-stack/Auctiondata/refs/heads/main/2026YTD-PERFORMANCE.xlsx"

@st.cache_data
def load_data():
    df = pd.read_excel(file_path)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ", regex=False)
        .str.replace("\t", " ", regex=False)
    )

    for col in df.columns:
        if "SOLD" in col and "MONTH" in col:
            df.rename(columns={col: "SOLD MONTH"}, inplace=True)

    df["CURRENT SALE STATUS"] = df["CURRENT SALE STATUS"].astype(str).str.upper().str.strip()
    df = df[df["CURRENT SALE STATUS"] == "SOLD"].copy()

    df["NET PRICE"] = pd.to_numeric(df["NET PRICE"], errors="coerce")
    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]

    return df

df = load_data()

# =====================================================
# SIDEBAR NAV
# =====================================================
page = st.sidebar.radio("Navigation", [
    "📊 Overview",
    "🤖 AI Price Engine",
    "📦 Dealer Performance",
    "📉 Residual Tracking",
    "⚖️ Sell vs Hold AI"
])

# =====================================================
# KM COLUMN DETECTION
# =====================================================
km_col = None
for col in df.columns:
    if "KM" in col or "MILE" in col or "ODOM" in col:
        km_col = col
        break

# =====================================================
# ================= PAGE 1 (LOCKED EXACT) =================
# =====================================================
if page == "📊 Overview":

    st.subheader("🔎 Filters")

    c1, c2, c3 = st.columns(3)

    make = c1.selectbox("Make", ["All"] + sorted(df["MAKE"].dropna().unique()))
    model = c2.selectbox("Model", ["All"] + sorted(df["MODEL"].dropna().unique()))
    year = c3.selectbox("Year", ["All"] + sorted(df["MODEL YEAR"].dropna().unique()))

    df_f = df.copy()

    if make != "All":
        df_f = df_f[df_f["MAKE"] == make]
    if model != "All":
        df_f = df_f[df_f["MODEL"] == model]
    if year != "All":
        df_f = df_f[df_f["MODEL YEAR"] == year]

    st.subheader("📌 KPIs")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units", len(df_f))
    col2.metric("Avg Price", f"AED {df_f['NetPrice'].mean():,.0f}")
    col3.metric("Max Price", f"AED {df_f['NetPrice'].max():,.0f}")
    col4.metric("Min Price", f"AED {df_f['NetPrice'].min():,.0f}")

    st.subheader("📈 Trend")

    trend = df_f.groupby("Auction")['NetPrice'].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend["Auction"], y=trend["NetPrice"]))

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_f, use_container_width=True)

# =====================================================
# ================= PAGE 2 AI ENGINE =================
# =====================================================
elif page == "🤖 AI Price Engine":

    st.subheader("🚗 Price Prediction Engine")

    if km_col is None:
        st.error("KM column not found")
        st.stop()

    df_ml = df.dropna(subset=[km_col, "NetPrice"]).copy()

    c1, c2, c3 = st.columns(3)

    make = c1.selectbox("Make", sorted(df_ml["MAKE"].unique()))
    year = c2.selectbox("Year", sorted(df_ml["MODEL YEAR"].unique()))
    km_input = c3.number_input("KM", min_value=0, step=1000)

    filtered = df_ml[(df_ml["MAKE"] == make) & (df_ml["MODEL YEAR"] == year)]

    if len(filtered) < 20:
        st.warning("Not enough data")
        st.stop()

    X = filtered[[km_col]]
    y = filtered["NetPrice"]

    rf_model = RandomForestRegressor(n_estimators=120, random_state=42)
    rf_model.fit(X, y)

    pred = rf_model.predict(np.array([[km_input]]))[0]

    st.success(f"Predicted Price: AED {pred:,.0f}")

# =====================================================
# ================= PAGE 3 DEALER PERF =================
# =====================================================
elif page == "📦 Dealer Performance":

    st.subheader("Dealer / Auction Performance")

    perf = df.groupby("Auction").agg(
        Units=("NetPrice", "count"),
        AvgPrice=("NetPrice", "mean"),
        TotalValue=("NetPrice", "sum")
    ).reset_index()

    st.dataframe(perf)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=perf["Auction"], y=perf["TotalValue"]))
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# ================= PAGE 4 RESIDUAL =================
# =====================================================
elif page == "📉 Residual Tracking":

    st.subheader("Residual Value Tracking")

    df["AGE"] = 2026 - df["MODEL YEAR"]

    residual = df.groupby("AGE")["NetPrice"].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=residual["AGE"], y=residual["NetPrice"], mode="lines+markers"))

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# ================= PAGE 5 AI DECISION =================
# =====================================================
elif page == "⚖️ Sell vs Hold AI":

    st.subheader("Sell vs Hold Decision Engine")

    sample = df.copy()
    sample["AVG_MARKET"] = sample.groupby("MODEL")["NetPrice"].transform("mean")

    sample["DECISION"] = np.where(sample["NetPrice"] < sample["AVG_MARKET"], "HOLD", "SELL")

    st.dataframe(sample[["MAKE", "MODEL", "NetPrice", "AVG_MARKET", "DECISION"]])
