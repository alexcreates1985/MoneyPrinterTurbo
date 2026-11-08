from datetime import date
import pytest
from app.services.travel_business import quote_issues, convert_budget, forecast, load

def test_minimum_and_unknown_fee_block_conversion():
    q=load('ledger')['quotes'][0]
    assert 'Minimum exchange exceeds this budget' in quote_issues(q,on=date(2026,11,8))
    assert 'Missing fee_sgd' in quote_issues(q,on=date(2026,11,8))
    with pytest.raises(ValueError): convert_budget(q,on=date(2026,11,8))

def test_no_missing_actuals_become_zero():
    assert all(x is None for x in load('status')['actuals'].values())

def test_calendar_timezone_unique_39():
    cal=load('calendar')
    assert len(cal)==39
    assert len({x['publish_at'] for x in cal})==39
    assert all(x['publish_at'].endswith('+08:00') and not x['published'] for x in cal)
    assert cal[0]['publish_at']=='2026-11-25T19:30:00+08:00'

def test_unapproved_affiliate_links_never_seeded():
    assert all(x['tracking_url'] is None for x in load('affiliates'))

def test_financial_cash_is_not_earned():
    a=dict(videos_month=10,views_video=1000,view_site=.01,site_sale=.1,site_affiliate=.2,
        click_booking=.1,completion=.5,commission=8,guide_price=19,refund_rate=.05,
        payment_pct=.06,payment_fixed=.5,b2b_month=0,b2b_price=450,b2b_cost=150,
        software_month=0,compliance_month=0,guide_paid_share=.9,affiliate_paid_share=.25,b2b_paid_share=.5)
    r=forecast(a)
    assert r['guide_sales']==10
    assert r['affiliate_earned']==8 and r['affiliate_paid']==2
    assert r['cash_received']==pytest.approx(164.45)
    assert r['contribution']==pytest.approx(172.1)
    assert forecast(a,3)['contribution']==pytest.approx(3*r['contribution'])
