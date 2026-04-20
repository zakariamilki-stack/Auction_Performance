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
# CLEAN
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
# MONTH FIX (SAFE)
# =====================================================
month_map = {
    "JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
    "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12
}

df["SOLD MONTH"] = df["SOLD MONTH"].astype(str).str[:3].str.upper()
df["MonthOrder"] = df["SOLD MONTH"].map(month_map)
df = df.dropna(subset=["MonthOrder"])
df["MonthOrder"] = df["MonthOrder"].astype(int)

# =====================================================
# KM DETECTION
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
# PAGE 1 (UNCHANGED CORE)
# =====================================================
if page == "📊 Overview":

    st.subheader("Filters")

    c1,c2,c3,c4,c5,c6 = st.columns(6)

    df_f = df.copy()

    auction = c1.selectbox("Auction", ["All"] + sorted(df["Auction"].dropna().unique()))
    if auction != "All":
        df_f = df_f[df_f["Auction"] == auction]

    make = c2.selectbox("Make", ["All"] + sorted(df_f["MAKE"].dropna().unique()))
    if make != "All":
        df_f = df_f[df_f["MAKE"] == make]

    model = c3.selectbox("Model", ["All"] + sorted(df_f["MODEL"].dropna().unique()))
    if model != "All":
        df_f = df_f[df_f["MODEL"] == model]

    year = c4.selectbox("Year", ["All"] + sorted(df_f["MODEL YEAR"].dropna().unique()))
    if year != "All":
        df_f = df_f[df_f["MODEL YEAR"] == year]

    list_type = c5.selectbox("List Type", ["All"] + sorted(df_f["LIST TYPE"].dropna().unique()))
    if list_type != "All":
        df_f = df_f[df_f["LIST TYPE"] == list_type]

    buyer_type = c6.selectbox("Buyer Type", ["All"] + sorted(df_f["BUYER TYPE"].dropna().unique()))
    if buyer_type != "All":
        df_f = df_f[df_f["BUYER TYPE"] == buyer_type]

    st.metric("Units", len(df_f))
    st.metric("Avg Price", f"AED {df_f['NetPrice'].mean():,.0f}")

# =====================================================
# PAGE 2 AI (FIXED SAFE TRAINING)
# =====================================================
elif page == "🤖 AI Price Engine":

    st.subheader("AI Market Pricing Engine (NORMAL reference)")

    if km_col is None:
        st.error("KM column missing")
        st.stop()

    df_ml = df[df["Auction"].astype(str).str.upper() == "NORMAL"].copy()

    df_ml = df_ml.dropna(subset=["NetPrice", "MAKE", "MODEL", "MODEL YEAR", km_col])

    # MUST HAVE ENOUGH DATA
    if len(df_ml) < 80:
        st.warning("Not enough NORMAL market data")
        st.stop()

    # ENCODING SAFE
    le_make = LabelEncoder()
    le_model = LabelEncoder()
    le_year = LabelEncoder()

    df_ml["MAKE_ENC"] = le_make.fit_transform(df_ml["MAKE"].astype(str))
    df_ml["MODEL_ENC"] = le_model.fit_transform(df_ml["MODEL"].astype(str))
    df_ml["YEAR_ENC"] = le_year.fit_transform(df_ml["MODEL YEAR"].astype(str))

    c1,c2,c3,c4 = st.columns(4)

    make_ai = c1.selectbox("Make", sorted(df_ml["MAKE"].unique()))
    model_ai = c2.selectbox("Model", sorted(df_ml[df_ml["MAKE"] == make_ai]["MODEL"].unique()))
    year_ai = c3.selectbox("Year", sorted(df_ml["MODEL YEAR"].unique()))
    km_input = c4.number_input("KM", min_value=0, step=1000)

    filtered = df_ml[
        (df_ml["MAKE"] == make_ai) &
        (df_ml["MODEL"] == model_ai) &
        (df_ml["MODEL YEAR"] == year_ai)
    ]

    # FIX CRASH
    if filtered.shape[0] < 20:
        st.warning("Not enough sample data for this combination")
        st.stop()

    X = filtered[["MAKE_ENC","MODEL_ENC","YEAR_ENC",km_col]]
    y = filtered["NetPrice"]

    # EXTRA SAFETY CHECK
    if X.shape[0] != y.shape[0]:
        st.error("Data mismatch")
        st.stop()

    model_rf = RandomForestRegressor(n_estimators=120, random_state=42)
    model_rf.fit(X, y)

    pred = model_rf.predict([[
        le_make.transform([make_ai])[0],
        le_model.transform([model_ai])[0],
        le_year.transform([year_ai])[0],
        km_input
    ]])[0]

    st.success(f"Predicted Price: AED {pred:,.0f}")

# =====================================================
# PAGE 3 DEALERS (WITH FILTERS)
# =====================================================
elif page == "📦 Dealer Performance":

    st.subheader("Dealer Intelligence")

    c1,c2 = st.columns(2)

    auction_filter = c1.selectbox("Auction Filter", ["All"] + sorted(df["Auction"].unique()))
    buyer_filter = c2.selectbox("Buyer Type", ["All"] + sorted(df["BUYER TYPE"].dropna().unique()))

    df_d = df.copy()

    if auction_filter != "All":
        df_d = df_d[df_d["Auction"] == auction_filter]

    if buyer_filter != "All":
        df_d = df_d[df_d["BUYER TYPE"] == buyer_filter]

    top_bidders = df_d.groupby("BUYER/DEBTOR NAME").agg(
        Units=("NetPrice","count"),
        Value=("NetPrice","sum")
    ).sort_values("Value", ascending=False).head(15)

    st.subheader("Top Bidders")
    st.dataframe(top_bidders)

    seg = df_d.groupby("BUYER TYPE").agg(
        Units=("NetPrice","count"),
        Value=("NetPrice","sum")
    )

    st.subheader("Buyer Segmentation")
    st.dataframe(seg)

# =====================================================
# PAGE 4 INSIGHTS (WITH FILTERS)
# =====================================================
elif page == "📉 Insights Hub":

    st.subheader("Market Insights")

    c1,c2 = st.columns(2)

    make_f = c1.selectbox("Make Filter", ["All"] + sorted(df["MAKE"].dropna().unique()))
    year_f = c2.selectbox("Year Filter", ["All"] + sorted(df["MODEL YEAR"].dropna().unique()))

    df_i = df.copy()

    if make_f != "All":
        df_i = df_i[df_i["MAKE"] == make_f]

    if year_f != "All":
        df_i = df_i[df_i["MODEL YEAR"] == year_f]

    df_i["AGE"] = 2026 - df_i["MODEL YEAR"]

    trend = df_i.groupby("AGE")["NetPrice"].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend["AGE"], y=trend["NetPrice"], mode="lines+markers"))

    st.plotly_chart(fig)

    st.dataframe(df_i.head(50))
