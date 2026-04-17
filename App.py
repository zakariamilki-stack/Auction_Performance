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

    # =====================================================
    # LOAD DATA
    # =====================================================
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

    # =====================================================
    # REQUIRED CHECK
    # =====================================================
    required_cols = [
        "CURRENT SALE STATUS",
        "SALE TYPE",
        "NET PRICE",
        "SOLD MONTH",
        "MAKE",
        "MODEL",
        "VERSION",
        "MODEL YEAR"
    ]

    missing = [c for c in required_cols if c not in df.columns]

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
    df["SoldMonth"] = df["SOLD MONTH"].astype(str).str.upper().str.strip()

    df = df.dropna(subset=["NetPrice", "SoldMonth"])

    # =====================================================
    # MONTH ORDER FIX
    # =====================================================
    month_order = {
        "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
        "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
        "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12
    }

    df["MonthOrder"] = df["SoldMonth"].map(month_order)
    df = df.dropna(subset=["MonthOrder"])

    # =====================================================
    # FILTERS (CASCADE)
    # =====================================================
    st.subheader("🔎 Filters")

    c1, c2, c3, c4, c5 = st.columns(5)

    # AUCTION
    auction = c1.selectbox("Auction", ["All"] + sorted(df["Auction"].dropna().unique()))
    df_f = df.copy()

    if auction != "All":
        df_f = df_f[df_f["Auction"] == auction]

    # MAKE
    make = c2.selectbox("Make", ["All"] + sorted(df_f["MAKE"].dropna().unique()))
    if make != "All":
        df_f = df_f[df_f["MAKE"] == make]

    # MODEL
    model = c3.selectbox("Model", ["All"] + sorted(df_f["MODEL"].dropna().unique()))
    if model != "All":
        df_f = df_f[df_f["MODEL"] == model]

    # VERSION
    version = c4.selectbox("Version", ["All"] + sorted(df_f["VERSION"].dropna().unique()))
    if version != "All":
        df_f = df_f[df_f["VERSION"] == version]

    # MODEL YEAR
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
    # TREND (SORTED MONTHS + LABELS)
    # =====================================================
    st.subheader("📈 Monthly Trend")

    trend = df_f.groupby(["SoldMonth", "MonthOrder"]).agg(
        Qty=("NetPrice", "count"),
        AvgNet=("NetPrice", "mean")
    ).reset_index()

    trend = trend.sort_values("MonthOrder")

    fig = go.Figure()

    # AVG NET (TOP LABEL)
    fig.add_trace(go.Scatter(
        x=trend["SoldMonth"],
        y=trend["AvgNet"],
        mode="lines+markers+text",
        name="Avg Net Price",
        text=[f"{v:,.0f}" for v in trend["AvgNet"]],
        textposition="top center"
    ))

    # QTY (BOTTOM LABEL)
    fig.add_trace(go.Scatter(
        x=trend["SoldMonth"],
        y=trend["Qty"],
        mode="lines+markers+text",
        name="Qty Sold",
        text=trend["Qty"],
        textposition="bottom center"
    ))

    fig.update_layout(
        height=500,
        xaxis_title="Month",
        yaxis_title="Value",
        legend_title="Metrics"
    )

    st.plotly_chart(fig, use_container_width=True)

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
