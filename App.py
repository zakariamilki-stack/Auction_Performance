import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Auction Dashboard", layout="wide")

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

    # FIX SOLD MONTH COLUMN
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
    df["CURRENT SALE STATUS"] = df["CURRENT SALE STATUS"].astype(str).str.strip().str.upper()
    df = df[df["CURRENT SALE STATUS"] == "SOLD"].copy()

    # =====================================================
    # NUMERIC CLEAN
    # =====================================================
    df["NET PRICE"] = pd.to_numeric(df["NET PRICE"], errors="coerce")

    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]

    # =====================================================
    # MONTH FIX (ROBUST)
    # =====================================================

    # Try convert to datetime first (handles Excel dates)
    df["SoldMonth_raw"] = df["SOLD MONTH"]

    df["SoldMonth_dt"] = pd.to_datetime(df["SoldMonth_raw"], errors="coerce")

    # Extract month number from datetime
    df["MonthOrder"] = df["SoldMonth_dt"].dt.month

    # If still NaN, try text mapping fallback
    month_map = {
        "JAN": 1, "JANUARY": 1,
        "FEB": 2, "FEBRUARY": 2,
        "MAR": 3, "MARCH": 3,
        "APR": 4, "APRIL": 4,
        "MAY": 5,
        "JUN": 6, "JUNE": 6,
        "JUL": 7, "JULY": 7,
        "AUG": 8, "AUGUST": 8,
        "SEP": 9, "SEPT": 9, "SEPTEMBER": 9,
        "OCT": 10, "OCTOBER": 10,
        "NOV": 11, "NOVEMBER": 11,
        "DEC": 12, "DECEMBER": 12
    }

    missing_mask = df["MonthOrder"].isna()

    df.loc[missing_mask, "MonthOrder"] = (
        df.loc[missing_mask, "SoldMonth_raw"]
        .astype(str)
        .str.upper()
        .str.strip()
        .str[:3]
        .map(month_map)
    )

    # Drop invalid months safely
    df = df.dropna(subset=["MonthOrder"])

    # Create readable month name
    df["SoldMonth"] = df["MonthOrder"].astype(int).map({
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    })

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
    # TREND (SORTED + SAFE)
    # =====================================================
    st.subheader("📈 Monthly Trend")

    trend = df_f.groupby(["MonthOrder", "SoldMonth"]).agg(
        Qty=("NetPrice", "count"),
        AvgNet=("NetPrice", "mean")
    ).reset_index()

    trend = trend.sort_values("MonthOrder")

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
