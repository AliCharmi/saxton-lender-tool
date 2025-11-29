import pandas as pd
import streamlit as st
import plotly.express as px
import re

st.set_page_config(page_title="Saxtons Lender Commission Tool", page_icon="💰", layout="wide")

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

st.markdown("<h1>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

data = [
    ["Santander", "0-24999", "HP,LP,PCP", 12.9, 9.05, None, True, ""],
    ["Santander", "25000-39999", "HP,LP,PCP", 11.9, 6.8, None, True, ""],
    ["Santander", "40000-49999", "HP,LP,PCP", 10.9, 5.15, None, True, ""],
    ["Santander", "50000+", "HP,LP,PCP", 9.9, 4, None, True, ""],
    ["ZOPA", "0-24999", "HP,PCP", 12.9, "HP:9.15 PCP:11.15", 3000, True, ""],
    ["ZOPA", "25000-32999", "HP,PCP", 11.9, "HP:7.15 PCP:9.15", 3000, True, ""],
    ["ZOPA", "33000-50000", "HP,PCP", 10.9, "HP:5.15 PCP:7.15", 3000, True, ""],
    ["Mann Island", "2500-40000+", "HP,PCP,LP", 10.9, 6.75, 3000, True, ""],
    ["Oodle & Blue", "All", "HP", "12.9-19.9", 8, 2000, False, ""],
    ["Startline Low", "16900", "HP,PCP", 16.9, 5, 2000, False, ""],
    ["Startline High", "19900", "HP,PCP", 19.9, 5, 1500, False, ""],
    ["Marsh Low", "0-30000", "HP,PCP", "14.4-23.9", 0, 1500, True, ""],
    ["Marsh High", "0-30000", "HP,PCP", 26.9, 0, 1500, True, ""],
    ["JBR", "0-500000", "HP,LP", 10.9, 5.5, None, True, "There has been a Comms update with JBR which now puts them in front of Santander on £40k+ Advances and Zopa on £33k+ on HP Only."],
    ["Admiral", "0-60000", "HP,PCP", "9.9-25.0", 7.5, 2500, True, "Admiral commission only applies to terms ≥ 36 months, capped at £2,500 or 50% of customer interest. Approach after Santander & Zopa. Check acceptance & caps."],
    ["Tandem", "0-60000", "HP", "10.9-19.9", 7.0, 2000, True, ""],
    ["Abound", "0-50000", "HP", 18.9, 5.0, None, False, "Ideal for customers with negative equity. Can support deals where traditional lenders decline."],
    ["GoCarCredit", "0-25000", "HP", 24.9, 1.0, None, False, "Use only as last resort. Speak to Luke or Ali before payout."]
]

columns = ["Lender", "Advance Band", "Products", "APR", "Commission %", "Commission Cap", "Favourite", "Notes"]
df = pd.DataFrame(data, columns=columns)

# UI Input
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

def band_includes(band, amount):
    band = band.replace(",", "").replace("%", "").strip()
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
    note = row["Notes"]

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

    results.append([row["Lender"], row["Advance Band"], rate, comm, apr, note])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)", "APR", "Notes"])

if calc_df.empty:
    st.warning("No lenders available for this combination.")
else:
    if product_choice == "PCP":
        zopa = calc_df[calc_df["Lender"].str.contains("ZOPA")]
        others = calc_df[~calc_df["Lender"].str.contains("ZOPA")]
        calc_df = pd.concat([zopa, others])

    best_comm = calc_df.loc[calc_df["Commission (£)"].idxmax()]
    lowest_apr = calc_df.loc[calc_df["APR"].apply(lambda x: float(str(x).split('-')[0]) if isinstance(x, str) else x).idxmin()]
    lender_count = calc_df["Lender"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='stat-card best'>Best Commission<br><span style='font-size:28px;'>£{best_comm['Commission (£)']:.0f}</span><br><span class='label'>{best_comm['Lender']} ({product_choice})</span></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='stat-card apr'>Lowest APR<br><span style='font-size:28px;'>{lowest_apr['APR']}</span><br><span class='label'>{lowest_apr['Lender']}</span></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='stat-card count'>Available Lenders<br><span style='font-size:28px;'>{lender_count}</span><br><span class='label'>For £{deal_amount:,.0f}</span></div>", unsafe_allow_html=True)

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
