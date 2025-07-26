import pandas as pd
import streamlit as st
import plotly.express as px
import os
import re
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Saxton4x4 Lender Commission Tool", page_icon="💰", layout="wide")

DATA_PATH = "data/Saxton Rates and Commissions.xlsx"
os.makedirs("data", exist_ok=True)

@st.cache_data
def load_data(file_path):
    df = pd.read_excel(file_path)
    return df

def save_uploaded_file(uploaded_file):
    with open(DATA_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return DATA_PATH

def band_includes(band, amount):
    if not isinstance(band, str) or band.strip() == "":
        return False
    band = band.replace(",", "").replace("%", "").strip()
    if "All" in band:
        return True
    try:
        if "+" in band:
            lower = int(re.findall(r"\d+", band)[0])
            return amount >= lower
        elif "-" in band:
            nums = re.findall(r"\d+", band)
            if len(nums) >= 2:
                lower, upper = int(nums[0]), int(nums[1])
                return lower <= amount <= upper
        else:
            number = int(re.findall(r"\d+", band)[0])
            return amount == number
    except:
        return False
    return False

if os.path.exists(DATA_PATH):
    df = load_data(DATA_PATH)
    last_updated = datetime.fromtimestamp(os.path.getmtime(DATA_PATH)).strftime("%d %b %Y %H:%M")
else:
    df = pd.DataFrame(columns=["Lender","Advance Band","Products","APR","Commission %","Commission Cap","Favourite"])
    last_updated = "Never"

st.markdown("<h1 style='text-align:center;color:#1e3d59;'>Saxton4x4 Lender Commission Tool</h1>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload updated Excel", type=["xlsx"])
if uploaded_file:
    save_uploaded_file(uploaded_file)
    df = load_data(DATA_PATH)
    last_updated = datetime.now().strftime("%d %b %Y %H:%M")
    st.success("Lender data successfully updated.")

st.write(f"**Last updated:** {last_updated}")
st.download_button("Download Template", data=open(DATA_PATH,"rb").read(), file_name="Saxton Rates and Commissions.xlsx")

col1, col2 = st.columns([2,1])
with col1:
    deal_amount = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])

st.markdown("### Select Product")
prod_col1, prod_col2, prod_col3 = st.columns(3)
with prod_col1:
    if st.button("PCP", key="pcp_btn"):
        product_choice = "PCP"
with prod_col2:
    if st.button("HP", key="hp_btn"):
        product_choice = "HP"
with prod_col3:
    if st.button("LP", key="lp_btn"):
        product_choice = "LP"
if "product_choice" not in locals():
    product_choice = "PCP"

df_filtered = df[df["Products"].str.contains(product_choice)]
df_filtered = df_filtered[df_filtered["Advance Band"].apply(lambda b: band_includes(b, deal_amount))]
df_fav = df_filtered[df_filtered["Favourite"] == True]

results = []
for _, row in df_fav.iterrows():
    comm_str = str(row['Commission %'])
    cap = float(row['Commission Cap']) if row['Commission Cap'] else None
    if "HP:" in comm_str and product_choice in ["HP","PCP"]:
        rate = float(comm_str.split(f"{product_choice}:")[1].split()[0])
    else:
        try: rate = float(comm_str)
        except: rate = 0
    comm = (rate / 100) * deal_amount
    if cap: comm = min(comm, cap)
    lender_name = row['Lender']
    if product_choice == "PCP" and "ZOPA" in lender_name.upper():
        lender_name = "⭐ ZOPA (Recommended)"
    results.append([lender_name, row['Advance Band'], rate, comm, row['APR']])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR"])

if calc_df.empty:
    st.warning("No lenders available for this combination.")
else:
    if product_choice == "PCP":
        zopa_df = calc_df[calc_df["Lender"].str.contains("ZOPA")]
        others_df = calc_df[~calc_df["Lender"].str.contains("ZOPA")]
        calc_df = pd.concat([zopa_df, others_df])

    best_commission_row = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest_apr_row = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if x != "Rate for risk" else 99).idxmin()]
    lender_count = calc_df["Lender"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Best Commission", f"£{best_commission_row['Commission (£)']:.0f}", best_commission_row['Lender'])
    c2.metric("Lowest APR", lowest_apr_row['APR'], lowest_apr_row['Lender'])
    c3.metric("Available Lenders", lender_count, f"For £{deal_amount:,.0f}")

    st.info("**Zopa PCP is prioritised — review this first as their balloons may outperform Santander.**\n\n**If declined with Zopa, message Taylor regardless — she may be able to overturn the decision.**")

    st.subheader("Detailed Lender Data")
    if sort_by == "Highest Commission":
        display_df = calc_df.sort_values(by="Commission (£)", ascending=False)
    else:
        display_df = calc_df.sort_values(by="APR", ascending=True)

    def highlight_zopa(row):
        return ['background-color: #d4edda' if 'ZOPA' in str(row['Lender']).upper() else '' for _ in row]
    st.dataframe(display_df.style.apply(highlight_zopa, axis=1), use_container_width=True)

    csv_data = calc_df.to_csv(index=False).encode()
    xlsx_data = BytesIO()
    calc_df.to_excel(xlsx_data, index=False)
    st.download_button("Download CSV", csv_data, "commissions.csv")
    st.download_button("Download Excel", xlsx_data.getvalue(), "commissions.xlsx")

    st.subheader("Commission by Lender")
    ranked = calc_df.sort_values(by="Commission (£)", ascending=False)
    ranked['Colour'] = ['#FFD700' if "ZOPA" in l.upper() else '#1e3d59' for l in ranked['Lender']]
    fig = px.bar(ranked, x="Lender", y="Commission (£)", title="Commission Amount by Lender", text_auto=True)
    fig.update_traces(marker_color=ranked['Colour'])
    fig.update_layout(plot_bgcolor="#f8f9fa", paper_bgcolor="#f8f9fa", font=dict(size=16, color="#1e3d59"))
    st.plotly_chart(fig, use_container_width=True)
