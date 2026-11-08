# TravelDecoded operating handoff — 8 November 2026

## Current result

The existing private Travel Factory was inspected. It is on `feat/iphone-travel-factory` in Codespace `reimagined-halibut-6vrxprjqw9jg34p4r`; port 8501 was verified Private and the dashboard loaded. The Codespace has uncommitted changes. Do not reset, overwrite, pull into or rebuild that working tree without first preserving and reviewing its changes. Main and draft PR #1 were not merged.

Existing private dashboard: https://reimagined-halibut-6vrxprjqw9jg34p4r-8501.app.github.dev/Travel_Factory

The new business page is additive. Deployment into that existing Codespace has NOT been verified. The portable pages run from the review bundle; they are not a public website. Open `dashboard.html` or `bangkok.html` after extracting the bundle. Keep the PDF, video, cover and ledger alongside the pages so relative links resolve. iPhone file previews may not execute JavaScript; the private Streamlit page is the intended interactive route after deployment.

## Reproduce locally

Use the project's documented environment for existing Travel Factory dependencies. New business logic uses Python's standard library. The added business page requires the existing Streamlit dependency. Review-video rendering additionally requires Pillow, edge-tts, FFmpeg and the bundled font. Edge TTS needs network access; its availability is not a guarantee of future service or commercial rights. Review applicable service terms before commercial publication.

1. `python scripts/build_travel_preview.py` regenerates portable HTML and CSV from JSON snapshots.
2. `python -m pytest test/services/test_travel_business.py -q` checks FX rejection, missing actuals, calendar, tracking-link gates and financial arithmetic.
3. `streamlit run webui/Main.py --server.address 0.0.0.0 --server.port 8501` uses the existing multipage app. Keep forwarded port Private.
4. `python scripts/render_travel_review.py` renders the separate evidence-review draft, not an approved full basket comparison. Voice and timings are cached under `storage/traveldecoded-review`. If editing the script, archive the old output folder before rerendering to avoid reusing stale narration.
5. Use the existing Travel Factory approval flow for future source-complete videos. A rendered file does not constitute approval to publish.

`build_travel_business.py` is a one-time seed utility and refuses to overwrite existing registers. Do not run it over edited operating data. All daily research remains manual/assisted; automatic web source ingestion is not implemented.

## Data contract and recovery

JSON files are the source of truth for this first build. `prices.csv` is an export. Each source change needs a new timestamped observation; retain previous values and provenance. No quote may pass if direction, fees, minimum or timestamp is unverified. S$50 must be an executable amount, not an extrapolation from a S$300 minimum. Unknown actuals stay null. The existing production service has a positive-price schema; zero-price eligibility observations in this new ledger are not automatically imported into it.

The original comparison engine spends the full budget on each example independently. It must not be described as one basket until basket accounting is implemented and tested. The new review avoids this problem and claims no converted total.

Recovery: preserve the branch and exported bundle. Restore JSON from a dated export, regenerate previews and rerun tests. Do not add credentials to records. Accounts should be reconnected through provider authentication, never by placing passwords or tokens in source code.

## Scheduling and monitoring

Existing Monday 08:00 Singapore Travel Content Factory task was updated, not duplicated. No successful run was observed; next-run metadata was unavailable. Daily and monthly tasks are not configured. No claim of unattended production or publication is made.

Weekly review fields: source age, current FX eligibility, research-ready scripts, approval queue, views, retention, profile visits, site sessions, outbound clicks, recorded/completed bookings, earned/paid commissions, sales, refunds, fees and cash. All external performance fields currently remain unavailable.

Largest current bottleneck: source-complete, review-approved content. First experiment: compare a concrete budget hook with an eligibility hook in the first six approved videos. Measure 3-second retention and outbound clicks using actual permitted platform analytics; do not declare a winner before gathering comparable results.

## Required external actions and approvals

- Obtain a reliable S$50 foreign-currency selling quote with fees and unit convention. Reverify matched food and transport items.
- User reviews voice, visuals, figures and disclosures for each video; no social publishing without approval.
- Confirm treatment of existing uncommitted Codespace work before deploying changes into it. A clean separate checkout is safer than destructive reset.
- Connect approved Instagram, TikTok and YouTube reporting through permitted APIs. No API credentials are currently configured for this build.
- Approve affiliate applications and applicable terms; enter personal/tax/payment details only in secure provider forms.
- Confirm Singapore payout eligibility, transaction fees, refund policy and consumer-facing terms before enabling checkout. Whop suitability remains unconfirmed.
- Review ACRA registration before commercially trading under Alex TravelDecoded; official ACRA guidance generally requires registration for regular for-profit business unless exempt. Do not assume operating under a brand is exempt. https://www.acra.gov.sg/register/business/requirements-eligibility/
- Keep income/expense evidence and assess tax obligations. Review IRAS self-employed and social-media income guidance before launch; no tax calculation has been completed.
- Establish privacy notice, consent and unsubscribe process before collecting emails. No collection is active now.

## Validation and limitations

Five new business-logic tests passed. Streamlit AppTest mounted the new business page and changed scenarios successfully. Full video decode succeeded; output is 1080 × 1920, 24fps, 51.216 seconds with audio and timed captions. Sample frames and both PDF pages were visually inspected. Full human listening review remains pending. No current claim is made that the historical 3,222-test suite was rerun.

Automated Chromium layout testing was attempted twice: bundled Playwright executable missing, then system Chromium blocked by socket permissions. Mobile CSS is implemented but mobile browser layout validation remains incomplete. No browser-test pass is claimed.
