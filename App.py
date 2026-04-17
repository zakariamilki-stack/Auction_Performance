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

    st.write("📌 Columns detected:", df.columns.tolist())

    # =====================================================
    # REQUIRED CHECK
    # =====================================================
    required_cols = [
        "CURRENT SALE STATUS",
        "SALE TYPE",
        "NET PRICE",
        "SOLD MONTH",
        "MAKE",
        "MODEL YEAR",
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
    # FIELDS
    # =====================================================
    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]
    df["SoldMonth"] = df["SOLD MONTH"].astype(str)

    df = df.dropna(subset=["SoldMonth", "NetPrice"])

    # =====================================================
    # KPIs
    # =====================================================
    units_sold = len(df)
    avg_price = df["NetPrice"].mean()
    max_price = df["NetPrice"].max()
    min_price = df["NetPrice"].min()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units Sold", units_sold)
    col2.metric("Avg Net Price", round(avg_price, 2))
    col3.metric("Max Net Price", max_price)
    col4.metric("Min Net Price", min_price)

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

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Units Sold",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # FILTERS
    # =====================================================
    st.subheader("🔎 Data Explorer")

    col1, col2, col3, col4 = st.columns(4)

    auction_filter = col1.selectbox(
        "Auction",
        ["All"] + sorted(df["Auction"].dropna().unique())
    )

    make_filter = col2.selectbox(
        "Make",
        ["All"] + sorted(df["MAKE"].dropna().unique())
    )

    model_filter = col3.selectbox(
        "Model",
        ["All"] + sorted(df["MODEL"].dropna().unique())
    )

    version_filter = col4.selectbox(
        "Version",
        ["All"] + sorted(df["VERSION"].dropna().unique())
    )

    filtered_df = df.copy()

    if auction_filter != "All":
        filtered_df = filtered_df[filtered_df["Auction"] == auction_filter]

    if make_filter != "All":
        filtered_df = filtered_df[filtered_df["MAKE"] == make_filter]

    if model_filter != "All":
        filtered_df = filtered_df[filtered_df["MODEL"] == model_filter]

    if version_filter != "All":
        filtered_df = filtered_df[filtered_df["VERSION"] == version_filter]

    st.dataframe(filtered_df, use_container_width=True)

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
