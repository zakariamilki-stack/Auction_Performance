import streamlit as st
import plotly.graph_objects as go
from utils import load_data

st.set_page_config(page_title="Auction Overview", layout="wide")

st.title("📊 Auction Overview")

df = load_data()

# ================= FILTERS =================
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

# ================= KPI =================
def fmt(v):
    return "-" if v is None else f"AED {v:,.0f}"

st.subheader("📌 KPIs")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Units Sold", len(df_f))
col2.metric("Avg Price", fmt(df_f["NetPrice"].mean()))
col3.metric("Max Price", fmt(df_f["NetPrice"].max()))
col4.metric("Min Price", fmt(df_f["NetPrice"].min()))

# ================= TREND =================
st.subheader("📈 Monthly Trend")

trend = df_f.groupby(["MonthOrder", "SoldMonth"]).agg(
    Qty=("NetPrice", "count"),
    Avg=("NetPrice", "mean")
).reset_index().sort_values("MonthOrder")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=trend["SoldMonth"],
    y=trend["Avg"],
    mode="lines+markers",
    name="Avg Price"
))

fig.add_trace(go.Scatter(
    x=trend["SoldMonth"],
    y=trend["Qty"],
    mode="lines+markers",
    name="Qty"
))

st.plotly_chart(fig, use_container_width=True)

# ================= TABLE =================
st.dataframe(df_f, use_container_width=True)
