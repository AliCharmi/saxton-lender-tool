import pandas as pd
import streamlit as st
import plotly.express as px
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="Saxton4x4 Lender Commission Tool", page_icon="💰", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp {background-color: #f8f9fa; font-family: 'Arial', sans-serif;}
    h1 {color: #1e3d59; text-align: center; margin-bottom: 10px;}
    .input-card {background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.1); margin-bottom: 20px;}
    .stat-card {padding: 20px; border-radius: 10px; color: #1e3d59;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.1); font-size: 20px; font-weight: bold; margin-bottom: 15px;}
    .best {background-color: #e8f9f0;} .apr {background-color: #e8f1fb;} .count {background-color: #f5e8fb;}
    .label {font-size:16px; font-weight: normal; color: #555;}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1>Saxton4x4 Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- DATASET ---
data = {
    "Lender": ["Santander", "ZOPA", "Admiral"],
    "Advance Band": ["0-60000", "0-50000", "0-60000"],
    "Products": ["HP,PCP", "HP,PCP", "HP,PCP"],
    "APR": ["9.9", "10.9", "9.9-25"],
    "Commission %": ["5", "HP:5.15 PCP:7.15", "7.5"],
    "Commission Cap": [None, 3000, 2500],
    "Favourite": [True, True, True]
}
df = pd.DataFrame(data)

# --- INPUT PANEL ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    deal_amount = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    product_choice = st.selectbox("Product", ["PCP", "HP", "LP"])
with col3:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])
with col4:
    deal_term = st.number_input("Term (months)", min_value=1, max_value=60, value=48)
st.markdown("</div>", unsafe_allow_html=True)

# --- SAFE BAND FILTER ---
def band_includes(band, amount):
    if not isinstance(band, str) or band.strip() == "": return False
    band = band.replace(",", "").replace("%", "").strip()
    if "All" in band: return True
    try:
        if "+" in band:
            lower = int(re.findall(r"\d+", band)[0])
            return amount >= lower
        elif "-" in band:
            nums = list(map(int, re.findall(r"\d+", band)))
            return nums[0] <= amount <= nums[1]
        else:
            return int(re.findall(r"\d+", band)[0]) == amount
    except: return False

# --- FILTER DATA ---
df_filtered = df[df["Products"].str.contains(product_choice)]
df_filtered = df_filtered[df_filtered["Advance Band"].apply(lambda b: band_includes(b, deal_amount))]
df_fav = df_filtered[df_filtered["Favourite"] == True]

# --- CALCULATE COMMISSIONS ---
results = []
for _, row in df_fav.iterrows():
    comm_str = row['Commission %']
    cap = float(row['Commission Cap']) if row['Commission Cap'] else None
    if "HP:" in comm_str and product_choice in ["HP", "PCP"]:
        rate = float(comm_str.split(f"{product_choice}:")[1].split()[0])
    else:
        try: rate = float(comm_str)
        except: rate = 0
    comm = (rate / 100) * deal_amount

    if row['Lender'] == "Admiral":
        if deal_term < 36:
            continue
        try:
            apr_low = float(str(row['APR']).split('-')[0])
        except:
            apr_low = 25
        interest = (deal_amount * (apr_low / 100))
        comm = min(comm, 2500, interest * 0.5)
    elif cap:
        comm = min(comm, cap)

    results.append([row['Lender'], row['Advance Band'], rate, comm, row['APR']])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR"])

# --- DISPLAY ---
if calc_df.empty:
    st.warning("No lenders available for this combination.")
else:
    best = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest = calc_df.loc[calc_df['APR'].apply(lambda x: float(str(x).split('-')[0])).idxmin()]
    count = calc_df['Lender'].nunique()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='stat-card best'>Best Commission<br><span style='font-size:28px;'>£{best['Commission (£)']:.0f}</span><br><span class='label'>{best['Lender']} ({product_choice})</span></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-card apr'>Lowest APR<br><span style='font-size:28px;'>{lowest['APR']}</span><br><span class='label'>{lowest['Lender']}</span></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='stat-card count'>Available Lenders<br><span style='font-size:28px;'>{count}</span><br><span class='label'>For £{deal_amount:,}</span></div>", unsafe_allow_html=True)

    st.info("""
    **Zopa PCP is prioritised — review this first as their balloons may outperform Santander.**  
    **If declined with Zopa, message Taylor regardless — she may be able to overturn the decision.**  
    **Admiral commission only applies to terms ≥ 36 months, capped at £2,500 or 50% of customer interest.**
    """)

    st.subheader("Detailed Lender Data")
    sorted_df = calc_df.sort_values(by="Commission (£)" if sort_by=="Highest Commission" else "APR")
    st.dataframe(sorted_df, use_container_width=True)

    st.download_button("Download as CSV", calc_df.to_csv(index=False).encode(), "commissions.csv")

    st.subheader("Commission by Lender")
    chart = px.bar(sorted_df, x="Lender", y="Commission (£)", text_auto=True)
    chart.update_layout(plot_bgcolor="#f8f9fa", paper_bgcolor="#f8f9fa", font=dict(size=16, color="#1e3d59"))
    st.plotly_chart(chart, use_container_width=True)
