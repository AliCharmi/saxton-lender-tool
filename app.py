import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Saxton4x4 Lender Commission Tool", layout="wide")

# --- DATA ---
data = {
    "Lender": ["Santander", "Santander", "Santander", "Santander",
               "ZOPA", "ZOPA", "ZOPA",
               "Mann Island",
               "Motion Finance - Alphera", "Motion Finance - BNP", "Motion Finance - CAAF", "Motion Finance - Close",
               "Moto Novo", "Oodle & Blue Rate for risk", "ZOPA T3-T6 Rate for risk",
               "Startline Low", "Startline High",
               "Oodle 9.1", "Oodle 10.35", "Oodle 11.35", "Oodle 12.35", "Oodle 13.35", "Oodle 14.85",
               "Blue", 
               "Marsh Low", "Marsh High",
               "JBR"],
    "Advance Band": ["0-24,999", "25,000-39,999", "40,000-49,999", "50,000+",
                     "0-24,999", "25,000-39,999", "40,000-49,999",
                     "2,500-40,000+",
                     "All", "All", "All", "All",
                     "All", "All", "All",
                     "16.9%", "19.9%",
                     "9.1", "10.35", "11.35", "12.35", "13.35", "14.85",
                     "12.9-19.9",
                     "0-30,000", "0-30,000",
                     "0-500,000"],
    "APR": [12.9, 11.9, 10.9, 9.9,
            12.9, 11.9, 10.9,
            10.9,
            10.9, 10.4, 10.9, 10.9,
            11.9, "Rate for risk", "Rate for risk",
            16.9, 19.9,
            9.1, 10.35, 11.35, 12.35, 13.35, 14.85,
            "12.9-19.9",
            "14.4-23.9", 26.9,
            10.9],
    "Commission %": ["9.05", "6.8", "5.15", "4",
                     "HP:9.15 PCP:11.15", "HP:7.15 PCP:9.15", "HP:5.15 PCP:7.15",
                     "6.75",
                     "3.5", "3.5", "3.5", "3.5",
                     "2", "3", "2",
                     "5", "5",
                     "7", "10", "10", "10", "10", "9",
                     "8",
                     "8", "5",
                     "5"],
    "Commission Cap": [None, None, None, None,
                       3000, 3000, 3000,
                       3000,
                       None, None, None, None,
                       None, None, None,
                       2000, 1500,
                       2500, 2500, 2500, 2500, 2500, 2500,
                       2000,
                       1500, 1500,
                       None]
}

df = pd.DataFrame(data)

# --- SIDEBAR ---
st.sidebar.header("Commission Calculator")
deal_amount = st.sidebar.number_input("Enter Deal Amount (£):", min_value=0, max_value=500000, value=25000, step=500)

# --- TAB NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["Lender Comparison", "Commission Calculator", "Best Lender"])

# --- TAB 1: Lender Comparison ---
with tab1:
    st.title("Lender Comparison")
    st.dataframe(df, use_container_width=True)

# --- TAB 2: Commission Calculator ---
with tab2:
    st.title("Commission Calculator")
    results = []
    for _, row in df.iterrows():
        comm_str = row['Commission %']
        cap = float(row['Commission Cap']) if row['Commission Cap'] else None
        if "HP:" in comm_str:
            hp_rate = float(comm_str.split("HP:")[1].split("PCP")[0].strip())
            pcp_rate = float(comm_str.split("PCP:")[1].strip())
            hp_comm = min((hp_rate / 100) * deal_amount, cap if cap else (hp_rate / 100) * deal_amount)
            pcp_comm = min((pcp_rate / 100) * deal_amount, cap if cap else (pcp_rate / 100) * deal_amount)
            results.append([row['Lender'], row['Advance Band'], "HP", hp_comm])
            results.append([row['Lender'], row['Advance Band'], "PCP", pcp_comm])
        else:
            try:
                rate = float(comm_str)
            except:
                rate = 0
            comm = min((rate / 100) * deal_amount, cap if cap else (rate / 100) * deal_amount)
            results.append([row['Lender'], row['Advance Band'], "All", comm])

    calc_df = pd.DataFrame(results, columns=["Lender", "Advance Band", "Product", "Commission (£)"])
    st.dataframe(calc_df, use_container_width=True)
    st.download_button("Download as CSV", calc_df.to_csv(index=False).encode(), "commissions.csv")

# --- TAB 3: Best Lender ---
with tab3:
    st.title("Best Lender Recommendation")
    ranked = calc_df.groupby("Lender")["Commission (£)"].max().sort_values(ascending=False).reset_index()
    st.write("### Lenders Ranked by Highest Possible Commission")
    st.dataframe(ranked, use_container_width=True)
    fig = px.bar(ranked, x="Lender", y="Commission (£)", title="Commission by Lender", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)
