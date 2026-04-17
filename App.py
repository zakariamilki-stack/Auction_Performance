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

    # FIX: messy SOLD MONTH column
    for col in df.columns:
        if "SOLD" in col and "MONTH" in col:
            df.rename(columns={col: "SOLD MONTH"}, inplace=True)

    st.write("📌 Columns detected:", df.columns.tolist())

    # =====================================================
    # REQUIRED COLUMNS CHECK
    # =====================================================
    required_cols = [
        "CURRENT SALE STATUS",
        "SALE TYPE",
        "NET PRICE",
        "SOLD MONTH",
        "MAKE",
        "MODEL",
        "VERSION"
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
    # CREATE FIELDS
    # =====================================================
    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]
    df["SoldMonth"] = df["SOLD MONTH"].astype(str)

    df = df.dropna(subset=["SoldMonth", "NetPrice"])

    # =====================================================
    # KPIs
    # =====================================================
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units Sold", len(df))
    col2.metric("Avg Net Price", round(df["NetPrice"].mean(), 2))
    col3.metric("Max Net Price", df["NetPrice"].max())
    col4.metric("Min Net Price", df["NetPrice"].min())

    # =====================================================
    # TREND (WITH LABELS)
    # =====================================================
    st.subheader("📈 Monthly Performance")

    trend = df.groupby("SoldMonth")["NetPrice"].count().reset_index()
    trend.columns = ["Month", "Units"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=trend["Month"],
        y=trend["Units"],
        mode="lines+markers+text",
        text=trend["Units"],
        textposition="top center"
    ))

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # FILTERS (CASCADE FIX)
    # =====================================================
    st.subheader("🔎 Data Explorer")

    col1, col2, col3, col4 = st.columns(4)

    # 1. MAKE
    make_filter = col1.selectbox(
        "Make",
        ["All"] + sorted(df["MAKE"].dropna().unique())
    )

    df_filtered = df.copy()

    if make_filter != "All":
        df_filtered = df_filtered[df_filtered["MAKE"] == make_filter]

    # 2. MODEL (depends on MAKE)
    model_filter = col2.selectbox(
        "Model",
        ["All"] + sorted(df_filtered["MODEL"].dropna().unique())
    )

    if model_filter != "All":
        df_filtered = df_filtered[df_filtered["MODEL"] == model_filter]

    # 3. VERSION (depends on MAKE + MODEL)
    version_filter = col3.selectbox(
        "Version",
        ["All"] + sorted(df_filtered["VERSION"].dropna().unique())
    )

    if version_filter != "All":
        df_filtered = df_filtered[df_filtered["VERSION"] == version_filter]

    # 4. AUCTION (independent)
    auction_filter = col4.selectbox(
        "Auction",
        ["All"] + sorted(df["Auction"].dropna().unique())
    )

    if auction_filter != "All":
        df_filtered = df_filtered[df_filtered["Auction"] == auction_filter]

    # =====================================================
    # OUTPUT TABLE
    # =====================================================
    st.dataframe(df_filtered, use_container_width=True)

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
        data=convert_to_excel(df),
        file_name="clean_auction_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
