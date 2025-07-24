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
    "Lender": ["Santander", "Santander", "Santander", "Santander",
               "ZOPA", "ZOPA", "ZOPA",
               "Mann Island",
               "Motion Finance - Alphera", "Motion Finance - BNP", "Motion Finance - CAAF", "Motion Finance - Close",
               "Moto Novo", "Oodle", "Blue", "Startline Low", "Startline High",
               "Marsh Low", "Marsh High",
               "JBR"],
    "Advance Band": ["0-24999", "25000-39999", "40000-49999", "50000+",
                     "0-24999", "25000-39999", "40000-49999",
                     "2500-40000+",
                     "All", "All", "All", "All",
                     "All", "All", "12900-19900",
                     "16900", "19900",
                     "0-30000", "0-30000",
                     "0-500000"],
    "Products": [
        "HP,LP,PCP","HP,LP,PCP","HP,LP,PCP","HP,LP,PCP",
        "HP,PCP","HP,PCP","HP,PCP",
        "HP,PCP,LP",
        "HP,PCP","HP,PCP","HP,PCP","HP,PCP",
        "HP,PCP","HP","HP","HP,PCP","HP,PCP",
        "HP,PCP","HP,PCP",
        "HP,LP"
    ],
    "APR": [12.9, 11.9, 10.9, 9.9,
            12.9, 11.9, 10.9,
            10.9,
            10.9, 10.4, 10.9, 10.9,
            11.9, "Rate for risk", "12.9-19.9",
            16.9, 19.9,
            "14.4-23.9", 26.9,
            10.9],
    "Commission %": ["9.05", "6.8", "5.15", "4",
                     "HP:9.15 PCP:11.15", "HP:7.15 PCP:9.15", "HP:5.15 PCP:7.15",
                     "6.75",
                     "3.5", "3.5", "3.5", "3.5",
                     "2", "7", "8",
                     "5", "5",
                     "0", "0",
                     "5"],
    "Commission Cap": [None, None, None, None,
                       3000, 3000, 3000,
                       3000,
                       None, None, None, None,
                       None, 2500, 2000,
                       2000, 1500,
                       1500, 1500,
                       None],
    "Favourite": [True, True, True, True,
                 True, True, True,
                 True,
                 True, True, True, True,
                 True, False, False,
                 False, False,
                 True, True,
                 True]
}
df = pd.DataFrame(data)

# --- INPUT PANEL ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1,1,1])
with col1:
    deal_amount = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    product_choice = st.selectbox("Product", ["PCP", "HP", "LP"])
with col3:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])
st.markdown("</div>", unsafe_allow_html=True)

# --- SAFE BAND FILTER ---
def band_includes(band, amount):
    if not isinstance(band, str) or band.strip() == "":
        return False
    band = band.replace(",", "").replace("%", "").strip()
    if "All" in band:
        return True
    try:
        if "+" in band:
            numbers = re.findall(r"\d+", band)
            lower = int(numbers[0])
            return amount >= lower
        elif "-" in band:
            numbers = re.findall(r"\d+", band)
            if len(numbers) >= 2:
                lower, upper = int(numbers[0]), int(numbers[1])
                return lower <= amount <= upper
        else:
            number = int(re.findall(r"\d+", band)[0])
            return amount == number
    except:
        return False
    return False

# --- FILTER DATA ---
df_filtered = df[df["Products"].str.contains(product_choice)]
df_filtered = df_filtered[df_filtered["Advance Band"].apply(lambda b: band_includes(b, deal_amount))]
df_fav = df_filtered[df_filtered["Favourite"] == True]

# --- CALCULATE COMMISSIONS ---
results = []
for _, row in df_fav.iterrows():
    comm_str = row['Commission %']
    cap = float(row['Commission Cap']) if row['Commission Cap'] else None
    if "HP:" in comm_str and product_choice in ["HP","PCP"]:
        rate = float(comm_str.split(f"{product_choice}:")[1].split()[0])
    else:
        try: rate = float(comm_str)
        except: rate = 0
    comm = (rate / 100) * deal_amount
    if cap: comm = min(comm, cap)
    lender_name = row['Lender']
    if product_choice == "PCP" and lender_name == "ZOPA":
        lender_name = "⭐ ZOPA (Recommended)"
    results.append([lender_name, row['Advance Band'], rate, comm, row['APR']])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR"])

# --- IF NO DATA ---
if calc_df.empty:
    st.warning("No lenders available for this combination of product and advance amount.")
else:
    # --- PRIORITISE ZOPA FOR PCP ---
    if product_choice == "PCP":
        zopa_df = calc_df[calc_df["Lender"].str.contains("ZOPA")]
        others_df = calc_df[~calc_df["Lender"].str.contains("ZOPA")]
        calc_df = pd.concat([zopa_df, others_df])

    # --- SUMMARY CARDS ---
    best_commission_row = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest_apr_row = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if x != "Rate for risk" else 99).idxmin()]
    lender_count = calc_df["Lender"].nunique()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='stat-card best'>Best Commission<br><span style='font-size:28px;'>£{best_commission_row['Commission (£)']:.0f}</span><br><span class='label'>{best_commission_row['Lender']} ({product_choice})</span></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='stat-card apr'>Lowest APR<br><span style='font-size:28px;'>{lowest_apr_row['APR']}</span><br><span class='label'>{lowest_apr_row['Lender']}</span></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='stat-card count'>Available Lenders<br><span style='font-size:28px;'>{lender_count}</span><br><span class='label'>For £{deal_amount:,.0f}</span></div>", unsafe_allow_html=True)

    # --- TABLE ---
    st.subheader("Detailed Lender Data")
    st.markdown("**Zopa PCP is prioritised — review this first as their balloons may outperform Santander.**")
    if sort_by == "Highest Commission":
        display_df = calc_df.sort_values(by="Commission (£)", ascending=False)
    else:
        display_df = calc_df.sort_values(by="APR", ascending=True)
    st.dataframe(display_df, use_container_width=True)

    # --- DOWNLOAD ---
    st.download_button("Download as CSV", calc_df.to_csv(index=False).encode(), "commissions.csv")

    # --- CHART ---
    st.subheader("Commission by Lender")
    ranked = calc_df.sort_values(by="Commission (£)", ascending=False)
    ranked['Colour'] = ['#FFD700' if "ZOPA" in l else '#1e3d59' for l in ranked['Lender']]
    fig = px.bar(ranked, x="Lender", y="Commission (£)", title="Commission Amount by Lender", text_auto=True)
    fig.update_traces(marker_color=ranked['Colour'])
    fig.update_layout(plot_bgcolor="#f8f9fa", paper_bgcolor="#f8f9fa", font=dict(size=16, color="#1e3d59"))
    st.plotly_chart(fig, use_container_width=True)
