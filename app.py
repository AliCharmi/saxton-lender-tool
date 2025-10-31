import pandas as pd
import streamlit as st
import plotly.express as px
import re

# --- CONFIG ---
st.set_page_config(page_title="Saxtons Lender Commission Tool", page_icon="💰", layout="wide")

# --- SESSION LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    with st.form("Login"):
        st.subheader("Login Required")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username == "Saxtons1" and password == "Saxtons1":
                st.session_state.logged_in = True
                st.success("Login successful")
                st.experimental_rerun()
            else:
                st.error("Incorrect username or password")

if not st.session_state.logged_in:
    login()
    st.stop()

# --- STYLING ---
st.markdown("""
    <style>
    .stApp {background-color: #f4f6f9; font-family: 'Arial';}
    h1 {color: #003366; text-align: center; margin-bottom: 10px;}
    .input-card {background: #fff; padding: 20px; border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;}
    .stat-card {padding: 20px; border-radius: 10px; color: #003366;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); font-size: 20px; font-weight: bold; margin-bottom: 15px;}
    .best {background: #d1e7dd;} .apr {background: #cfe2ff;} .count {background: #f8d7da;}
    .label {font-size:14px; font-weight: normal; color: #555;}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- LOAD DATA ---
EXCEL_URL = "https://github.com/AliCharmi/saxton-lender-tool/raw/main/data/commission_data_clean.xlsx"
df = pd.read_excel(EXCEL_URL)
df["Notes"] = df["Notes"].fillna("")

# --- INPUTS ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    deal_amount = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    product_choice = st.selectbox("Product", ["PCP", "HP", "LP"])
with col3:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])
with col4:
    term_months = st.selectbox("Term (months)", [24, 36, 48, 60])
st.markdown("</div>", unsafe_allow_html=True)

# --- FILTERING ---
def band_includes(band, amount):
    band = band.replace(",", "").strip()
    if "All" in band: return True
    if "+" in band: return amount >= int(re.findall(r"\d+", band)[0])
    if "-" in band:
        parts = list(map(int, re.findall(r"\d+", band)))
        if len(parts) == 2: return parts[0] <= amount <= parts[1]
    return amount == int(re.findall(r"\d+", band)[0]) if band.isdigit() else False

applicable = df[df["Products"].str.contains(product_choice)]
applicable = applicable[applicable["Advance Band"].apply(lambda x: band_includes(x, deal_amount))]

results = []
for _, row in applicable.iterrows():
    rate_raw = row["Commission %"]
    cap = float(row["Commission Cap"]) if pd.notnull(row["Commission Cap"]) else None
    apr = row["APR"]
    notes = row["Notes"]

    if isinstance(rate_raw, str) and f"{product_choice}:" in rate_raw:
        rate = float(rate_raw.split(f"{product_choice}:")[1].split()[0])
    else:
        try: rate = float(rate_raw)
        except: rate = 0

    interest_est = (rate / 100) * deal_amount * (term_months / 12)
    comm = (rate / 100) * deal_amount

    if row["Lender"] == "Admiral":
        if term_months < 36: continue
        comm = min(comm, interest_est * 0.5)
    if cap: comm = min(comm, cap)

    results.append([row["Lender"], row["Advance Band"], rate, comm, apr, notes])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR", "Notes"])

# --- DISPLAY ---
if calc_df.empty:
    st.warning("No lenders available for this combination.")
else:
    best_comm = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest_apr = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if x != "Rate for risk" else 99).idxmin()]
    lender_count = calc_df["Lender"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='stat-card best'>Best Commission<br><span style='font-size:24px;'>£{best_comm['Commission (£)']:.0f}</span><br><span class='label'>{best_comm['Lender']}</span></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='stat-card apr'>Lowest APR<br><span style='font-size:24px;'>{lowest_apr['APR']}</span><br><span class='label'>{lowest_apr['Lender']}</span></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='stat-card count'>Lenders<br><span style='font-size:24px;'>{lender_count}</span><br><span class='label'>For £{deal_amount:,.0f}</span></div>", unsafe_allow_html=True)

    st.subheader("Detailed Lender Breakdown")
    st.dataframe(calc_df.sort_values("Commission (£)", ascending=(sort_by != "Highest Commission")), use_container_width=True)
    st.download_button("Download CSV", calc_df.to_csv(index=False).encode(), "commissions.csv")

    st.subheader("Commission Chart")
    chart = calc_df.sort_values("Commission (£)", ascending=False)
    fig = px.bar(chart, x="Lender", y="Commission (£)", title="Commission by Lender", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)
