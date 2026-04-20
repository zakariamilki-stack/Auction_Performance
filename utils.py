import pandas as pd

FILE_PATH = "https://raw.githubusercontent.com/zakariamilki-stack/Auctiondata/main/2026YTD-PERFORMANCE.xlsx"

def load_data():
    df = pd.read_excel(FILE_PATH)

    # CLEAN COLUMNS
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ", regex=False)
        .str.replace("\t", " ", regex=False)
    )

    # Fix SOLD MONTH
    for col in df.columns:
        if "SOLD" in col and "MONTH" in col:
            df.rename(columns={col: "SOLD MONTH"}, inplace=True)

    # FILTER SOLD ONLY
    df["CURRENT SALE STATUS"] = df["CURRENT SALE STATUS"].astype(str).str.upper().str.strip()
    df = df[df["CURRENT SALE STATUS"] == "SOLD"].copy()

    # NUMERIC
    df["NET PRICE"] = pd.to_numeric(df["NET PRICE"], errors="coerce")
    df["Auction"] = df["SALE TYPE"]
    df["NetPrice"] = df["NET PRICE"]

    # MONTH FIX
    df["SoldMonth_raw"] = df["SOLD MONTH"]
    df["SoldMonth_dt"] = pd.to_datetime(df["SoldMonth_raw"], errors="coerce")
    df["MonthOrder"] = df["SoldMonth_dt"].dt.month

    month_map = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
    }

    mask = df["MonthOrder"].isna()

    df.loc[mask, "MonthOrder"] = (
        df.loc[mask, "SoldMonth_raw"]
        .astype(str)
        .str.upper()
        .str[:3]
        .map(month_map)
    )

    df = df.dropna(subset=["MonthOrder"])

    df["SoldMonth"] = df["MonthOrder"].astype(int).map({
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    })

    return df
