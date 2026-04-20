import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from utils import load_data

st.set_page_config(page_title="AI Price Engine", layout="wide")

st.title("🚗 AI Pricing & Valuation Engine")

df = load_data()

# ================= KM COLUMN DETECTION =================
km_col = None
for col in df.columns:
    if "KM" in col or "MILE" in col or "ODOM" in col:
        km_col = col
        break

if km_col is None:
    st.error("KM column not found")
    st.stop()

df = df.dropna(subset=[km_col, "NetPrice"])

df[km_col] = pd.to_numeric(df[km_col], errors="coerce")
df["NetPrice"] = pd.to_numeric(df["NetPrice"], errors="coerce")
df = df.dropna()

# ================= USER INPUT =================
st.subheader("🎯 Vehicle Selection")

c1, c2, c3 = st.columns(3)

make = c1.selectbox("Make", sorted(df["MAKE"].unique()))
model_year = c2.selectbox("Model Year", sorted(df["MODEL YEAR"].unique()))
km_input = c3.number_input("KM", min_value=0, step=1000)

filtered = df[(df["MAKE"] == make) & (df["MODEL YEAR"] == model_year)]

if len(filtered) < 30:
    st.warning("Not enough data")
    st.stop()

# ================= MODEL =================
X = filtered[[km_col]]
y = filtered["NetPrice"]

model = RandomForestRegressor(n_estimators=120, random_state=42)
model.fit(X, y)

pred = model.predict([[km_input]])[0]

# confidence
all_preds = [tree.predict([[km_input]])[0] for tree in model.estimators_]
low = np.percentile(all_preds, 10)
high = np.percentile(all_preds, 90)

# ================= OUTPUT =================
st.subheader("💰 Prediction")

st.success(f"""
Expected Price: AED {pred:,.0f}
Range: AED {low:,.0f} - AED {high:,.0f}
""")

# ================= SIGNAL =================
market_avg = filtered["NetPrice"].mean()

if pred < market_avg * 0.95:
    st.info("🟢 Undervalued (Good Buy)")
elif pred > market_avg * 1.05:
    st.error("🔴 Overpriced")
else:
    st.warning("🟡 Fair Market")

# ================= TREND =================
st.subheader("📉 KM vs Price")

st.scatter_chart(filtered[[km_col, "NetPrice"]].rename(columns={km_col: "KM"}))
