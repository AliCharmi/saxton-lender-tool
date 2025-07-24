import pandas as pd
import streamlit as st
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Saxton4x4 Lender Commission Tool", layout="wide")

# --- DATASET ---
data = {
    "Lender": ["Santander", "Santander", "Santander", "Santander",
               "ZOPA", "ZOPA", "ZOPA",
               "Mann Island",
               "Motion Finance - Alphera", "Motion Finance - BNP", "Motion Finance - CAAF", "Motion Finance - Close",
               "Moto Novo", "Oodle", "Blue", "Startline Low", "Startline High",
               "Marsh Low", "Marsh High",
               "JBR"],
    "Advance Band": ["0-24,999", "25,000-39,999", "40,000-49,999", "50,000+",
                     "0-24,999", "25,000-39,999", "40,000-49,999",
                     "2,500-40,000+",
                     "All", "All", "All", "All",
                     "All", "All", "12.9-19.9",
                     "16.9%", "19.9%",
                     "0-30,000", "0-30,000",
                     "0-500,000"],
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
    "Favorite": [True, True, True, True,
                 True, True, True,
                 True,
                 True, True, True, True,
                 True, False, False,
                 False, False,
                 True, True,
                 True]
}

df = pd.DataFrame(data)

# --- TOP INPUTS (MOBILE-FRIENDLY) ---
st.title("Saxton4x4 Lender Commission Tool")
col1, col2, col3 = st.columns([1,1,1])
with col1:
    product_choice = st.selectbox("Product", ["PCP", "HP", "LP"])
with col2:
    deal_amount = st.number_input("Deal Amount (£):", min_value=0, max_value=500000, value=25000, step=500)
with col3:
    show_least_fav = st.checkbox("Include least-favorite lenders", value=False)

# Filter lenders by product
df = df[df["Products"].str.contains(product_choice)]
if not show_least_fav:
    df = df[df["Favorite"] == True]

# --- CALCULATE COMMISSIONS ---
results = []
for _, row in df.iterrows():
    comm_str = row['Commission %']
    cap = float(row['Commission Cap']) if row['Commission Cap'] else None
    if "HP:" in comm_str and product_choice in ["HP","PCP"]:
        rate = float(comm_str.split(f"{product_choice}:")[1].split()[0])
        comm = (rate / 100) * deal_amount
        if cap: comm = min(comm, cap)
        results.append([row['Lender'], row['Advance Band'], rate, comm])
    else:
        try:
            rate = float(comm_str)
        except:
            rate = 0
        comm = (rate / 100) * deal_amount
        if cap: comm = min(comm, cap)
        results.append([row['Lender'], row['Advance Band'], rate, comm])

calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Commission %", "Commission (£)"])
ranked = calc_df.groupby("Lender")["Commission (£)"].max().sort_values(ascending=False).reset_index()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["Lender Comparison", "Commission Calculator", "Best Lender"])

with tab1:
    st.subheader("Lender Comparison")
    st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("Commission Calculator")
    st.dataframe(calc_df.sort_values(by="Commission (£)", ascending=False), use_container_width=True)
    st.download_button("Download as CSV", calc_df.to_csv(index=False).encode(), "commissions.csv")

with tab3:
    st.subheader("Best Lender Recommendation")
    st.write("### Top 3 Lenders by Commission")
    top3 = ranked.head(3)
    top3['Rank'] = ["🥇 1st","🥈 2nd","🥉 3rd"]
    st.dataframe(top3, use_container_width=True)
    if product_choice == "PCP":
        st.info("Zopa PCP is prioritized — review this first for potential better balloons than Santander.")
    fig = px.bar(ranked, x="Lender", y="Commission (£)", title="Commission by Lender", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)
