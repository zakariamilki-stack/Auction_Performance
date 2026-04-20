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

st.title("📊 Auction Intelligence System")

# =====================================================
# LOAD DATA
# =====================================================
file_path = "https://raw.githubusercontent.com/zakariamilki-stack/Auctiondata/main/2026YTD-PERFORMANCE.xlsx"

@st.cache_data
def load_data():
    df = pd.read_excel(file_path)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ", regex=False)
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
# SIDEBAR NAVIGATION
# =====================================================
page = st.sidebar.radio("Navigation", ["📊 Overview", "🤖 AI Price Engine"])

# =====================================================
# COMMON KM COLUMN DETECTION
# =====================================================
km_col = None
for col in df.columns:
    if "KM" in col or "MILE" in col or "ODOM" in col:
        km_col = col
        break

# =====================================================
# PAGE 1 - DASHBOARD
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

    # KPIs
    st.subheader("📌 KPIs")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units", len(df_f))
    col2.metric("Avg Price", f"AED {df_f['NetPrice'].mean():,.0f}")
    col3.metric("Max Price", f"AED {df_f['NetPrice'].max():,.0f}")
    col4.metric("Min Price", f"AED {df_f['NetPrice'].min():,.0f}")

    # Trend
    st.subheader("📈 Trend")

    trend = df_f.groupby("Auction")["NetPrice"].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend["Auction"], y=trend["NetPrice"]))

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_f, use_container_width=True)

# =====================================================
# PAGE 2 - AI PRICE ENGINE
# =====================================================
elif page == "🤖 AI Price Engine":

    st.subheader("🚗 Price Prediction Engine")

    if km_col is None:
        st.error("KM column not found")
        st.stop()

    df_ml = df.dropna(subset=[km_col, "NetPrice"]).copy()
    df_ml[km_col] = pd.to_numeric(df_ml[km_col], errors="coerce")
    df_ml["NetPrice"] = pd.to_numeric(df_ml["NetPrice"], errors="coerce")
    df_ml = df_ml.dropna()

    c1, c2, c3 = st.columns(3)

    make = c1.selectbox("Make", sorted(df_ml["MAKE"].unique()))
    year = c2.selectbox("Year", sorted(df_ml["MODEL YEAR"].unique()))
    km_input = c3.number_input("KM", min_value=0, step=1000)

    filtered = df_ml[(df_ml["MAKE"] == make) & (df_ml["MODEL YEAR"] == year)]

    if len(filtered) < 20:
        st.warning("Not enough data for prediction")
        st.stop()

    # MODEL
    X = filtered[[km_col]]
    y = filtered["NetPrice"]

    model = RandomForestRegressor(n_estimators=120, random_state=42)
    model.fit(X, y)

    pred = model.predict([[km_input]])[0]

    all_preds = [tree.predict([[km_input]])[0] for tree in model.estimators_]

    low = np.percentile(all_preds, 10)
    high = np.percentile(all_preds, 90)

    # OUTPUT
    st.success(f"""
    💰 Predicted Price: AED {pred:,.0f}  
    Range: AED {low:,.0f} - AED {high:,.0f}
    """)

    # MARKET VIEW
    market_avg = filtered["NetPrice"].mean()

    if pred < market_avg * 0.95:
        st.info("🟢 Undervalued")
    elif pred > market_avg * 1.05:
        st.error("🔴 Overpriced")
    else:
        st.warning("🟡 Fair Market")

    # CHART
    st.subheader("KM vs Price")
    st.scatter_chart(filtered[[km_col, "NetPrice"]].rename(columns={km_col: "KM"}))
