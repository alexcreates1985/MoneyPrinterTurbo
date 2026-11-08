"""TravelDecoded operating records. No network access or publishing side effects."""
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'docs/travel/business'

def load(name):
    if name not in {'ledger', 'calendar', 'affiliates', 'products', 'status', 'competitors'}:
        raise ValueError('Unknown register')
    return json.loads((ROOT / f'{name}.json').read_text())

def quote_issues(quote, budget=50, on=None):
    """Unknown is not zero; a minimum cannot be evaded by scaling a quote."""
    on = on or date.today()
    issues = []
    for key in ('provider', 'source_url', 'quoted_at', 'direction', 'local_per_sgd', 'fee_sgd', 'minimum_sgd'):
        if quote.get(key) is None or quote.get(key) == '':
            issues.append(f'Missing {key}')
    if quote.get('direction') != 'SGD_to_THB':
        issues.append('Wrong or unconfirmed exchange direction')
    if quote.get('minimum_sgd') is not None and Decimal(str(quote['minimum_sgd'])) > Decimal(str(budget)):
        issues.append('Minimum exchange exceeds this budget')
    if quote.get('quoted_at'):
        try:
            quoted = datetime.fromisoformat(quote['quoted_at'])
            if quoted.tzinfo is None:
                issues.append('Quote timezone missing')
            if not 0 <= (on - quoted.date()).days <= 7:
                issues.append('Quote date is stale or in the future')
        except ValueError:
            issues.append('Invalid quote timestamp')
    rate = quote.get('local_per_sgd')
    if rate is not None and (not Decimal(str(rate)).is_finite() or Decimal(str(rate)) <= 0):
        issues.append('Invalid rate')
    fee = quote.get('fee_sgd')
    if fee is not None and (not Decimal(str(fee)).is_finite() or not 0 <= Decimal(str(fee)) < Decimal(str(budget))):
        issues.append('Invalid fee')
    if quote.get('verification_status') != 'verified':
        issues.append('Quote not verified for this budget')
    return issues

def convert_budget(quote, budget=50, on=None):
    issues = quote_issues(quote, budget, on)
    if issues:
        raise ValueError('; '.join(issues))
    return (Decimal(str(budget)) - Decimal(str(quote['fee_sgd']))) * Decimal(str(quote['local_per_sgd']))

def forecast(a, months=1):
    """Monthly steady-state hypotheses, cumulative periods; not growth benchmarks."""
    views = a['videos_month'] * a['views_video'] * months
    visits = views * a['view_site']
    sales = visits * a['site_sale']
    clicks = visits * a['site_affiliate']
    bookings = clicks * a['click_booking']
    completed = bookings * a['completion']
    affiliate = completed * a['commission']
    guide_gross = sales * a['guide_price']
    refunds = guide_gross * a['refund_rate']
    fees = guide_gross * a['payment_pct'] + sales * a['payment_fixed']
    b2b = a['b2b_month'] * months * a['b2b_price']
    costs = months * (a['software_month'] + a['compliance_month'] + a['b2b_month'] * a['b2b_cost'])
    earned = guide_gross - refunds + affiliate + b2b
    cash = (guide_gross-refunds)*a['guide_paid_share'] + affiliate*a['affiliate_paid_share'] + b2b*a['b2b_paid_share']
    return dict(views=views, visits=visits, guide_sales=sales, affiliate_clicks=clicks, bookings=bookings,
                completed_bookings=completed, affiliate_earned=affiliate, affiliate_paid=affiliate*a['affiliate_paid_share'],
                guide_gross=guide_gross, refunds=refunds, b2b_gross=b2b, fees=fees, operating_costs=costs,
                earned_revenue=earned, contribution=earned-fees-costs, cash_received=cash,
                net_cash=cash-fees-costs, platform_revenue=0)
