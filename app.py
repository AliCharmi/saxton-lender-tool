import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- CONFIG ---
st.set_page_config(page_title="Saxtons Lender Tool", layout="wide")

# --- LOGIN ---
def login():
    st.markdown("### Login to Saxtons Tool")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username == "Saxtons1" and password == "Saxtons1":
                return True
            else:
                st.error("Incorrect username or password.")
                return False
    return False

if not login():
    st.stop()

# --- HEADER ---
st.markdown("<h1 style='text-align:center; color:#1e3d59;'>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- LOAD DATA FROM GITHUB ---
url = "https://raw.githubusercontent.com/AliCharmi/saxton-lender-tool/main/data/commission_data_clean.xlsx"

@st.cache_data
def load_data():
    return pd.read_excel(url)

df = load_data()

# --- CLEANING ---
df["Favourite"] = df["Favourite"].fillna(False)
if "Notes" not in df.columns:
    df["Notes"] = ""

# --- INPUT PANEL ---
st.markdown("<div style='background:#fff;padding:20px;border-radius:10px;margin-bottom:20px;'>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    amount = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    product = st.selectbox("Product", ["HP", "PCP", "LP"])
with col3:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])
with col4:
    term = st.selectbox("Term (months)", [24, 36, 48, 60])
st.markdown("</div>", unsafe_allow_html=True)

# --- FILTERING ---
def band_includes(band, amount):
    band = str(band).replace(",", "")
    if "All" in band:
        return True
    if "+" in band:
        return amount >= int(re.findall(r"\d+", band)[0])
    if "-" in band:
        nums = re.findall(r"\d+", band)
        if len(nums) == 2:
            return int(nums[0]) <= amount <= int(nums[1])
    return False

df = df[df["Products"].str.contains(product)]
df = df[df["Advance Band"].apply(lambda x: band_includes(x, amount))]
df_fav = df[df["Favourite"] == True]

# --- CALCULATIONS ---
results = []
for _, row in df_fav.iterrows():
    lender = row["Lender"]
    apr = row["APR"]
    cap = row["Commission Cap"]
    notes = row["Notes"]
    comm_raw = row["Commission %"]

    # Get correct rate (if dual HP:xx PCP:xx etc)
    if isinstance(comm_raw, str) and f"{product}:" in comm_raw:
        try:
            rate = float(comm_raw.split(f"{product}:")[1].split()[0])
        except:
            rate = 0
    else:
        try:
            rate = float(comm_raw)
        except:
            rate = 0

    comm = (rate / 100) * amount
    est_interest = (rate / 100) * amount * (term / 12)

    if lender == "Admiral":
        if term < 36:
            continue
        comm = min(comm, est_interest * 0.5)

    if pd.notnull(cap):
        comm = min(comm, cap)

    lender_display = lender
    if lender == "ZOPA" and product == "PCP":
        lender_display = "⭐ ZOPA (Recommended)"

    results.append([lender_display, row["Advance Band"], rate, round(comm), apr, notes])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR", "Notes"])

# --- DISPLAY ---
if calc_df.empty:
    st.warning("No lenders available for this combination.")
    st.stop()

# --- PRIORITISE ZOPA ON PCP ---
if product == "PCP":
    zopa = calc_df[calc_df["Lender"].str.contains("ZOPA")]
    rest = calc_df[~calc_df["Lender"].str.contains("ZOPA")]
    calc_df = pd.concat([zopa, rest])

# --- STATS ---
best_comm = calc_df.loc[calc_df["Commission (£)"].idxmax()]
lowest_apr = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if x != "Rate for risk" else 99).idxmin()]
lender_count = calc_df["Lender"].nunique()

col1, col2, col3 = st.columns(3)
col1.markdown(f"<div class='stat-card best'>Best Commission<br><span style='font-size:28px;'>£{best_comm['Commission (£)']:.0f}</span><br><span class='label'>{best_comm['Lender']}</span></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='stat-card apr'>Lowest APR<br><span style='font-size:28px;'>{lowest_apr['APR']}</span><br><span class='label'>{lowest_apr['Lender']}</span></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='stat-card count'>Available Lenders<br><span style='font-size:28px;'>{lender_count}</span><br><span class='label'>For £{amount:,.0f}</span></div>", unsafe_allow_html=True)

# --- NOTES ---
st.info("""
**Zopa PCP is prioritised — review this first as their balloons may outperform Santander.**  
**If declined with Zopa, message Taylor regardless — she may be able to overturn the decision.**  
**Admiral commission only applies to terms ≥ 36 months, capped at £2,500 or 50% of customer interest.**  
**Admiral to be approached after Santander and Zopa as they are in front of the others on their PCP and HP offering, however is rate for risk, so always check the acceptance for full balance and Comms cap.**  
**JBR now ahead of Santander on £40k+ and Zopa on £33k+ for HP — ensure 10% deposit and products covered by deposit.**
""")

# --- TABLE ---
st.subheader("Lender Details")
def highlight_zopa(row):
    return ['background-color: #d4edda' if 'ZOPA' in str(row['Lender']) else '' for _ in row]
st.dataframe(calc_df.style.apply(highlight_zopa, axis=1), use_container_width=True)

# --- DOWNLOAD ---
st.download_button("Download as CSV", calc_df.to_csv(index=False).encode(), "commission_output.csv")

# --- CHART ---
st.subheader("Commission by Lender")
ranked = calc_df.sort_values("Commission (£)", ascending=False)
ranked['Colour'] = ['#FFD700' if "ZOPA" in l else '#1e3d59' for l in ranked['Lender']]
fig = px.bar(ranked, x="Lender", y="Commission (£)", title="Commission Amount by Lender", text_auto=True)
fig.update_traces(marker_color=ranked['Colour'])
fig.update_layout(plot_bgcolor="#f8f9fa", paper_bgcolor="#f8f9fa", font=dict(size=16, color="#1e3d59"))
st.plotly_chart(fig, use_container_width=True)


