import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="Saxtons Lender Commission Tool", page_icon="💰", layout="wide")

# --- LOGIN ---
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        with st.form("login_form", clear_on_submit=False):
            st.title("🔐 Saxtons Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Log In")

            if submit:
                if username == "Saxtons1" and password == "Saxtons1":
                    st.session_state.logged_in = True
                    st.experimental_rerun()
                else:
                    st.error("Incorrect username or password")
        st.stop()

login()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp {background-color: #f5f7fa; font-family: 'Segoe UI', sans-serif;}
    h1 {color: #003366; text-align: center; margin-bottom: 10px;}
    .input-card {background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px;}
    .stat-card {padding: 20px; border-radius: 12px; color: #003366;
        box-shadow: 0 4px 12px rgba(0,0,0,0.07); font-size: 20px; font-weight: bold; margin-bottom: 15px;}
    .best {background-color: #e8f9f0;} .apr {background-color: #e8f1fb;} .count {background-color: #f5e8fb;}
    .label {font-size:16px; font-weight: normal; color: #555;}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- LENDER DATA ---
data = [
    ["Santander", "0-24999", "HP,LP,PCP", 12.9, 9.05, None, True],
    ["Santander", "25000-39999", "HP,LP,PCP", 11.9, 6.8, None, True],
    ["Santander", "40000-49999", "HP,LP,PCP", 10.9, 5.15, None, True],
    ["Santander", "50000+", "HP,LP,PCP", 9.9, 4, None, True],
    ["ZOPA", "0-24999", "HP,PCP", 12.9, "HP:9.15 PCP:11.15", 3000, True],
    ["ZOPA", "25000-32999", "HP,PCP", 11.9, "HP:7.15 PCP:9.15", 3000, True],
    ["ZOPA", "33000-50000", "HP,PCP", 10.9, "HP:5.15 PCP:7.15", 3000, True],
    ["Mann Island", "2500-40000+", "HP,PCP,LP", 10.9, 6.75, 3000, True],
    ["Moto Novo", "All", "HP,PCP", 11.9, 2, None, True],
    ["Blue", "12900-19900", "HP", "12.9-19.9", 8, 2000, False],
    ["Startline Low", "16900", "HP,PCP", 16.9, 5, 2000, False],
    ["Startline High", "19900", "HP,PCP", 19.9, 5, 1500, False],
    ["Marsh Low", "0-30000", "HP,PCP", "14.4-23.9", 0, 1500, True],
    ["Marsh High", "0-30000", "HP,PCP", 26.9, 0, 1500, True],
    ["JBR", "0-500000", "HP,LP", 10.9, 5.5, None, True],
    ["Tandem", "0-60000", "HP", "10.9-19.9", 7, 2000, False],
    ["Admiral", "0-60000", "HP,PCP", "9.9-25.0", 7.5, 2500, True],
    ["Alphera", "All", "HP,PCP", 10.9, 4.5, 3000, False],
    ["BNP", "All", "HP,PCP", 9.9, 4.5, 3000, False],
    ["CAAF", "All", "HP,PCP", 10.9, 4.5, 3000, False],
    ["Close", "All", "HP,PCP", 10.9, 3.5, 3000, False],
    ["Moto Novo (Motion)", "All", "HP,PCP", 11.9, 4.5, 3000, False],
    ["Oodle & Blue", "All", "HP", "Rate for risk", 3, 3000, False],
    ["ABOUND (Personal Loan)", "All", "Loan", "N/A", 0, None, False],
    ["Go Car Credit", "All", "HP", "Rate for risk", 0.5, None, False]
]
columns = ["Lender", "Advance Band", "Products", "APR", "Commission %", "Commission Cap", "Favourite"]
df = pd.DataFrame(data, columns=columns)

# --- INPUT PANEL ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    advance = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    product = st.selectbox("Product", ["HP", "PCP", "LP", "Loan"])
with col3:
    term = st.selectbox("Term (months)", [24, 36, 48, 60])
with col4:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])
st.markdown("</div>", unsafe_allow_html=True)

# --- LOGIC ---
def match_band(band, val):
    if "All" in band: return True
    if "+" in band: return val >= int(band.split("+")[0])
    if "-" in band:
        low, high = map(int, band.split("-"))
        return low <= val <= high
    return int(band) == val

matches = df[df["Products"].str.contains(product)]
matches = matches[matches["Advance Band"].apply(lambda x: match_band(x.replace(",", ""), advance))]
matches = matches[matches["Favourite"] == True]

results = []
for _, row in matches.iterrows():
    rate = row["Commission %"]
    cap = float(row["Commission Cap"]) if pd.notnull(row["Commission Cap"]) else None
    apr = row["APR"]

    if isinstance(rate, str) and f"{product}:" in rate:
        pct = float(rate.split(f"{product}:")[1].split()[0])
    else:
        try: pct = float(rate)
        except: pct = 0

    comm = (pct / 100) * advance
    interest = (pct / 100) * advance * (term / 12)
    if row["Lender"] == "Admiral":
        if term < 36: continue
        comm = min(comm, interest * 0.5)
    if cap: comm = min(comm, cap)
    results.append([row["Lender"], row["Advance Band"], pct, comm, apr])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR"])
if calc_df.empty:
    st.warning("No lenders found for this combination.")
else:
    best = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if x != "Rate for risk" else 99).idxmin()]
    count = calc_df["Lender"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='stat-card best'>Top Commission<br><span style='font-size:28px;'>£{best['Commission (£)']:.0f}</span><br><span class='label'>{best['Lender']} ({product})</span></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='stat-card apr'>Lowest APR<br><span style='font-size:28px;'>{lowest['APR']}</span><br><span class='label'>{lowest['Lender']}</span></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='stat-card count'>Matching Lenders<br><span style='font-size:28px;'>{count}</span><br><span class='label'>For £{advance:,.0f}</span></div>", unsafe_allow_html=True)

    st.subheader("Detailed Results")
    df_to_show = calc_df.sort_values("Commission (£)", ascending=(sort_by != "Highest Commission"))
    st.dataframe(df_to_show, use_container_width=True)

    st.download_button("Download CSV", df_to_show.to_csv(index=False).encode(), "commission_results.csv")
