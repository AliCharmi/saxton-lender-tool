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
    # Normalise column names
    df.columns = df.columns.str.strip().str.replace(r'\s+', ' ', regex=True).str.title()
    col_map = {
        'Apr (%)': 'APR',
        'Apr': 'APR',
        'Introductory Comms (Hp)': 'Commission %',
        'Introductory Comms (Pcp)': 'Commission %',
        'Commissions Cap (£)': 'Commission Cap',
        'Comission Cap (£)': 'Commission Cap'
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)
    # Ensure required columns exist
    required_cols = ["Lender", "Advance Band", "Products", "APR", "Commission %", "Commission Cap", "Preference"]
    for col in required_cols:
        if col not in df.columns:
            if col == "Products":
                df[col] = "HP,PCP,LP"
            elif col == "Preference":
                df[col] = "Green"
            else:
                df[col] = 0
    # Clean numeric columns
    for col in ["APR", "Commission %", "Commission Cap"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace("%", "").str.replace("£", "").str.replace(",", "").str.strip(), errors='coerce')
    # Validate
    if "Lender" not in df.columns or "Advance Band" not in df.columns:
        st.error("Uploaded Excel is missing essential columns like 'Lender' or 'Advance Band'. Please check the template.")
        return pd.DataFrame(columns=required_cols)
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
    df = pd.DataFrame(columns=["Lender","Advance Band","Products","APR","Commission %","Commission Cap","Preference"])
    last_updated = "Never"

# Header
st.markdown("<h1 style='text-align:center;color:#1e3d59;'>Saxton4x4 Lender Commission Tool</h1>", unsafe_allow_html=True)

# Upload
uploaded_file = st.file_uploader("Upload updated Excel", type=["xlsx"])
if uploaded_file:
    save_uploaded_file(uploaded_file)
    df = load_data(DATA_PATH)
    last_updated = datetime.now().strftime("%d %b %Y %H:%M")
    st.success("Lender data successfully updated.")

# Data health
incomplete_rows = df[df["APR"].isnull() | df["Commission %"].isnull()]
total_lenders = df["Lender"].nunique()
if len(incomplete_rows) > 0:
    st.warning(f"⚠️ {len(incomplete_rows)} rows have missing APR or commission values. Please check the Excel.")
else:
    st.success("All data is healthy.")

st.markdown(f"**Lenders loaded:** {total_lenders} | **Incomplete rows:** {len(incomplete_rows)} | **Last updated:** {last_updated}")
st.download_button("Download Template", data=open(DATA_PATH,"rb").read(), file_name="Saxton Rates and Commissions.xlsx")

# Inputs
col1, col2 = st.columns([2,1])
with col1:
    deal_amount = st.number_input("Advance Amount (£)", min_value=0, max_value=500000, value=30000, step=500)
with col2:
    sort_by = st.selectbox("Sort By", ["Highest Commission", "Lowest APR"])

# Product selection
st.markdown("### Select Product")
prod_col1, prod_col2, prod_col3 = st.columns(3)
if "product_choice" not in st.session_state:
    st.session_state.product_choice = "PCP"
if prod_col1.button("PCP", key="pcp_btn"): st.session_state.product_choice = "PCP"
if prod_col2.button("HP", key="hp_btn"): st.session_state.product_choice = "HP"
if prod_col3.button("LP", key="lp_btn"): st.session_state.product_choice = "LP"
product_choice = st.session_state.product_choice

# Filter
df_filtered = df[df["Products"].str.contains(product_choice, case=False, na=False)]
df_filtered = df_filtered[df_filtered["Advance Band"].apply(lambda b: band_includes(b, deal_amount))]

# Calculate commissions
results = []
for _, row in df_filtered.iterrows():
    rate = row['Commission %'] if not pd.isna(row['Commission %']) else 0
    cap = row['Commission Cap'] if not pd.isna(row['Commission Cap']) else None
    comm = (rate / 100) * deal_amount
    if cap: comm = min(comm, cap)
    lender_name = row['Lender']
    if product_choice == "PCP" and "ZOPA" in lender_name.upper():
        lender_name = "⭐ ZOPA (Recommended)"
    results.append([lender_name, row['Advance Band'], row['Products'], rate, comm, row['APR'], row['Preference']])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Products", "Commission %", "Commission (£)", "APR", "Preference"])

# Display
if calc_df.empty:
    st.warning("No lenders available for this combination.")
else:
    # Zopa priority
    if product_choice == "PCP":
        zopa_df = calc_df[calc_df["Lender"].str.contains("ZOPA")]
        others_df = calc_df[~calc_df["Lender"].str.contains("ZOPA")]
        calc_df = pd.concat([zopa_df, others_df])

    # KPIs
    best_commission_row = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest_apr_row = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if pd.notna(x) else 99).idxmin()]
    lender_count = calc_df["Lender"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Best Commission", f"£{best_commission_row['Commission (£)']:.0f}", best_commission_row['Lender'])
    c2.metric("Lowest APR", lowest_apr_row['APR'], lowest_apr_row['Lender'])
    c3.metric("Available Lenders", lender_count, f"For £{deal_amount:,.0f}")

    # Info box
    st.info("**Zopa PCP is prioritised — review this first as their balloons may outperform Santander.**\n\n**If declined with Zopa, message Taylor regardless — she may be able to overturn the decision.**")

    # Search box
    search_term = st.text_input("Search for a lender")
    if search_term:
        display_df = calc_df[calc_df["Lender"].str.contains(search_term, case=False)]
    else:
        display_df = calc_df.copy()

    # Sort
    if sort_by == "Highest Commission":
        display_df = display_df.sort_values(by="Commission (£)", ascending=False)
    else:
        display_df = display_df.sort_values(by="APR", ascending=True)

    # Highlighting
    def style_rows(row):
        if pd.isna(row['APR']) or pd.isna(row['Commission %']):
            return ['background-color: #f8d7da']*len(row)  # red for incomplete
        if 'ZOPA' in str(row['Lender']).upper():
            return ['background-color: #d4edda']*len(row)  # green for Zopa
        return ['']*len(row)
    st.dataframe(display_df.style.apply(style_rows, axis=1), use_container_width=True)

    # Downloads
    csv_data = calc_df.to_csv(index=False).encode()
    xlsx_data = BytesIO()
    calc_df.to_excel(xlsx_data, index=False)
    st.download_button("Download CSV", csv_data, "commissions.csv")
    st.download_button("Download Excel", xlsx_data.getvalue(), "commissions.xlsx")

    # Chart
    st.subheader("Commission by Lender (click bar to filter)")
    ranked = calc_df.sort_values(by="Commission (£)", ascending=False)
    ranked['Colour'] = ranked['Preference'].map({'Green':'#28a745','Amber':'#ffc107','Red':'#dc3545'}).fillna('#1e3d59')
    fig = px.bar(ranked, x="Lender", y="Commission (£)", title="Commission Amount by Lender", text_auto=True)
    fig.update_traces(marker_color=ranked['Colour'])
    fig.update_layout(plot_bgcolor="#f8f9fa", paper_bgcolor="#f8f9fa", font=dict(size=16, color="#1e3d59"))
    st.plotly_chart(fig, use_container_width=True)
