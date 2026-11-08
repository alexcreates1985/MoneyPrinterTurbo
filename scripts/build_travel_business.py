"""Rebuild initial registers from the audited prior plan; never run on edited records."""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1] / 'docs/travel/business'
def save(name, data):
    path = ROOT / (name+'.json')
    if path.exists():
        raise FileExistsError(f'Preserving existing register: {path}')
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

prior = json.loads((ROOT/'prior-plan-audit.json').read_text())
prices=[]
def price(id, city, item, provider, amount, currency, eligibility, url, notes):
    prices.append(dict(id=id,country='Singapore' if city=='Singapore' else 'Thailand',city=city,
        item=item,provider=provider,quantity=1,unit='adult admission' if 'admission' in item.lower() else 'one-day pass',
        local_price=amount,currency=currency,tax_and_fees='Published ticket price; optional extras excluded',
        eligibility=eligibility,source_url=url,checked_at='2026-11-08',exchange_rate_id=None,
        sgd_equivalent=amount if currency=='SGD' else None,verification_status='official_published_price',
        human_approved=False,notes=notes))
gallery='https://www.nationalgallery.sg/sg/en/visit/visitor-information.html'
price('SG-GALLERY-LOCAL','Singapore','General admission','National Gallery Singapore',0,'SGD','Singapore citizens and PRs',gallery,'Selected exhibitions only. Not all-access. Free does not mean unlimited purchasable tickets.')
price('SG-GALLERY-STANDARD','Singapore','General admission','National Gallery Singapore',20,'SGD','Other nationalities, standard adult',gallery,'Not a like-for-like equivalent of the Grand Palace.')
price('TH-PALACE','Bangkok','Grand Palace admission','Bureau of the Royal Household',500,'THB','Foreign visitor','https://www.royalgrandpalace.th/en/visit/practical-information','Includes Wat Phra Kaew and Queen Sirikit Museum of Textiles. Dress rules and closures must be checked for travel date.')
price('SG-STP','Singapore','Singapore Tourist Pass','Singapore Tourist Pass',17,'SGD','Adult and child above 0.9m','https://thesingaporetouristpass.com.sg/type-of-passes/','Basic bus, MRT and LRT services. Day of first use to end of service, not 24 hours. Premium services excluded.')
quotes=[dict(id='FX-SALEEM-20261107',provider='Saleem Exchange Centre, Thomson Plaza, via CashChanger',
    source_url='https://cashchanger.co/singapore/mc/saleem-exchange-centre/110',quoted_at='2026-11-07T20:11:00+08:00',
    checked_at='2026-11-08',direction='SGD_to_THB',unit_convention='THB per SGD 1; WE SELL foreign currency',
    local_per_sgd=25.985,fee_sgd=None,minimum_sgd=300,verification_status='rejected_for_SGD50',
    notes='Detailed retail panel has S$300 minimum. Retrieved page contains conflicting duplicate values. No executable S$50 quote confirmed. Prior workbook 26.14379 matches WE BUY, not WE SELL in this panel. Do not use for the pilot.')]
save('ledger',dict(as_of='2026-11-08',prices=prices,quotes=quotes,fx_status='Unavailable for S$50',
    scope='Published examples, not a cost-of-living index or complete daily budget. No automatic source refresh yet.'))

calendar=[]
for i,r in enumerate(prior['Publishing Calendar'][5:]):
    if not r[0]: continue
    calendar.append(dict(id=f'TD-{i+1:03}',publish_at=r[0]+'+08:00',week=r[1],pillar=r[3],title=r[4],
        destination=r[5],cta=r[7],research_status='Research required',video_status='Planned but not started',
        approval_status='Not requested',published=False,platforms=['Instagram','TikTok','YouTube'],actual_views=None))
calendar[0]['research_status']='Four price observations; qualifying FX and food basket missing'
calendar[0]['video_status']='In progress'
save('calendar',calendar)

aff=[]
for i,r in enumerate(prior['Affiliate Directory'][5:]):
    if not r[2]: continue
    aff.append(dict(id=f'AFF-{i+1:02}',name=r[2],category=r[1],signup_url=r[-1],
        singapore_eligibility='Not confirmed',application_requirements='Check live application and contract',
        approval_status='Not applied',commission_basis=None,attribution_days=None,
        completed_booking_rule=None,cancellation_treatment=None,payout_threshold=None,payout_timing=None,
        tracking_id=None,tracking_url=None,priority='Research queue',relevance=r[8],
        restrictions='No paid search, email campaigns or promotion until applicable contract reviewed. Clear affiliate disclosure required.',
        verified_at=None,terms_status='Prior-plan URL only; current full terms not verified'))
for a in aff:
    if a['name']=='Viator':
        a.update(commission_basis='8% on completed qualifying experiences',attribution_days=30,
            completed_booking_rule='Experience must be completed',cancellation_treatment='Cancelled bookings do not qualify',
            priority='First application draft',verified_at='2026-11-08',
            terms_status='Public commission and attribution verified; Singapore onboarding and payout details pending',
            evidence_url='https://partnerresources.viator.com/creator/')
    elif a['name']=='Airalo':
        a.update(commission_basis='Advertised up to 10%; actual Impact contract controls',priority='First application draft',
            verified_at='2026-11-08',terms_status='Public programme verified; full contract and Singapore payout eligibility pending',
            evidence_url='https://www.airalo.com/m/resources/airalo-affiliate-program')
    elif a['name']=='GetYourGuide':
        a.update(commission_basis='Creator page advertises up to 8%',attribution_days=31,
            verified_at='2026-11-08',terms_status='Public headline terms verified; account contract pending',
            evidence_url='https://partner.getyourguide.support/hc/en-us/articles/13981115983133-How-does-the-cookie-ID-tracking-work')
    elif 'Klook Kreator' in a['name']:
        a.update(singapore_eligibility='Singapore-specific programme exists; individual eligibility pending',
            verified_at='2026-11-08',terms_status='Singapore programme page verified; current requirements and terms pending')
save('affiliates',aff)
save('products',[
 dict(name='Bangkok comparison sheet',price_sgd=0,status='In progress',gate='Qualifying FX and full basket missing'),
 dict(name='Bangkok three-day guide',price_sgd=19,status='Planned but not started',gate='Research, route checks, full guide, legal and checkout approval'),
 dict(name='Three-city bundle',price_sgd=39,status='Planned but not started',gate='Three complete guides and demand evidence'),
 dict(name='Membership',price_sgd=9,status='Planned but not started',gate='Recurring value and demand evidence'),
 dict(name='B2B pilot package',price_sgd=450,status='Completed but awaiting approval',gate='One 40–55s original researched reel; one revision; organic use. Stock, paid ads and extensive research quoted separately. Proposed offer only; demand untested.')])
save('status',dict(as_of='2026-11-08',launch='2026-11-25',
    actuals=dict(views=None,clicks=None,recorded_bookings=None,completed_bookings=None,earned_commissions=None,paid_commissions=None,guide_sales=None),
    actuals_note='Accounts not connected. Null means unavailable, never zero.',
    blockers=['No qualifying S$50 retail FX quote','Food and transport comparables not verified','Voice service unavailable; free fallback being tested','Social analytics, affiliate accounts and checkout not connected','ACRA decision before trading under brand name'],
    automation='Existing Monday 08:00 SGT Travel Content Factory updated. No successful run observed; daily/monthly tasks not yet configured.',
    deployment='Existing Codespace on development branch with uncommitted changes; Streamlit port 8501 verified Private. New files not yet installed in Codespace.'))
print(f'Created {len(prices)} price records, {len(calendar)} calendar entries and {len(aff)} affiliate rows')
