import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from io import BytesIO

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Auction Intelligence Dashboard made by ZM", layout="wide")

st.title("📊 Auction Intelligence Dashboard")

# =====================================================
# LOAD DATA
# =====================================================
file_path = "https://raw.githubusercontent.com/zakariamilki-stack/Auctiondata/refs/heads/main/2026YTD-PERFORMANCE.xlsx"

try:
    df = pd.read_excel(file_path)
    st.success("✅ Data loaded from GitHub")
except Exception as e:
    st.error(f"❌ Failed to load file: {e}")
    st.stop()

# =====================================================
# CLEAN COLUMNS
# =====================================================
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
    "MODEL YEAR",
    "LIST TYPE"
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

# =====================================================
# SAFE MONTH PARSING (FIXED)
# =====================================================
df["SOLD MONTH"] = df["SOLD MONTH"].astype(str).str.upper().str.strip()

month_map = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

df["MonthOrder"] = df["SOLD MONTH"].str[:3].map(month_map)
df = df.dropna(subset=["MonthOrder"])
df["MonthOrder"] = df["MonthOrder"].astype(int)

df["SoldMonth"] = df["MonthOrder"].map({
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
})

# =====================================================
# FILTERS
# =====================================================
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

# =====================================================
# KPI FORMAT
# =====================================================
def format_aed(value):
    if pd.isna(value):
        return "-"
    return f"AED {value:,.0f}"

# =====================================================
# KPIs
# =====================================================
st.subheader("📌 KPIs")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Units Sold", f"{len(df_f):,}")
col2.metric("Avg Net Price", format_aed(df_f["NetPrice"].mean()))
col3.metric("Max Net Price", format_aed(df_f["NetPrice"].max()))
col4.metric("Min Net Price", format_aed(df_f["NetPrice"].min()))

# =====================================================
# TREND
# =====================================================
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

# =====================================================
# SMART INSIGHTS
# =====================================================
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
        dataframe.to_excel(writer, index=False)
    return output.getvalue()

st.download_button(
    "⬇️ Download Clean Data",
    data=to_excel(df_f),
    file_name="auction_dashboard.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =====================================================
# AI PRICE ENGINE (UPDATED - MODEL INCLUDED)
# =====================================================
st.subheader("🤖 AI Price Engine")

km_col = None
for col in df.columns:
    if "KM" in col or "MILE" in col or "ODOM" in col:
        km_col = col
        break

if km_col:

    df_ml = df.dropna(subset=[km_col, "NetPrice"]).copy()

    c1, c2, c3 = st.columns(3)

    make_ai = c1.selectbox("Make (AI)", sorted(df_ml["MAKE"].unique()))
    model_ai = c2.selectbox("Model (AI)", sorted(df_ml[df_ml["MAKE"] == make_ai]["MODEL"].unique()))
    km_input = c3.number_input("KM", min_value=0, step=1000)

    filtered = df_ml[(df_ml["MAKE"] == make_ai) & (df_ml["MODEL"] == model_ai)]

    if len(filtered) >= 20:

        X = filtered[[km_col]]
        y = filtered["NetPrice"]

        rf_model = RandomForestRegressor(n_estimators=120, random_state=42)
        rf_model.fit(X, y)

        pred = rf_model.predict(np.array([[km_input]]))[0]

        st.success(f"""
🚗 Make: {make_ai}  
🚙 Model: {model_ai}  
💰 Predicted Price: AED {pred:,.0f}
""")

    else:
        st.warning("Not enough data for this Make + Model")
