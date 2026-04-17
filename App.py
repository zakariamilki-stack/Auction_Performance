import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Auction Dashboard", layout="wide")

st.title("📊 Auction Performance Dashboard")

# =====================================================
# UPLOAD FILE
# =====================================================
uploaded_file = st.file_uploader("Upload Sale Data Excel", type=["xlsx"])

if uploaded_file:

    # =====================================================
    # LOAD DATA
    # =====================================================
    df = pd.read_excel(uploaded_file)

    # =====================================================
    # CLEAN COLUMN NAMES
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
    # CLEAN STATUS
    # =====================================================
    df["CURRENT SALE STATUS"] = (
        df["CURRENT SALE STATUS"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df = df[df["CURRENT SALE STATUS"] == "SOLD"].copy()

    # =====================================================
    # CLEAN NUMERIC
    # =====================================================
    df["NET PRICE"] = pd.to_numeric(df["NET PRICE"], errors="coerce")

    # =====================================================
    # FIELDS
    # =====================================================
    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]
    df["SoldMonth"] = df["SOLD MONTH"].astype(str)

    df = df.dropna(subset=["SoldMonth", "NetPrice"])

    # =====================================================
    # FILTERS (CASCADE FIXED)
    # =====================================================
    st.subheader("🔎 Data Explorer")

    col1, col2, col3, col4 = st.columns(4)

    # MAKE
    make_filter = col1.selectbox("Make", ["All"] + sorted(df["MAKE"].dropna().unique()))

    df_f = df.copy()
    if make_filter != "All":
        df_f = df_f[df_f["MAKE"] == make_filter]

    # MODEL
    model_filter = col2.selectbox("Model", ["All"] + sorted(df_f["MODEL"].dropna().unique()))
    if model_filter != "All":
        df_f = df_f[df_f["MODEL"] == model_filter]

    # VERSION
    version_filter = col3.selectbox("Version", ["All"] + sorted(df_f["VERSION"].dropna().unique()))
    if version_filter != "All":
        df_f = df_f[df_f["VERSION"] == version_filter]

    # MODEL YEAR (NEW)
    year_filter = col4.selectbox("Model Year", ["All"] + sorted(df["MODEL YEAR"].dropna().unique()))
    if year_filter != "All":
        df_f = df_f[df_f["MODEL YEAR"] == year_filter]

    # =====================================================
    # KPIs (based on FILTERED DATA)
    # =====================================================
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units Sold", len(df_f))
    col2.metric("Avg Net Price", round(df_f["NetPrice"].mean(), 2))
    col3.metric("Max Net Price", df_f["NetPrice"].max())
    col4.metric("Min Net Price", df_f["NetPrice"].min())

    # =====================================================
    # TREND (NOW CONNECTED TO FILTERS)
    # =====================================================
    st.subheader("📈 Monthly Performance")

    trend = df_f.groupby("SoldMonth").agg(
        Qty=("NetPrice", "count"),
        AvgNet=("NetPrice", "mean")
    ).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=trend["SoldMonth"],
        y=trend["Qty"],
        mode="lines+markers+text",
        text=[
            f"Qty: {q}<br>Avg: {a:,.0f}"
            for q, a in zip(trend["Qty"], trend["AvgNet"])
        ],
        textposition="top center"
    ))

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Quantity Sold",
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # TABLE
    # =====================================================
    st.dataframe(df_f, use_container_width=True)

    # =====================================================
    # DOWNLOAD
    # =====================================================
    def convert_to_excel(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="CleanData")
        return output.getvalue()

    st.download_button(
        "⬇️ Download Clean Data",
        data=convert_to_excel(df_f),
        file_name="clean_auction_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
