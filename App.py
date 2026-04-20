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

    st.subheader("AI Pricing Engine (NORMAL Market)")

    if km_col is None:
        st.error("KM column missing")
        st.stop()

    df_ml = df[df["Auction"].astype(str).str.upper() == "NORMAL"].copy()
    df_ml = df_ml.dropna(subset=["NetPrice","MAKE","MODEL","MODEL YEAR",km_col])

    if len(df_ml) < 80:
        st.warning("Not enough NORMAL market data")
        st.stop()

    # =====================================================
    # SAFE ENCODING MAP (NO LabelEncoder CRASH)
    # =====================================================
    make_map = {v:i for i,v in enumerate(df_ml["MAKE"].astype(str).unique())}
    model_map = {v:i for i,v in enumerate(df_ml["MODEL"].astype(str).unique())}
    year_map = {v:i for i,v in enumerate(df_ml["MODEL YEAR"].astype(str).unique())}

    df_ml["MAKE_ENC"] = df_ml["MAKE"].astype(str).map(make_map)
    df_ml["MODEL_ENC"] = df_ml["MODEL"].astype(str).map(model_map)
    df_ml["YEAR_ENC"] = df_ml["MODEL YEAR"].astype(str).map(year_map)

    df_ml = df_ml.dropna()

    c1,c2,c3,c4 = st.columns(4)

    make_ai = c1.selectbox("Make", sorted(make_map.keys()))
    model_ai = c2.selectbox("Model", sorted(df_ml[df_ml["MAKE"]==make_ai]["MODEL"].unique()))
    year_ai = c3.selectbox("Year", sorted(df_ml[df_ml["MODEL"]==model_ai]["MODEL YEAR"].unique()))
    km_input = c4.number_input("KM",0,step=1000)

    # =====================================================
    # TRAIN MODEL
    # =====================================================
    from sklearn.ensemble import RandomForestRegressor

    rf = RandomForestRegressor(n_estimators=150, random_state=42)

    X = df_ml[["MAKE_ENC","MODEL_ENC","YEAR_ENC",km_col]]
    y = df_ml["NetPrice"]

    rf.fit(X,y)

    # =====================================================
    # SAFE INPUT HANDLING (NO CRASH EVER)
    # =====================================================
    make_enc = make_map.get(make_ai, 0)
    model_enc = model_map.get(model_ai, 0)
    year_enc = year_map.get(year_ai, 0)

    pred = rf.predict([[make_enc, model_enc, year_enc, km_input]])[0]

    st.success(f"""
🚗 Make: {make_ai}  
🚙 Model: {model_ai}  
📅 Year: {year_ai}  
📍 KM: {km_input:,.0f}  

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
