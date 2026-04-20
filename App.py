import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

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
except Exception as e:
    st.error(f"Load error: {e}")
    st.stop()

# =====================================================
# CLEAN DATA
# =====================================================
df.columns = df.columns.astype(str).str.upper().str.strip()

for col in df.columns:
    if "SOLD" in col and "MONTH" in col:
        df.rename(columns={col: "SOLD MONTH"}, inplace=True)

df["CURRENT SALE STATUS"] = df["CURRENT SALE STATUS"].astype(str).str.upper()
df = df[df["CURRENT SALE STATUS"] == "SOLD"].copy()

df["NET PRICE"] = pd.to_numeric(df["NET PRICE"], errors="coerce")

df["Auction"] = df["SALE TYPE"]
df["NetPrice"] = df["NET PRICE"]

# =====================================================
# MONTH FIX
# =====================================================
month_map = {
    "JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
    "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12
}

df["SOLD MONTH"] = df["SOLD MONTH"].astype(str).str[:3].str.upper()
df["MonthOrder"] = df["SOLD MONTH"].map(month_map)
df = df.dropna(subset=["MonthOrder"])
df["MonthOrder"] = df["MonthOrder"].astype(int)

df["SoldMonth"] = df["MonthOrder"].map({
    1:"Jan",2:"Feb",3:"Mar",4:"Apr",
    5:"May",6:"Jun",7:"Jul",8:"Aug",
    9:"Sep",10:"Oct",11:"Nov",12:"Dec"
})

# =====================================================
# KM COLUMN DETECTION
# =====================================================
km_col = None
for c in df.columns:
    if "KM" in c or "ODOM" in c or "MILE" in c:
        km_col = c
        break

# =====================================================
# NAVIGATION
# =====================================================
page = st.sidebar.radio("Navigation", [
    "📊 Overview",
    "🤖 AI Price Engine",
    "📦 Dealer Performance",
    "📉 Insights Hub"
])

# =====================================================
# PAGE 1 - DASHBOARD + SEARCH
# =====================================================
if page == "📊 Overview":

    st.subheader("🔎 Global Search")

    df_f = df.copy()

    search = st.text_input("Search (Make / Model / Version / Buyer / List Type)")

    if search:
        search = search.upper()

        df_f = df_f[
            df_f["MAKE"].astype(str).str.upper().str.contains(search, na=False) |
            df_f["MODEL"].astype(str).str.upper().str.contains(search, na=False) |
            df_f["VERSION"].astype(str).str.upper().str.contains(search, na=False) |
            df_f["BUYER/DEBTOR NAME"].astype(str).str.upper().str.contains(search, na=False) |
            df_f["LIST TYPE"].astype(str).str.upper().str.contains(search, na=False)
        ]

    st.subheader("Filters")

    c1,c2,c3,c4,c5,c6 = st.columns(6)

    auction = c1.selectbox("Auction", ["All"] + sorted(df_f["Auction"].dropna().unique()))
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

    def fmt(x):
        return "-" if pd.isna(x) else f"AED {x:,.0f}"

    st.subheader("📌 KPIs")

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Units", len(df_f))
    c2.metric("Avg Price", fmt(df_f["NetPrice"].mean()))
    c3.metric("Max Price", fmt(df_f["NetPrice"].max()))
    c4.metric("Min Price", fmt(df_f["NetPrice"].min()))

    st.subheader("📈 Monthly Trend")

    if len(df_f) > 0:

        trend = df_f.groupby(["MonthOrder","SoldMonth"]).agg(
            Qty=("NetPrice","count"),
            AvgNet=("NetPrice","mean")
        ).reset_index().sort_values("MonthOrder")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=trend["SoldMonth"],
            y=trend["AvgNet"],
            mode="lines+markers+text",
            name="Avg Price",
            text=[f"{x:,.0f}" for x in trend["AvgNet"]],
            textposition="top center"
        ))

        fig.add_trace(go.Scatter(
            x=trend["SoldMonth"],
            y=trend["Qty"],
            mode="lines+markers+text",
            name="Qty",
            text=trend["Qty"],
            textposition="bottom center"
        ))

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No data found")

    st.dataframe(df_f, use_container_width=True)

# =====================================================
# PAGE 2 - AI ENGINE
# =====================================================
elif page == "🤖 AI Price Engine":

    st.subheader("AI Pricing Engine (Stable Market Model)")

    if km_col is None:
        st.error("KM column missing")
        st.stop()

    # =====================================================
    # CLEAN DATA FIRST
    # =====================================================
    df_ml = df.copy()

    df_ml["NetPrice"] = pd.to_numeric(df_ml["NetPrice"], errors="coerce")
    df_ml[km_col] = pd.to_numeric(df_ml[km_col], errors="coerce")
    df_ml["MODEL YEAR"] = pd.to_numeric(df_ml["MODEL YEAR"], errors="coerce")

    df_ml = df_ml.dropna(subset=[
        "NetPrice",
        km_col,
        "MAKE",
        "MODEL",
        "MODEL YEAR"
    ])

    # REMOVE INVALID YEARS
    df_ml = df_ml[(df_ml["MODEL YEAR"] > 1990) & (df_ml["MODEL YEAR"] <= 2026)]

    # =====================================================
    # FEATURE ENGINEERING (SAFE)
    # =====================================================
    CURRENT_YEAR = 2026

    df_ml["AGE"] = CURRENT_YEAR - df_ml["MODEL YEAR"]

    # FIX: avoid zero or negative age
    df_ml["AGE"] = df_ml["AGE"].clip(lower=1)

    df_ml["KM_PER_YEAR"] = df_ml[km_col] / df_ml["AGE"]

    # REMOVE INF / BAD VALUES
    df_ml = df_ml.replace([np.inf, -np.inf], np.nan)
    df_ml = df_ml.dropna(subset=["AGE", "KM_PER_YEAR"])

    # log price for stability
    df_ml["LOG_PRICE"] = np.log1p(df_ml["NetPrice"])

    # =====================================================
    # ENCODING
    # =====================================================
    make_map = {v:i for i,v in enumerate(df_ml["MAKE"].astype(str).unique())}
    model_map = {v:i for i,v in enumerate(df_ml["MODEL"].astype(str).unique())}

    df_ml["MAKE_ENC"] = df_ml["MAKE"].astype(str).map(make_map)
    df_ml["MODEL_ENC"] = df_ml["MODEL"].astype(str).map(model_map)

    # FINAL CLEAN CHECK
    df_ml = df_ml.dropna()

    if len(df_ml) < 50:
        st.error("Not enough valid structured data after cleaning")
        st.stop()

    # =====================================================
    # INPUT UI
    # =====================================================
    c1, c2, c3, c4 = st.columns(4)

    make_ai = c1.selectbox("Make", sorted(make_map.keys()))
    model_ai = c2.selectbox("Model", sorted(df_ml[df_ml["MAKE"]==make_ai]["MODEL"].unique()))
    year_ai = c3.number_input("Model Year", min_value=1990, max_value=2026, value=2020)
    km_input = c4.number_input("KM", 0, step=1000)

    age = max(1, CURRENT_YEAR - year_ai)
    km_per_year = km_input / age

    # =====================================================
    # MODEL
    # =====================================================
    from sklearn.ensemble import RandomForestRegressor

    X = df_ml[["MAKE_ENC", "MODEL_ENC", "AGE", "KM_PER_YEAR"]]
    y = df_ml["LOG_PRICE"]

    # FINAL ALIGNMENT SAFETY
    valid = X.notna().all(axis=1) & y.notna()
    X = X[valid]
    y = y[valid]

    rf = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        max_depth=12
    )

    rf.fit(X, y)

    # =====================================================
    # PREDICTION
    # =====================================================
    make_enc = make_map.get(make_ai, 0)
    model_enc = model_map.get(model_ai, 0)

    pred_log = rf.predict([[make_enc, model_enc, age, km_per_year]])[0]
    pred = np.expm1(pred_log)

    # =====================================================
    # OUTPUT
    # =====================================================
    st.success(f"""
🚗 Make: {make_ai}  
🚙 Model: {model_ai}  
📅 Year: {year_ai}  
📍 KM: {km_input:,.0f}  
📊 Age: {age} years  

💰 Predicted Price: AED {pred:,.0f}
""")
# =====================================================
# PAGE 3 - DEALERS
# =====================================================
elif page == "📦 Dealer Performance":

    st.subheader("Dealer Intelligence")

    c1,c2 = st.columns(2)

    auction_f = c1.selectbox("Auction", ["All"] + sorted(df["Auction"].unique()))
    buyer_f = c2.selectbox("Buyer Type", ["All"] + sorted(df["BUYER TYPE"].dropna().unique()))

    df_d = df.copy()

    if auction_f != "All":
        df_d = df_d[df_d["Auction"]==auction_f]

    if buyer_f != "All":
        df_d = df_d[df_d["BUYER TYPE"]==buyer_f]

    top = df_d.groupby("BUYER/DEBTOR NAME").agg(
        Units=("NetPrice","count"),
        Value=("NetPrice","sum")
    ).sort_values("Value",ascending=False).head(15)

    st.subheader("Top Bidders")
    st.dataframe(top)

    seg = df_d.groupby("BUYER TYPE").agg(
        Units=("NetPrice","count"),
        Value=("NetPrice","sum")
    )

    st.subheader("Buyer Segmentation")
    st.dataframe(seg)

# =====================================================
# PAGE 4 - INSIGHTS
# =====================================================
elif page == "📉 Insights Hub":

    st.subheader("Market Insights")

    c1,c2 = st.columns(2)

    make_f = c1.selectbox("Make Filter", ["All"] + sorted(df["MAKE"].dropna().unique()))
    year_f = c2.selectbox("Year Filter", ["All"] + sorted(df["MODEL YEAR"].dropna().unique()))

    df_i = df.copy()

    if make_f != "All":
        df_i = df_i[df_i["MAKE"]==make_f]

    if year_f != "All":
        df_i = df_i[df_i["MODEL YEAR"]==year_f]

    df_i["AGE"] = 2026 - df_i["MODEL YEAR"]

    trend = df_i.groupby("AGE")["NetPrice"].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend["AGE"], y=trend["NetPrice"], mode="lines+markers"))

    st.plotly_chart(fig)

    st.dataframe(df_i.head(50))
