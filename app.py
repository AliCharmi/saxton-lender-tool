import pandas as pd
import streamlit as st
import plotly.express as px
import re

st.set_page_config(page_title="Saxtons Lender Commission Tool", page_icon="💰", layout="wide")

# --- STYLE ---
st.markdown("""
<style>
.stApp {background:#f8f9fa;font-family:Arial;}
h1 {color:#1e3d59;text-align:center;}
.input-card {background:#fff;padding:20px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,0.1);}
.stat-card {padding:20px;border-radius:10px;font-size:18px;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.1);}
.best {background:#e8f9f0;}
.apr {background:#e8f1fb;}
.count {background:#f5e8fb;}
.warn {background:#fdecea;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>Saxtons Lender Commission Tool</h1>", unsafe_allow_html=True)

# --- DATA ---
data = [
    ["Santander","0-24999","HP,LP,PCP",12.9,9.05,None],
    ["Santander","25000-39999","HP,LP,PCP",11.9,6.8,None],
    ["Santander","40000-49999","HP,LP,PCP",10.9,5.15,None],
    ["Santander","50000+","HP,LP,PCP",9.9,4,None],

    ["ZOPA","0-24999","HP,PCP",12.9,"HP:9.15 PCP:11.15",3000],
    ["ZOPA","25000-32999","HP,PCP",11.9,"HP:7.15 PCP:9.15",3000],
    ["ZOPA","33000-50000","HP,PCP",10.9,"HP:5.15 PCP:7.15",3000],

    ["Mann Island","2500-40000+","HP,PCP",10.9,7.2,3000],

    ["Startline Low","0-16900","HP,PCP",16.9,5,2000],
    ["Startline High","0-19900","HP,PCP",19.9,5,1500],

    ["Marsh Low","0-30000","HP,PCP","14.4-23.9",0,1500],
    ["Marsh High","0-30000","HP,PCP",26.9,0,1500],

    ["JBR","0-500000","HP,LP",10.9,5.5,None],

    ["Tandem","0-60000","HP","10.9-19.9",7,2000],
    ["Admiral","0-60000","HP,PCP","9.9-25.0",7.5,2500],

    ["Close Brothers","0-24999","HP,PCP",12.9,7,3000],
    ["Close Brothers","25000-39999","HP,PCP",11.9,5.5,3000],
    ["Close Brothers","40000-49999","HP,PCP",10.9,4,3000],
    ["Close Brothers","50000-200000","HP,PCP",9.9,3,3000],

    ["Ayan (Halal)","2000-45000","HP","7.9-22.0",7,3000],
]

df = pd.DataFrame(data, columns=["Lender","Advance Band","Products","APR","Commission %","Cap"])

# --- INPUTS ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
c1,c2,c3,c4,c5 = st.columns(5)

deal_amount = c1.number_input("Advance (£)",0,500000,30000,500)
product_choice = c2.selectbox("Product",["PCP","HP","LP","Loan"])
sort_by = c3.selectbox("Sort By",["Highest Commission","Lowest APR"])
term = c4.selectbox("Term",[24,36,48,60])
halal_mode = c5.checkbox("Halal Finance")

st.markdown("</div>", unsafe_allow_html=True)

# --- AYAN FULL TRAINING ---
if halal_mode:
    st.warning("""
### 🕌 HALAL FINANCE – AYAN

One line:
Rent instead of interest. You own it at the end. No balloon.

Steps:
1. Not a loan, no interest  
2. Customer pays rental  
3. Owns car at end  

Customer:
No balloon  
No penalty to settle early  

Rules:
Only use if asked  
Do not compare on APR  
Do not push for commission  

Commission:
7%  
Debit back:
100% 1–3m  
75% 4–6m  
50% 7–12m  
0% after  

Customer no penalty  
Dealer full clawback
""")

# --- FILTER ---
def band_ok(band, amt):
    band = band.replace(",","")
    if "All" in band: return True
    if "+" in band: return amt >= int(re.findall(r"\d+",band)[0])
    low,high = re.findall(r"\d+",band)
    return int(low)<=amt<=int(high)

app = df[df["Products"].str.contains(product_choice,na=False)]
app = app[app["Advance Band"].apply(lambda x: band_ok(x,deal_amount))]

if halal_mode:
    product_choice="HP"
    app = app[app["Lender"].str.contains("Ayan")]

# --- CALC ---
rows=[]
for _,r in app.iterrows():

    rate=r["Commission %"]

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

    if r["Cap"]:
        comm=min(comm,r["Cap"])

    rows.append([r["Lender"],rate,comm,r["APR"]])

calc=pd.DataFrame(rows,columns=["Lender","Rate","Commission","APR"])

# --- SORT ---
def apr_val(x):
    try: return float(str(x).split('-')[0])
    except: return 999

if sort_by=="Lowest APR":
    calc["APR_val"]=calc["APR"].apply(apr_val)
    calc=calc.sort_values("APR_val")
else:
    calc=calc.sort_values("Commission",ascending=False)

# --- EXTRA PROFIT ---
base = calc[calc["Lender"].str.contains("Santander")]["Commission"].max() if not calc.empty else 0
calc["Extra vs Santander"] = calc["Commission"] - base

# --- MISSED PROFIT ---
best_comm = calc["Commission"].max() if not calc.empty else 0
calc["Missed Profit"] = best_comm - calc["Commission"]

# --- BADGES ---
calc["Tier"]="🟡 Backup"

if not calc.empty:
    calc.loc[calc["Commission"].idxmax(),"Tier"]="🥇 Best Profit"
    calc.loc[calc.head(3).index,"Tier"]="🥈 Strong Option"
    calc.loc[calc["Lender"].str.contains("Ayan"),"Tier"]="🕌 Halal"
    calc.loc[calc["Lender"].str.contains("Go Car|ABOUND"),"Tier"]="🔴 Risk"

# --- WHY + RISK ---
calc["Why"] = calc["Lender"].apply(lambda x:
    "High profit" if "Santander" in x else
    "Strong PCP" if "ZOPA" in x else
    "High value deals" if "JBR" in x else
    "Halal only" if "Ayan" in x else
    ""
)

calc["Risk"] = calc["Lender"].apply(lambda x:
    "High clawback" if "Ayan" in x else
    "Medium" if "Admiral" in x else
    "Low"
)

# --- TOP ---
st.subheader("Top Lenders")

if not halal_mode:
    for i,row in calc.head(3).iterrows():
        st.write(f"{i+1}. {row['Lender']} — £{row['Commission']:.0f} — {row['Tier']}")
else:
    if not calc.empty:
        r=calc.iloc[0]
        st.write(f"{r['Tier']} — £{r['Commission']:.0f}")

# --- CARDS ---
if not calc.empty:
    best=calc.iloc[0]
    low=calc.iloc[calc["APR"].apply(apr_val).idxmin()]
    c1,c2,c3=st.columns(3)
    c1.markdown(f"<div class='stat-card best'>Best Commission<br>£{best['Commission']:.0f}</div>",unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-card apr'>Lowest APR<br>{low['APR']}</div>",unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-card count'>Lenders<br>{calc['Lender'].nunique()}</div>",unsafe_allow_html=True)

# --- NOTES ---
if not halal_mode:
    st.info("""
### ZOPA PCP
Zopa PCP is prioritised. Often better balloons than Santander.  
If declined, message Taylor

### ADMIRAL
36+ months only  
Capped at £2,500  

### JBR
Strong £40k+  
10% deposit  

### STARTLINE
Under £20k  

### CONTROL
Go Car / Abound approval needed
""")

# --- TABLE ---
st.subheader("Detailed Data")

st.dataframe(
    calc[["Lender","Commission","APR","Extra vs Santander","Missed Profit","Tier","Why","Risk"]]
    .style.highlight_max(subset=["Commission"], color="lightgreen"),
    use_container_width=True
)

fig=px.bar(calc,x="Lender",y="Commission")
st.plotly_chart(fig,use_container_width=True)
