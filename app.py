import pandas as pd
import streamlit as st
import plotly.express as px
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="Saxtons Lender Commission Tool", page_icon="💰", layout="wide")

# --- AUTH ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.form("login_form"):
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login = st.form_submit_button("Login")
        if login:
            if username == "Saxtons1" and password == "Saxtons1":
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Invalid login. Please try again.")
    st.stop()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp {background-color: #f5f7fa; font-family: 'Arial', sans-serif;}
    h1 {color: #1e3d59; text-align: center; margin-bottom: 10px;}
    .input-card {background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.1); margin-bottom: 20px;}
    .stat-card {padding: 20px; border-radius: 10px; color: #1e3d59;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.1); font-size: 20px; font-weight: bold; margin-bottom: 15px;}
    .best {background-color: #e8f9f0;} .apr {background-color: #e8f1fb;} .count {background-color: #f5e8fb;}
    .label {font-size:16px; font-weight: normal; color: #555;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- DATA ---
EXCEL_URL = "https://github.com/AliCharmi/saxton-lender-tool/raw/main/data/commission_data_clean.xlsx"
@st.cache_data
def load_data():
    df = pd.read_excel(EXCEL_URL)
    df["Notes"] = df["Notes"].fillna("")
    return df

df = load_data()

# --- INPUT ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
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
applicable = applicable[applicable["Favourite"] == True]

results = []
for _, row in applicable.iterrows():
    comm_rate = row["Commission %"]
    cap = float(row["Commission Cap"]) if pd.notnull(row["Commission Cap"]) else None
    apr = row["APR"]

    if isinstance(comm_rate, str) and f"{product_choice}:" in comm_rate:
        rate = float(comm_rate.split(f"{product_choice}:")[1].split()[0])
    else:
        try: rate = float(comm_rate)
        except: rate = 0

    interest_est = (rate / 100) * deal_amount * (term_months / 12)
    comm = (rate / 100) * deal_amount

    if row["Lender"] == "Admiral":
        if term_months < 36: continue
        comm = min(comm, interest_est * 0.5)
    if cap: comm = min(comm, cap)

    lender_display = row["Lender"]
    if row["Lender"] == "ZOPA" and product_choice == "PCP":
        lender_display = "⭐ ZOPA (Recommended)"

    results.append([lender_display, row["Advance Band"], rate, comm, apr, row["Notes"]])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR", "Notes"])

# --- DISPLAY ---
if calc_df.empty:
    st.warning("No lenders available for this combination.")
else:
    if product_choice == "PCP":
        zopa = calc_df[calc_df["Lender"].str.contains("ZOPA")]
        others = calc_df[~calc_df["Lender"].str.contains("ZOPA")]
        calc_df = pd.concat([zopa, others])

    best_comm = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest_apr = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if x != "Rate for risk" else 99).idxmin()]
    lender_count = calc_df["Lender"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='stat-card best'>Best Commission<br><span style='font-size:28px;'>£{best_comm['Commission (£)']:.0f}</span><br><span class='label'>{best_comm['Lender']} ({product_choice})</span></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='stat-card apr'>Lowest APR<br><span style='font-size:28px;'>{lowest_apr['APR']}</span><br><span class='label'>{lowest_apr['Lender']}</span></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='stat-card count'>Available Lenders<br><span style='font-size:28px;'>{lender_count}</span><br><span class='label'>For £{deal_amount:,.0f}</span></div>", unsafe_allow_html=True)

    st.info("""
    **Zopa PCP is prioritised — review this first as their balloons may outperform Santander.**  
    **If declined with Zopa, message Taylor regardless — she may be able to overturn the decision.**  
    **Admiral commission only applies to terms ≥ 36 months, capped at £2,500 or 50% of customer interest.**  
    **Admiral to be approached after Santander and Zopa as they are in front of the others on their PCP and HP offering, however is rate for risk, so always check the acceptance for full balance and Comms cap. If comms get capped, then we need to check if it gets more elsewhere.**  
    **There has been a Comms update with JBR which now puts them in front of Santander on £40k+ Advances and Zopa on £33k+ on HP Only.**
    """)

    st.subheader("Detailed Lender Data")
    df_to_show = calc_df.sort_values("Commission (£)", ascending=(sort_by != "Highest Commission"))

    def highlight(row): return ["background-color: #d4edda" if 'ZOPA' in str(row['Lender']) else '' for _ in row]
    st.dataframe(df_to_show.style.apply(highlight, axis=1), use_container_width=True)

    st.download_button("Download as CSV", df_to_show.to_csv(index=False).encode(), "commissions.csv")

    st.subheader("Commission by Lender")
    ranked = df_to_show.sort_values("Commission (£)", ascending=False)
    ranked['Colour'] = ['#FFD700' if "ZOPA" in l else '#1e3d59' for l in ranked['Lender']]
    fig = px.bar(ranked, x="Lender", y="Commission (£)", title="Commission Amount by Lender", text_auto=True)
    fig.update_traces(marker_color=ranked['Colour'])
    fig.update_layout(plot_bgcolor="#f8f9fa", paper_bgcolor="#f8f9fa", font=dict(size=16, color="#1e3d59"))
    st.plotly_chart(fig, use_container_width=True)
