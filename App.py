import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Auction Intelligence Dashboard", layout="wide")

st.title("📊 Auction Intelligence Dashboard")

# =====================================================
# UPLOAD
# =====================================================
uploaded_file = st.file_uploader("Upload Sale Data Excel", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # =====================================================
    # CLEAN COLUMNS
    # =====================================================
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ", regex=False)
        .str.replace("\t", " ", regex=False)
    )

    # FIX SOLD MONTH
    for col in df.columns:
        if "SOLD" in col and "MONTH" in col:
            df.rename(columns={col: "SOLD MONTH"}, inplace=True)

    required = [
        "CURRENT SALE STATUS",
        "SALE TYPE",
        "NET PRICE",
        "SOLD MONTH",
        "MAKE",
        "MODEL",
        "VERSION",
        "MODEL YEAR"
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

    # =====================================================
    # CLEAN DATA
    # =====================================================
    df["CURRENT SALE STATUS"] = df["CURRENT SALE STATUS"].astype(str).str.strip().str.upper()
    df = df[df["CURRENT SALE STATUS"] == "SOLD"].copy()

    df["NET PRICE"] = pd.to_numeric(df["NET PRICE"], errors="coerce")

    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]
    df["SoldMonth"] = df["SOLD MONTH"].astype(str)

    df = df.dropna(subset=["NetPrice", "SoldMonth"])

    # =====================================================
    # FILTERS (CASCADE)
    # =====================================================
    st.subheader("🔎 Filters")

    c1, c2, c3, c4, c5 = st.columns(5)

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

    # =====================================================
    # KPIs
    # =====================================================
    st.subheader("📌 KPIs")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units Sold", len(df_f))
    col2.metric("Avg Net Price", round(df_f["NetPrice"].mean(), 2))
    col3.metric("Max Net Price", df_f["NetPrice"].max())
    col4.metric("Min Net Price", df_f["NetPrice"].min())

    # =====================================================
    # AUCTION COMPARISON CHART (NEW)
    # =====================================================
    st.subheader("📊 Auction Comparison (Qty + Avg Price)")

    auction_trend = df_f.groupby(["SoldMonth", "Auction"]).agg(
        Qty=("NetPrice", "count"),
        AvgPrice=("NetPrice", "mean")
    ).reset_index()

    fig = go.Figure()

    for a in auction_trend["Auction"].unique():
        temp = auction_trend[auction_trend["Auction"] == a]

        fig.add_trace(go.Scatter(
            x=temp["SoldMonth"],
            y=temp["Qty"],
            mode="lines+markers",
            name=f"{a} - Qty"
        ))

    fig.update_layout(
        height=450,
        xaxis_title="Month",
        yaxis_title="Units Sold",
        title="Auction Performance Comparison"
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # SMART INSIGHT BOX (NEW)
    # =====================================================
    st.subheader("🧠 Smart Insight")

    if len(df_f) > 0:

        best_auction = (
            df_f.groupby("Auction")["NetPrice"]
            .count()
            .sort_values(ascending=False)
            .head(1)
        )

        best_name = best_auction.index[0]
        best_value = best_auction.values[0]

        avg_market = df_f["NetPrice"].mean()

        st.info(
            f"""
            🔹 Best Performing Auction: {best_name} ({best_value} units)

            🔹 Average Market Price: {round(avg_market,2)}

            🔹 Observation:
            {'Market is strong and stable' if avg_market > df_f['NetPrice'].median() else 'Prices are slightly under pressure'}
            """
        )

    # =====================================================
    # TABLE
    # =====================================================
    st.dataframe(df_f, use_container_width=True)

    # =====================================================
    # DOWNLOAD
    # =====================================================
    def to_excel(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="CleanData")
        return output.getvalue()

    st.download_button(
        "⬇️ Download Clean Data",
        data=to_excel(df_f),
        file_name="auction_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
