import streamlit as st
import pandas as pd
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
    # CLEAN COLUMN NAMES (ROBUST FIX)
    # =====================================================
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ", regex=False)
        .str.replace("\t", " ", regex=False)
        .str.replace("  ", " ", regex=False)
    )

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
        "MODEL YEAR"
    ]

    missing_cols = [c for c in required_cols if c not in df.columns]

    if missing_cols:
        st.error(f"Missing columns in file: {missing_cols}")
        st.stop()

    # =====================================================
    # CLEAN DATA
    # =====================================================
    df = df[df["CURRENT SALE STATUS"] == "Sold"].copy()

    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]
    df["SoldMonth"] = df["SOLD MONTH"].astype(str)

    df = df.dropna(subset=["SoldMonth", "NetPrice"])

    # =====================================================
    # KPI SECTION
    # =====================================================
    units_sold = len(df)
    avg_price = df["NetPrice"].mean()
    max_price = df["NetPrice"].max()
    min_price = df["NetPrice"].min()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Units Sold", units_sold)
    col2.metric("Avg Net Price", round(avg_price, 2) if pd.notna(avg_price) else 0)
    col3.metric("Max Net Price", max_price if pd.notna(max_price) else 0)
    col4.metric("Min Net Price", min_price if pd.notna(min_price) else 0)

    # =====================================================
    # MONTHLY TREND
    # =====================================================
    st.subheader("📈 Monthly Performance")

    trend = df.groupby("SoldMonth")["NetPrice"].count().reset_index()
    trend.columns = ["Month", "Units"]

    st.line_chart(trend.set_index("Month"))

    # =====================================================
    # FILTERS
    # =====================================================
    st.subheader("🔎 Data Explorer")

    col1, col2, col3 = st.columns(3)

    auction_filter = col1.selectbox(
        "Auction",
        ["All"] + sorted(df["Auction"].dropna().unique())
    )

    make_filter = col2.selectbox(
        "Make",
        ["All"] + sorted(df["MAKE"].dropna().unique())
    )

    model_filter = col3.selectbox(
        "Model Year",
        ["All"] + sorted(df["MODEL YEAR"].dropna().unique())
    )

    filtered_df = df.copy()

    if auction_filter != "All":
        filtered_df = filtered_df[filtered_df["Auction"] == auction_filter]

    if make_filter != "All":
        filtered_df = filtered_df[filtered_df["MAKE"] == make_filter]

    if model_filter != "All":
        filtered_df = filtered_df[filtered_df["MODEL YEAR"] == model_filter]

    st.dataframe(filtered_df, use_container_width=True)

    # =====================================================
    # DOWNLOAD FUNCTION
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
