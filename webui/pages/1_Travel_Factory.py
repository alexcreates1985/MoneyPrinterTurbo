"""Phone-first, source-attested travel production using the existing media engine."""

# ruff: noqa: E402 -- standalone Streamlit entry point must resolve the project first.
from datetime import date
from pathlib import Path
from uuid import uuid4
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
from pydantic import ValidationError

from app.services import travel_factory as factory
from app.services import travel_research as research
from app.services import material_upload
from app.utils import utils

st.set_page_config(page_title="Travel Factory", page_icon="🌏", layout="centered")
st.markdown(
    f"<style>{(ROOT / 'webui/styles.css').read_text()}</style>", unsafe_allow_html=True
)
st.title("Travel Video Factory")
st.caption(
    "Research → review → render → download → approve. Publishing is always a separate action."
)
st.page_link("Main.py", label="Full studio and provider settings")
from webui.travel_animation_panel import show as show_animation_panel
with st.expander("Animated reel studio", expanded=True):
    show_animation_panel()
STORE = Path(utils.storage_dir("travel", create=True))
DRAFT = STORE / "research.json"


def load_draft(value):
    st.session_state.travel_draft = value
    st.session_state.travel_epoch = st.session_state.get("travel_epoch", 0) + 1


if "travel_draft" not in st.session_state:
    try:
        load_draft(
            research.Research.model_validate_json(DRAFT.read_bytes()).model_dump(
                mode="json"
            )
        )
    except (OSError, ValueError):
        load_draft(research.template())

st.header("1. Choose your comparison")
with st.form("destination"):
    country = st.text_input("Destination country", value="Russia")
    city = st.text_input("Destination city", value="Moscow")
    currency = st.text_input("Local currency (ISO code)", value="RUB", max_chars=3)
    budget = st.number_input(
        "Budget in Singapore dollars", min_value=1.0, max_value=10000.0, value=50.0
    )
    if st.form_submit_button("Start a new research draft", use_container_width=True):
        try:
            value = research.template(country, city, currency.upper(), str(budget))
            load_draft(value)
            factory.save_json(DRAFT, value)
            st.rerun()
        except ValueError:
            st.error("Enter a country, city and three-letter currency code.")

st.header("2. Import or enter dated research")
st.info(
    "No prices or rates are prefilled. Open source pages in Safari, check their dates and conditions, then enter observations below. A URL alone does not verify a fact."
)
st.markdown(
    "Source starting points: [Singapore statistics](https://www.singstat.gov.sg/) · [Russia statistics](https://rosstat.gov.ru/) · [Singapore retail quote listings](https://cashchanger.co/singapore). Check the actual outlet's sell-SGD offer; a listing may be stale or have minimum amounts. Published retailer prices are often more useful than city averages."
)
raw = st.file_uploader("Import research JSON from Files", type=["json"])
if st.button("Load imported research", disabled=raw is None, use_container_width=True):
    try:
        if raw.size > 256000:
            raise ValueError("Oversized research")
        value = research.Research.model_validate_json(raw.getvalue()).model_dump(
            mode="json"
        )
        load_draft(value)
        factory.save_json(DRAFT, value)
        st.rerun()
    except (ValueError, ValidationError):
        st.error(
            "Invalid research JSON. Use the downloadable template; keep it under 256 KB."
        )
st.download_button(
    "Download blank pilot template",
    json.dumps(research.template(), indent=2),
    "singapore-moscow-research.json",
    "application/json",
    use_container_width=True,
)

value = st.session_state.travel_draft
prefix = f"travel_{st.session_state.travel_epoch}_"


def key(name):
    return prefix + name


def source_fields(label, source, name):
    source = source or {}
    publisher = st.text_input(
        f"{label}: publisher or retailer",
        source.get("publisher", ""),
        key=key(name + "publisher"),
    )
    url = st.text_input(
        f"{label}: public HTTPS source URL",
        source.get("url", ""),
        key=key(name + "url"),
    )
    data_date = st.date_input(
        f"{label}: observation / quote date",
        date.fromisoformat(source["data_date"])
        if source.get("data_date")
        else research.today(),
        key=key(name + "date"),
    )
    accessed = st.date_input(
        f"{label}: date you checked it",
        date.fromisoformat(source["accessed_date"])
        if source.get("accessed_date")
        else research.today(),
        key=key(name + "access"),
    )
    evidence = st.text_area(
        f"{label}: quoted evidence, size, taxes and location",
        source.get("evidence", ""),
        key=key(name + "evidence"),
    )
    reviewed = st.checkbox(
        f"I checked this {label.lower()} source and its conditions",
        value=source.get("reviewed", False),
        key=key(name + "review"),
    )
    return (
        {
            "publisher": publisher,
            "url": url,
            "data_date": data_date.isoformat(),
            "accessed_date": accessed.isoformat(),
            "evidence": evidence,
            "reviewed": reviewed,
        }
        if publisher or url or evidence
        else None
    )


st.subheader(
    f"{value['country']} / {value['city']} · S${value['budget_sgd']} · {value['currency']}"
)
count = st.selectbox(
    "Number of comparable items (1–3)",
    [1, 2, 3],
    index=len(value["items"]) - 1,
    key=key("count"),
)
with st.form(key("evidence_form")):
    quote = value["quote"]
    with st.expander("Exchange quotation", expanded=True):
        retail_required = st.checkbox(
            "Require a Singapore retail money-changer quote",
            value=value["retail_quote_required"],
        )
        kinds = ["singapore_retail", "indicative", "estimate"]
        kind = st.selectbox("Rate type", kinds, index=kinds.index(quote["kind"]))
        rate = st.text_input(
            f"{value['currency']} received for ONE SGD (not the reverse)",
            value=quote.get("local_per_sgd") or "",
        )
        fee = st.text_input("Total exchange fee in SGD", value=quote["fee_sgd"])
        outlet = st.text_input(
            "Money changer / rate publisher and outlet", value=quote["outlet"]
        )
        assumptions = st.text_area(
            "Exchange direction, minimum amount, availability and fee assumptions",
            value=quote["assumptions"],
        )
        fx_source = source_fields("Quote", quote.get("source"), "fx")
    items = []
    for index in range(count):
        old = (
            value["items"][index]
            if index < len(value["items"])
            else research.template()["items"][0]
        )
        with st.expander(f"Item {index + 1}"):
            label = st.text_input("Item name", old["label"], key=key(f"label{index}"))
            unit = st.text_input(
                "Comparable price unit (e.g. one 500 ml bottle)",
                old["unit"],
                key=key(f"unit{index}"),
            )
            comparability = st.text_area(
                "Explain comparability, sizes, taxes and shop locations",
                old["comparability"],
                key=key(f"compare{index}"),
            )
            prices = {}
            for location, title in (
                ("singapore", "Singapore"),
                ("destination", value["city"]),
            ):
                currency_label = "SGD" if location == "singapore" else value["currency"]
                name = f"{index}_{location}_"
                price = st.text_input(
                    f"{title}: price per unit in {currency_label}",
                    old[location]["amount"] or "",
                    key=key(name + "amount"),
                )
                status = st.selectbox(
                    f"{title}: price status",
                    ["observed", "estimate"],
                    index=0 if old[location]["kind"] == "observed" else 1,
                    key=key(name + "status"),
                )
                source = source_fields(title, old[location].get("source"), name)
                prices[location] = {
                    "amount": price or None,
                    "kind": status,
                    "source": source,
                }
            items.append(
                {"label": label, "unit": unit, "comparability": comparability, **prices}
            )
    if st.form_submit_button(
        "Save research and check missing evidence", use_container_width=True
    ):
        try:
            candidate = {
                **value,
                "retail_quote_required": retail_required,
                "quote": {
                    "kind": kind,
                    "local_per_sgd": rate or None,
                    "fee_sgd": fee,
                    "outlet": outlet,
                    "assumptions": assumptions,
                    "source": fx_source,
                },
                "items": items,
            }
            checked = research.Research.model_validate(candidate)
            load_draft(checked.model_dump(mode="json"))
            factory.save_json(DRAFT, checked.model_dump(mode="json"))
            st.rerun()
        except ValidationError as error:
            st.error(
                "Check required fields, HTTPS source URLs, numeric values and dates: "
                + ", ".join(
                    " / ".join(str(p) for p in e["loc"]) for e in error.errors()
                )
            )

bundle = research.Research.model_validate(st.session_state.travel_draft)
issues = research.review_issues(bundle)
st.download_button(
    "Download current research draft",
    bundle.model_dump_json(indent=2),
    "travel-research.json",
    "application/json",
    use_container_width=True,
)
if issues:
    st.warning(
        "Research needs review. Rendering is blocked until these values are sourced:"
    )
    for issue in issues:
        st.write(f"• {issue}")
else:
    st.header("3. Review the storyline")
    script = research.storyline(bundle)
    st.write(script)
    st.dataframe(research.calculate(bundle), hide_index=True)
    st.caption(
        f"{len(script.split())} words. Actual narration must measure 35–45 seconds. Each item uses the entire budget independently."
    )
    st.download_button(
        "Download script",
        script,
        "travel-script.txt",
        "text/plain",
        use_container_width=True,
    )
    approved = st.checkbox(
        "I reviewed every fact, exchange condition and the full storyline; any uploaded narration speaks this exact script",
        key="review_" + research.digest(bundle),
    )
    st.header("4. Voice and visuals")
    voice = st.selectbox(
        "English Edge voice",
        [
            "en-SG-WayneNeural-Male",
            "en-SG-LunaNeural-Female",
            "en-US-AriaNeural-Female",
        ],
    )
    voice_rate = st.slider("Narration speed", 0.8, 1.5, 1.0, 0.05)
    st.caption(
        "Comparison graphics are included. Optional background photos are labelled illustrative. Use the full studio for stock footage or custom production."
    )
    background = st.file_uploader(
        "Optional background photo (JPEG / PNG)", type=["jpg", "jpeg", "png"]
    )
    rights = st.checkbox(
        "I have permission to use this background", disabled=background is None
    )
    audio = st.file_uploader(
        "Optional English narration (35–45 seconds)", type=["mp3", "wav"]
    )
    captions = st.file_uploader(
        "Matching SRT of the reviewed storyline (required with uploaded narration)",
        type=["srt"],
    )
    if st.button(
        "Generate captioned vertical video",
        type="primary",
        use_container_width=True,
        disabled=not approved or (background is not None and not rights),
    ):
        task_id = str(uuid4())
        folder = Path(utils.task_dir(task_id))
        try:
            background_path = None
            if background:
                # Reuse the existing image validator instead of trusting filename extensions.
                stored = material_upload.save_material_upload(
                    background.name, background
                )
                background_path = Path(material_upload.uploaded_material_dir()) / stored
            audio_path = captions_path = None
            if audio:
                if (
                    audio.size > 20 * 1024 * 1024
                    or not captions
                    or captions.size > 256000
                ):
                    raise ValueError(
                        "Provide narration under 20 MB and matching SRT under 256 KB."
                    )
                audio_path = folder / ("narration" + Path(audio.name).suffix.lower())
                audio_path.write_bytes(audio.getvalue())
                captions_path = folder / "uploaded.srt"
                captions_path.write_bytes(captions.getvalue())
            with st.spinner(
                "Creating narration, comparisons and MP4. This can take several minutes."
            ):
                factory.render(
                    bundle,
                    task_id,
                    voice,
                    background_path,
                    audio_path,
                    captions_path,
                    voice_rate,
                )
            st.session_state.travel_selected_task = task_id
            st.success(
                "Video rendered. Preview it below before approving any publication."
            )
        except factory.TravelError as error:
            st.error(str(error))
        except Exception as error:
            st.error(
                f"Generation did not complete ({type(error).__name__}). Check 35–45s narration, matching captions and connectivity; no video success is claimed."
            )

st.header("5. Preview, download and publication decision")
receipts = sorted(
    Path(utils.task_dir()).glob("*/travel-result.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
if not receipts:
    st.caption(
        "No completed Travel Factory videos yet. Research drafts survive restarts; live jobs do not."
    )
else:
    receipt = st.selectbox(
        "Completed video", receipts, format_func=lambda p: p.parent.name
    )
    result = json.loads(receipt.read_text())
    folder = receipt.parent
    video_path = Path(result["video"])
    if video_path.is_file():
        st.video(str(video_path))
        with video_path.open("rb") as stream:
            st.download_button(
                "Download MP4 to iPhone",
                stream,
                "travel-comparison.mp4",
                "video/mp4",
                use_container_width=True,
            )
        st.download_button(
            "Download source record",
            (folder / "sources.json").read_bytes(),
            "travel-sources.json",
            "application/json",
            use_container_width=True,
        )
        with st.expander("Source record for this video"):
            st.json(json.loads((folder / "sources.json").read_text()))
        st.caption(
            "On iPhone, use Safari's Downloads menu or Share → Save to Files. Keep the source record alongside the MP4."
        )
        platforms = st.multiselect(
            "Publication platforms",
            ["instagram", "tiktok", "youtube"],
            default=["instagram"],
            key="platforms_" + result["video_sha256"],
        )
        reviewed_video = st.checkbox(
            "I watched this finished video and checked its sources",
            key="watched_" + result["video_sha256"],
        )
        if st.button(
            "Record approval",
            disabled=not reviewed_video or not platforms,
            use_container_width=True,
        ):
            try:
                factory.record_decision(folder, bundle, True, platforms)
                st.success(
                    "Approval recorded for this exact MP4 and source record. Nothing has been published."
                )
            except (ValueError, OSError, TimeoutError) as error:
                st.error(str(error))
        if st.button("Reject publication", use_container_width=True):
            try:
                factory.record_decision(folder, bundle, False, platforms)
                st.success("Publication rejected.")
            except (ValueError, OSError, TimeoutError) as error:
                st.error(str(error))
        with st.expander("Optional Upload-Post account and explicit publishing"):
            st.caption(
                "No account or paid service is activated here. Connect platforms at Upload-Post first. Keys below stay in this browser session; Codespaces secrets can supply UPLOAD_POST_API_KEY and UPLOAD_POST_USERNAME on restart."
            )
            api_key = st.text_input(
                "Upload-Post API key",
                value=os.environ.get("UPLOAD_POST_API_KEY", ""),
                type="password",
            )
            username = st.text_input(
                "Upload-Post connected user",
                value=os.environ.get("UPLOAD_POST_USERNAME", ""),
            )
            made_for_kids = st.checkbox(
                "This video is made for children (YouTube audience declaration)",
                key="audience_" + result["video_sha256"],
            )
            st.caption(
                "YouTube uploads start as private. Instagram/TikTok visibility follows the connected account and provider settings."
            )
            confirm = st.checkbox(
                "Publish the approved video to the selected accounts now; I accept any provider charges",
                key="publish_" + result["video_sha256"],
            )
            if st.button(
                "Publish approved video now",
                disabled=not confirm,
                use_container_width=True,
            ):
                try:
                    outcome = factory.publish(
                        folder,
                        {
                            "upload_post_enabled": True,
                            "upload_post_api_key": api_key,
                            "upload_post_username": username,
                        },
                        title=f"Singapore vs {json.loads((folder / 'sources.json').read_text())['research']['city']}",
                        platforms=platforms,
                        made_for_kids=made_for_kids,
                    )
                    st.write(outcome)
                    if outcome["status"] == "unconfirmed":
                        st.warning(
                            "Do not retry blindly. Reconcile the request in Upload-Post first."
                        )
                except (ValueError, OSError, TimeoutError) as error:
                    st.error(str(error))
    else:
        st.warning("This MP4 is missing; restore its files or render again.")
