import pandas as pd
import streamlit as st
import plotly.express as px
import re

st.set_page_config(page_title="Saxtons Lender Commission Tool", page_icon="💰", layout="wide")

st.markdown("""
<style>
.stApp {background:#f8f9fa;font-family:Arial;}
h1 {color:#1e3d59;text-align:center;}
.input-card {background:#fff;padding:20px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,0.1);}
.stat-card {padding:20px;border-radius:10px;font-size:20px;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.1);}
.best {background:#e8f9f0;} .apr {background:#e8f1fb;} .count {background:#f5e8fb;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- LENDER DATA ---
data = [
    ["Santander","0-24999","HP,LP,PCP",12.9,9.05,None,True],
    ["Santander","25000-39999","HP,LP,PCP",11.9,6.8,None,True],
    ["Santander","40000-49999","HP,LP,PCP",10.9,5.15,None,True],
    ["Santander","50000+","HP,LP,PCP",9.9,4,None,True],

    ["ZOPA","0-24999","HP,PCP",12.9,"HP:9.15 PCP:11.15",3000,True],
    ["ZOPA","25000-32999","HP,PCP",11.9,"HP:7.15 PCP:9.15",3000,True],
    ["ZOPA","33000-50000","HP,PCP",10.9,"HP:5.15 PCP:7.15",3000,True],

    ["Mann Island","2500-40000+","HP,PCP",9.9,6.5,3000,True],

    ["Startline Low","0-16900","HP,PCP",16.9,5,2000,True],
    ["Startline High","0-19900","HP,PCP",19.9,5,1500,True],

    ["Marsh Low","0-30000","HP,PCP","14.4-23.9",0,1500,True],
    ["Marsh High","0-30000","HP,PCP",26.9,0,1500,True],

    ["JBR","0-500000","HP,LP",10.9,5.5,None,True],

    ["Tandem","0-60000","HP","10.9-19.9",7,2000,True],
    ["Admiral","0-60000","HP,PCP","9.9-25.0",7.5,2500,True],
]

motion = [
    ["Alphera (Motion)","All","HP,PCP",10.9,4.5,3000,False],
    ["BNP (Motion)","All","HP,PCP",9.9,4.5,3000,False],
    ["CAAF (Motion)","All","HP,PCP",10.9,4.5,3000,False],
    ["Close (Motion)","All","HP,PCP",10.9,3.5,3000,False],
    ["Moto Novo (Motion)","All","HP,PCP",11.9,4.5,3000,False],
    ["Oodle & Blue (Motion)","All","HP","Rate for risk",3,3000,False],
    ["Go Car Credit (Motion)","All","HP","Rate for risk",0.5,None,False],
    ["ABOUND (Personal Loan)","All","Loan","N/A","No commission",None,False],
]

data.extend(motion)
df = pd.DataFrame(data, columns=["Lender","Advance Band","Products","APR","Commission %","Cap","Favourite"])

# --- INPUTS ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
c1,c2,c3,c4 = st.columns(4)
deal_amount = c1.number_input("Advance Amount (£)",0,500000,30000,500)
product_choice = c2.selectbox("Product",["PCP","HP","LP","Loan"])
sort_by = c3.selectbox("Sort By",["Highest Commission","Lowest APR"])
term = c4.selectbox("Term (months)",[24,36,48,60])
st.markdown("</div>", unsafe_allow_html=True)

# --- FILTER ---
def band_ok(band, amt):
    band = band.replace(",","")
    if "All" in band: return True
    if "+" in band: return amt >= int(re.findall(r"\d+",band)[0])
    low,high = re.findall(r"\d+",band)
    return int(low)<=amt<=int(high)

app = df[df["Products"].str.contains(product_choice,na=False)]
app = app[app["Advance Band"].apply(lambda x: band_ok(x,deal_amount))]

# --- CALC ---
results=[]
for _,r in app.iterrows():
    rate = r["Commission %"]
    if isinstance(rate,str) and f"{product_choice}:" in rate:
        rate=float(rate.split(f"{product_choice}:")[1].split()[0])
    else:
        try: rate=float(rate)
        except: rate=0

    comm=(rate/100)*deal_amount
    if r["Lender"]=="Admiral":
        if term<36: continue
        interest=(rate/100)*deal_amount*(term/12)
        comm=min(comm,interest*0.5)

    if r["Cap"]: comm=min(comm,r["Cap"])
    pct=(comm/deal_amount)*100
    results.append([r["Lender"],rate,comm,pct,r["APR"]])

calc=pd.DataFrame(results,columns=["Lender","Rate %","Commission","Comm % of Deal","APR"])
calc=calc.sort_values("Commission",ascending=False)

def safe_apr(x):
    try: return float(str(x).split('-')[0])
    except: return 999

# --- EXTRA PROFIT ---
sant=calc[calc["Lender"].str.contains("Santander")]
base=sant["Commission"].max() if not sant.empty else 0
calc["Extra vs Santander"]=calc["Commission"]-base

# --- TIERS ---
calc["Tier"]="🟡 Backup"
calc.loc[calc["Commission"].idxmax(),"Tier"]="🥇 Best Profit"
calc.loc[calc.head(3).index,"Tier"]="🥈 Strong Option"
calc.loc[calc["Lender"].str.contains("Go Car Credit|ABOUND"),"Tier"]="⚠️ Low Priority"

# --- TOP 3 ---
st.subheader("Top 3 Lenders For This Deal")
for i,row in calc.head(3).iterrows():
    st.write(f"{i+1}. {row['Lender']} — £{row['Commission']:.0f}")

# --- CARDS ---
best=calc.iloc[0]
low=calc.iloc[calc["APR"].apply(safe_apr).idxmin()]
c1,c2,c3=st.columns(3)
c1.markdown(f"<div class='stat-card best'>Best Commission<br>£{best['Commission']:.0f}</div>",unsafe_allow_html=True)
c2.markdown(f"<div class='stat-card apr'>Lowest APR<br>{low['APR']}</div>",unsafe_allow_html=True)
c3.markdown(f"<div class='stat-card count'>Lenders<br>{calc['Lender'].nunique()}</div>",unsafe_allow_html=True)

# --- OPERATIONAL NOTES ---
st.info("""
### ZOPA PCP
Zopa PCP is prioritised. Often better balloons than Santander.  
If declined, message Taylor — she may overturn it.

### ADMIRAL
Commission only applies to terms ≥ 36 months.  
Capped at £2,500 or 50% of interest.

### JBR
Strong on £40k+ HP.  
10% minimum deposit required including products.

### STARTLINE
Use for lower advances under £20k.

### MOTION FINANCE
Multiple sub-lenders — compare offers carefully.

### ⚠️ MANAGEMENT CONTROL
ABOUND → Negative equity only. No commission.  
Go Car Credit → Speak to Luke or Ali before payout.
""")

st.subheader("Detailed Lender Data")
st.dataframe(calc,use_container_width=True)

fig=px.bar(calc,x="Lender",y="Commission",color="Commission")
st.plotly_chart(fig,use_container_width=True)
