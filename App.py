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

st.title("📊 Auction Intelligence Platform v1 - ZM")

# =====================================================
# LOAD DATA (shared)
# =====================================================
file_path = r"https://raw.githubusercontent.com/zakariamilki-stack/Auctiondata/refs/heads/main/2026YTD-PERFORMANCE.xlsx"

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
# ================= PAGE 1 (EXACT ORIGINAL - LOCKED) =================
# =====================================================
if page == "📊 Overview":

    st.subheader("🔎 Filters")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    auction = c1.selectbox("Auction", ["All"] + sorted(df["Auction"].dropna().unique()))
    df_f = df.copy()
    if auction != "All":
        df_f = df_f[df_f["Auction"] == auction]

    make = c2.selectbox("Make", ["All"] + sorted(df_f["MAKE"].dropna().unique()))
    if make != "All":
        df_f = df_f[df_f["MAKE"] == make]

    model = c3.selectbox("Model", ["All"] + sorted(df_f["MODEL"].dropna().unique()))
    if model != "All":
        df_f = df_f[df_f["MODEL"] == model]

    version = c4.selectbox("Version", ["All"] + sorted(df_f["VERSION"].dropna().unique()))
    if version != "All":
        df_f = df_f[df_f["VERSION"] == version]

    year = c5.selectbox("Model Year", ["All"] + sorted(df_f["MODEL YEAR"].dropna().unique()))
    if year != "All":
        df_f = df_f[df_f["MODEL YEAR"] == year]

    list_type = c6.selectbox("List Type", ["All"] + sorted(df_f["LIST TYPE"].dropna().unique()))
    if list_type != "All":
        df_f = df_f[df_f["LIST TYPE"] == list_type]

    def format_aed(value):
        if pd.isna(value):
            return "-"
        return f"AED {value:,.0f}"

    st.subheader("📌 KPIs")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units Sold", f"{len(df_f):,}")
    col2.metric("Avg Net Price", format_aed(df_f["NetPrice"].mean()))
    col3.metric("Max Net Price", format_aed(df_f["NetPrice"].max()))
    col4.metric("Min Net Price", format_aed(df_f["NetPrice"].min()))

    st.subheader("📈 Monthly Trend")

    trend = df_f.groupby(["MonthOrder", "SoldMonth"]).agg(
        Qty=("NetPrice", "count"),
        AvgNet=("NetPrice", "mean")
    ).reset_index().sort_values("MonthOrder")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=trend["SoldMonth"],
        y=trend["AvgNet"],
        mode="lines+markers+text",
        name="Avg Net Price",
        text=[f"{v:,.0f}" for v in trend["AvgNet"]],
        textposition="top center"
    ))

    fig.add_trace(go.Scatter(
        x=trend["SoldMonth"],
        y=trend["Qty"],
        mode="lines+markers+text",
        name="Qty Sold",
        text=trend["Qty"],
        textposition="bottom center"
    ))

    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧠 Smart Insights")

    if len(df_f) > 0:

        best_auction = df_f.groupby("Auction")["NetPrice"].count().idxmax()
        best_count = df_f.groupby("Auction")["NetPrice"].count().max()

        avg_price = df_f["NetPrice"].mean()
        median_price = df_f["NetPrice"].median()

        trend_direction = "increasing" if len(trend) > 1 and trend["Qty"].iloc[-1] > trend["Qty"].iloc[0] else "declining"

        st.info(f"""
🔹 Best Auction: {best_auction} ({best_count} units)

🔹 Avg Price: {format_aed(avg_price)}

🔹 Market Insight:
{'Prices are strong vs median' if avg_price > median_price else 'Prices slightly under pressure'}

🔹 Volume Trend:
Sales are {trend_direction} over time
""")

    st.dataframe(df_f, use_container_width=True)

    def to_excel(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button(
        "⬇️ Download Clean Data",
        data=to_excel(df_f),
        file_name="auction_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =====================================================
# ================= PAGE 2 AI ENGINE =================
# =====================================================
elif page == "🤖 AI Price Engine - Developed by ZM":

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
elif page == "⚖️ Sell vs Hold AI- BY ZM":

    st.subheader("Sell vs Hold Decision Engine")

    sample = df.copy()
    sample["AVG_MARKET"] = sample.groupby("MODEL")["NetPrice"].transform("mean")

    sample["DECISION"] = np.where(sample["NetPrice"] < sample["AVG_MARKET"], "HOLD", "SELL")

    st.dataframe(sample[["MAKE", "MODEL", "NetPrice", "AVG_MARKET", "DECISION"]])
