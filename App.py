import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
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
# SAFE MONTH PARSING
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
# SIDEBAR NAVIGATION
# =====================================================
page = st.sidebar.radio("Navigation", [
    "📊 Overview",
    "🤖 AI Price Engine",
    "📦 Dealer Performance",
    "📉 Insights Hub"
])

# =====================================================
# KM DETECTION
# =====================================================
km_col = None
for col in df.columns:
    if "KM" in col or "MILE" in col or "ODOM" in col:
        km_col = col
        break

# =====================================================
# ================= PAGE 1 (UNCHANGED) =================
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

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_f, use_container_width=True)

# =====================================================
# ================= PAGE 2 AI ENGINE (FIXED) =================
# =====================================================
elif page == "🤖 AI Price Engine":

    st.subheader("🚗 AI Price Prediction Engine (Advanced)")

    if km_col is None:
        st.error("KM column not found")
        st.stop()

    df_ml = df.dropna(subset=["NetPrice", km_col, "MAKE", "MODEL", "MODEL YEAR"]).copy()

    # ================= ENCODING =================
    le_make = LabelEncoder()
    le_model = LabelEncoder()
    le_year = LabelEncoder()

    df_ml["MAKE_ENC"] = le_make.fit_transform(df_ml["MAKE"].astype(str))
    df_ml["MODEL_ENC"] = le_model.fit_transform(df_ml["MODEL"].astype(str))
    df_ml["YEAR_ENC"] = le_year.fit_transform(df_ml["MODEL YEAR"].astype(str))

    # ================= INPUT =================
    c1, c2, c3, c4 = st.columns(4)

    make_ai = c1.selectbox("Make", sorted(df_ml["MAKE"].unique()))
    model_ai = c2.selectbox("Model", sorted(df_ml[df_ml["MAKE"] == make_ai]["MODEL"].unique()))
    year_ai = c3.selectbox("Model Year", sorted(df_ml["MODEL YEAR"].unique()))
    km_input = c4.number_input("KM", min_value=0, step=1000)

    # ================= FILTER =================
    filtered = df_ml[
        (df_ml["MAKE"] == make_ai) &
        (df_ml["MODEL"] == model_ai) &
        (df_ml["MODEL YEAR"] == year_ai)
    ]

    if len(filtered) < 20:
        st.warning("Not enough data for this combination")
        st.stop()

    # ================= MODEL =================
    X = filtered[["MAKE_ENC", "MODEL_ENC", "YEAR_ENC", km_col]]
    y = filtered["NetPrice"]

    rf = RandomForestRegressor(n_estimators=150, random_state=42)
    rf.fit(X, y)

    make_enc = le_make.transform([make_ai])[0]
    model_enc = le_model.transform([model_ai])[0]
    year_enc = le_year.transform([year_ai])[0]

    pred = rf.predict([[make_enc, model_enc, year_enc, km_input]])[0]

    st.success(f"""
🚗 Make: {make_ai}  
🚙 Model: {model_ai}  
📅 Year: {year_ai}  
📍 KM: {km_input:,.0f}  

💰 Predicted Price: AED {pred:,.0f}
""")

# =====================================================
# ================= PAGE 3 =================
# =====================================================
elif page == "📦 Dealer Performance":

    st.subheader("Dealer Performance")

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
# ================= PAGE 4 =================
# =====================================================
elif page == "📉 Insights Hub":

    st.subheader("Market Insights")

    df["AGE"] = 2026 - df["MODEL YEAR"]

    residual = df.groupby("AGE")["NetPrice"].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=residual["AGE"],
        y=residual["NetPrice"],
        mode="lines+markers"
    ))

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sell vs Hold")

    sample = df.copy()
    sample["AVG_MARKET"] = sample.groupby("MODEL")["NetPrice"].transform("mean")
    sample["DECISION"] = np.where(sample["NetPrice"] < sample["AVG_MARKET"], "HOLD", "SELL")

    st.dataframe(sample[["MAKE", "MODEL", "NetPrice", "AVG_MARKET", "DECISION"]])
