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

    ["Mann Island","2500-40000+","HP,PCP",10.9,7.2,3000,True],

    ["Startline Low","0-16900","HP,PCP",16.9,5,2000,True],
    ["Startline High","0-19900","HP,PCP",19.9,5,1500,True],

    ["Marsh Low","0-30000","HP,PCP","14.4-23.9",0,1500,True],
    ["Marsh High","0-30000","HP,PCP",26.9,0,1500,True],

    ["JBR","0-500000","HP,LP",10.9,5.5,None,True],

    ["Tandem","0-60000","HP","10.9-19.9",7,2000,True],
    ["Admiral","0-60000","HP,PCP","9.9-25.0",7.5,2500,True],

    ["Close Brothers", "0-24999", "HP,PCP", 12.9, 7, 3000, True],
    ["Close Brothers", "25000-39999", "HP,PCP", 11.9, 5.5, 3000, True],
    ["Close Brothers", "40000-49999", "HP,PCP", 10.9, 4, 3000, True],
    ["Close Brothers", "50000-200000", "HP,PCP", 9.9, 3, 3000, True],
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

    ["Ayan (Halal)","2000-45000","HP","7.9-22.0",7,3000,False],
]

data.extend(motion)
df = pd.DataFrame(data, columns=["Lender","Advance Band","Products","APR","Commission %","Cap","Favourite"])

# --- INPUTS ---
st.markdown("<div class='input-card'>", unsafe_allow_html=True)
c1,c2,c3,c4,c5 = st.columns(5)
deal_amount = c1.number_input("Advance Amount (£)",0,500000,30000,500)
product_choice = c2.selectbox("Product",["PCP","HP","LP","Loan"])
sort_by = c3.selectbox("Sort By",["Highest Commission","Lowest APR"])
term = c4.selectbox("Term (months)",[24,36,48,60])
halal_mode = c5.checkbox("Halal Finance (Ayan Only)")
st.markdown("</div>", unsafe_allow_html=True)

# --- AYAN NOTES ---
if halal_mode:
    st.warning("""
### CUSTOMER EXPLANATION

This is a halal finance option where you rent the car instead of paying interest, and you own it at the end with no large final payment.

- Not a loan  
- No interest  
- Monthly rental payments  
- Ownership builds over time  
- No balloon payment  
- Can settle early with no penalty  

---

### INTERNAL RULES FOR BMS

Only use when:
- Customer asks for halal finance  

Do not:
- Compare on APR  
- Say it is cheaper  
- Say it is the same as HP or PCP  
- Push for commission  

---

### COMMISSION AND DEBIT BACK

7% commission  
Cap £3,000  

Debit back:
- 100% months 1–3  
- 75% months 4–6  
- 50% months 7–12  
- 0% after 12 months  

Customer has no early settlement penalty  
Dealer has full clawback exposure  
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
    product_choice = "HP"
    app = app[app["Lender"].str.contains("Ayan")]

# --- CALC ---
results=[]
for _,r in app.iterrows():
    rate = r["Commission %"]
    try: rate=float(rate)
    except: rate=0

    comm=(rate/100)*deal_amount

    if r["Lender"]=="Admiral":
        if term<36: continue
        interest=(rate/100)*deal_amount*(term/12)
        comm=min(comm,interest*0.5)

    if r["Cap"]:
        comm=min(comm,r["Cap"])

    pct=(comm/deal_amount)*100
    results.append([r["Lender"],rate,comm,pct,r["APR"]])

calc=pd.DataFrame(results,columns=["Lender","Rate %","Commission","Comm % of Deal","APR"])
calc=calc.sort_values("Commission",ascending=False)

# --- TOP ---
st.subheader("Top Lenders")
if not halal_mode:
    for i,row in calc.head(3).iterrows():
        st.write(f"{i+1}. {row['Lender']} — £{row['Commission']:.0f}")
else:
    if not calc.empty:
        ayan = calc.iloc[0]
        st.write(f"Ayan — £{ayan['Commission']:.0f}")

# --- ORIGINAL NOTES ---
if not halal_mode:
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

# --- TABLE ---
st.subheader("Detailed Lender Data")
st.dataframe(calc,use_container_width=True)

fig=px.bar(calc,x="Lender",y="Commission",color="Commission")
st.plotly_chart(fig,use_container_width=True)
