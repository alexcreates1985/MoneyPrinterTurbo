"""Operating desk alongside, not a replacement for, Travel Factory."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import json
import streamlit as st
from app.services.travel_business import load, forecast, quote_issues

st.set_page_config(page_title='TravelDecoded Business',page_icon='🌏',layout='wide')
st.title('Alex TravelDecoded')
st.caption('Operating desk • proposed launch 25 November 2026 • preparation only')
state=load('status')
tab=st.tabs(['Overview','Prices','Calendar','Affiliates','Forecast','Products','Competitors'])
with tab[0]:
    st.info('No social, affiliate or checkout reporting connected. Actual revenue and clicks are unavailable.')
    st.write('39 proposed videos · 13 weeks · three platforms · approval required for each publication')
    st.write(state['automation'])
    for b in state['blockers']: st.warning(b)
    st.markdown('[Open existing video production dashboard](/Travel_Factory)')
    for f,label,mime in [('bangkok.html','Download Bangkok page','text/html'),('dashboard.html','Download portable operating dashboard','text/html')]:
        p=ROOT/'docs/travel/business'/f
        if p.exists():st.download_button(label,p.read_bytes(),f,mime)
with tab[1]:
    ledger=load('ledger'); st.subheader('Dated price observations')
    st.write(ledger['scope']); st.dataframe(ledger['prices'],hide_index=True)
    st.subheader('Exchange quote exclusions')
    for q in ledger['quotes']:
        st.write(q)
        for issue in quote_issues(q):st.error(issue)
    st.download_button('Export source ledger JSON',json.dumps(ledger,indent=2),'traveldecoded-ledger.json','application/json')
    st.caption('Source observations are immutable snapshots. Proposed changes should be saved as new records; an AI check does not set human approval.')
with tab[2]:
    cal=load('calendar'); st.dataframe(cal,hide_index=True)
    st.download_button('Export 39-slot calendar',json.dumps(cal,indent=2),'traveldecoded-calendar.json','application/json')
with tab[3]:
    st.write('No approved accounts or tracking URLs. Programme signup URLs are not affiliate links.')
    st.dataframe(load('affiliates'),hide_index=True)
with tab[4]:
    st.subheader('Editable hypotheses, not earnings predictions')
    scenario=st.selectbox('Scenario',['Conservative','Base','Upside'])
    presets={'Conservative':(400,.004,.005,.15,.015,.65),'Base':(2000,.008,.01,.2,.02,.75),'Upside':(8000,.015,.02,.25,.03,.8)}
    v,vs,ss,sa,cb,c=presets[scenario]
    defs=dict(videos_month=13,views_video=v,view_site=vs,site_sale=ss,site_affiliate=sa,click_booking=cb,completion=c,
        commission=8,guide_price=19,refund_rate=.05,payment_pct=.06,payment_fixed=.5,
        b2b_month=1 if scenario=='Upside' else 0,b2b_price=450,b2b_cost=150,software_month=0,compliance_month=0,
        guide_paid_share=.9,affiliate_paid_share=.25,b2b_paid_share=.5)
    st.caption('Views per original video combine the three platforms. Fee and settlement assumptions are placeholders, not verified Whop terms. Labour and income tax excluded; add them before a commercial decision.')
    inputs={}
    with st.expander('Edit assumptions',expanded=True):
        for key,value in defs.items():
            inputs[key]=st.number_input(key.replace('_',' '),min_value=0.0,value=float(value),key=scenario+key,
                max_value=1.0 if key in ['view_site','site_sale','site_affiliate','click_booking','completion','refund_rate','payment_pct','guide_paid_share','affiliate_paid_share','b2b_paid_share'] else None)
    rows=[dict(period=label,**forecast(inputs,m)) for label,m in [('30 days',1),('90 days',3),('6 months',6),('12 months',12)]]
    st.dataframe(rows,hide_index=True)
    st.download_button('Export forecast and assumptions',json.dumps(dict(scenario=scenario,assumptions=inputs,results=rows),indent=2),'traveldecoded-forecast.json','application/json')
with tab[5]:
    st.dataframe(load('products'),hide_index=True)
    st.caption('Checkout is not enabled. No customer data is collected by this desk.')
with tab[6]:
    st.caption('20 public businesses identified. Website observations only; video pacing, engagement and private revenue are not inferred.')
    st.dataframe(load('competitors'),hide_index=True)
