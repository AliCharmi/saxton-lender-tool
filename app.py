import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- LOGIN CONFIG ---
USERNAME = "Saxtons1"
PASSWORD = "Saxtons1"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("login_form"):
        st.markdown("""
            <style>
                .stTextInput > div > div > input {
                    font-size: 16px;
                    padding: 0.75rem;
                }
            </style>
        """, unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>🔐 Login to Access Commission Tool</h3>", unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login = st.form_submit_button("Login")

        if login:
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
                st.experimental_rerun()
            else:
                st.error("Incorrect username or password")
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Saxtons Lender Tool", page_icon="💷", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    body, .stApp {
        background-color: #f4f6f8;
        font-family: 'Segoe UI', sans-serif;
    }
    h1 {
        color: #002b45;
        text-align: center;
    }
    .input-card, .stat-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .stat-card h4 {
        margin: 0 0 5px 0;
        color: #555;
    }
    .best { background-color: #e7f6ec; }
    .apr { background-color: #e7eff9; }
    .count { background-color: #f9e7f3; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- DATASET ---
data = [
    ["Santander", "0-24999", "HP,LP,PCP", 12.9, 9.05, None],
    ["Santander", "25000-39999", "HP,LP,PCP", 11.9, 6.8, None],
    ["Santander", "40000-49999", "HP,LP,PCP", 10.9, 5.15, None],
    ["Santander", "50000+", "HP,LP,PCP", 9.9, 4, None],
    ["ZOPA", "0-24999", "HP,PCP", 12.9, "HP:9.15 PCP:11.15", 3000],
    ["ZOPA", "25000-32999", "HP,PCP", 11.9, "HP:7.15 PCP:9.15", 3000],
    ["ZOPA", "33000-50000", "HP,PCP", 10.9, "HP:5.15 PCP:7.15", 3000],
    ["Mann Island", "2500-40000+", "HP,PCP,LP", 10.9, 6.75, 3000],
    ["JBR", "0-500000", "HP,LP", 10.9, 5.5, None],
    ["Admiral", "0-60000", "HP,PCP", "9.9-25.0", 7.5, 2500],
    ["Tandem", "0-60000", "HP", "10.9-19.9", 7.0, 2000]
]

columns = ["Lender", "Advance Band", "Products", "APR", "Commission %", "Commission Cap"]
df = pd.DataFrame(data, columns=columns)

# --- INPUT PANEL ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    deal_amount = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    product_choice = st.selectbox("Product", ["PCP", "HP", "LP"])
with col3:
    term_months = st.selectbox("Term (months)", [24, 36, 48, 60])
with col4:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])
st.markdown("</div>", unsafe_allow_html=True)

# --- FILTER FUNCTION ---
def band_includes(band, amount):
    band = band.replace(",", "").strip()
    if "All" in band:
        return True
    if "+" in band:
        return amount >= int(re.findall(r"\d+", band)[0])
    elif "-" in band:
        nums = list(map(int, re.findall(r"\d+", band)))
        return nums[0] <= amount <= nums[1]
    else:
        return amount == int(re.findall(r"\d+", band)[0])

# --- FILTER & CALCULATE ---
df = df[df["Products"].str.contains(product_choice)]
df = df[df["Advance Band"].apply(lambda x: band_includes(x, deal_amount))]

results = []
for _, row in df.iterrows():
    comm_rate = row["Commission %"]
    cap = float(row["Commission Cap"]) if pd.notnull(row["Commission Cap"]) else None

    if isinstance(comm_rate, str) and f"{product_choice}:" in comm_rate:
        rate = float(comm_rate.split(f"{product_choice}:")[1].split()[0])
    else:
        try: rate = float(comm_rate)
        except: rate = 0

    interest = (rate / 100) * deal_amount * (term_months / 12)
    comm = (rate / 100) * deal_amount

    if row["Lender"] == "Admiral" and term_months < 36:
        continue
    if row["Lender"] == "Admiral":
        comm = min(comm, interest * 0.5)
    if cap:
        comm = min(comm, cap)

    results.append([row["Lender"], row["Advance Band"], rate, comm, row["APR"]])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR"])

# --- DISPLAY ---
if calc_df.empty:
    st.warning("No lenders available for this combination.")
else:
    if product_choice == "PCP":
        zopa = calc_df[calc_df["Lender"].str.contains("ZOPA")]
        others = calc_df[~calc_df["Lender"].str.contains("ZOPA")]
        calc_df = pd.concat([zopa, others])

    top = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    low_apr = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if x != "Rate for risk" else 99).idxmin()]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='stat-card best'><h4>Best Commission</h4><p style='font-size:24px;'>£{top['Commission (£)']:.0f}</p><div>{top['Lender']}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='stat-card apr'><h4>Lowest APR</h4><p style='font-size:24px;'>{low_apr['APR']}</p><div>{low_apr['Lender']}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='stat-card count'><h4>Lenders Found</h4><p style='font-size:24px;'>{calc_df['Lender'].nunique()}</p><div>on £{deal_amount}</div></div>", unsafe_allow_html=True)

    st.info("""
    **Zopa PCP is prioritised — review this first as their balloons may outperform Santander.**  
    **Admiral: commission only applies for terms ≥ 36 months, capped at £2,500 or 50% of customer interest.**  
    **Admiral to be approached after Santander and Zopa — always check the full balance and comms cap.**
    """)

    st.subheader("Lender Breakdown")
    calc_df = calc_df.sort_values("Commission (£)", ascending=(sort_by != "Highest Commission"))
    st.dataframe(calc_df, use_container_width=True)

    st.download_button("Download CSV", calc_df.to_csv(index=False).encode(), "commissions.csv")

    fig = px.bar(calc_df.sort_values("Commission (£)", ascending=False), x="Lender", y="Commission (£)",
                 title="Commission by Lender", text_auto=True)
    fig.update_layout(plot_bgcolor="#f4f6f8", paper_bgcolor="#f4f6f8", font=dict(size=16))
    st.plotly_chart(fig, use_container_width=True)
