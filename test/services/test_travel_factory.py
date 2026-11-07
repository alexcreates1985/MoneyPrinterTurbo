"""Offline tests use synthetic observations only; they do not validate real prices."""

from datetime import timedelta
from pathlib import Path
import json
import os
import subprocess
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.services import travel_factory as factory
from app.services import travel_research as research


@pytest.fixture
def bundle():
    source = dict(
        publisher="SYNTHETIC TEST SOURCE",
        url="https://example.com/test-only",
        data_date=research.today(),
        accessed_date=research.today(),
        evidence="Synthetic fixture, never use as a real quotation or price",
        reviewed=True,
    )
    return research.Research.model_validate(
        {
            "country": "Test Country",
            "city": "Test City",
            "currency": "TST",
            "budget_sgd": "50",
            "quote": {
                "kind": "singapore_retail",
                "local_per_sgd": "2",
                "fee_sgd": "1",
                "outlet": "TEST ONLY",
                "assumptions": "Synthetic sell-SGD quote; applicable to 50 SGD; fee explicit",
                "source": source,
            },
            "items": [
                {
                    "label": "SYNTHETIC TEST ITEM",
                    "unit": "one item",
                    "comparability": "Same fixture size, taxes included",
                    "singapore": {"amount": "3", "source": source},
                    "destination": {"amount": "4", "source": source},
                }
            ],
        }
    )


def test_blank_pilot_never_renders_or_invents_values():
    blank = research.Research.model_validate(research.template())
    assert blank.city == "Moscow" and blank.quote.local_per_sgd is None
    assert len(research.review_issues(blank)) >= 6
    with pytest.raises(ValueError, match="incomplete"):
        research.storyline(blank)


def test_decimal_fee_direction_and_independent_whole_quantities(bundle):
    row = research.calculate(bundle)[0]
    assert row["local_budget"] == "98"
    assert (row["sg_quantity"], row["local_quantity"]) == (16, 24)
    assert "whole units" in research.storyline(bundle)
    assert "retail cash quotation" in research.storyline(bundle)


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (lambda b: setattr(b.quote, "kind", "indicative"), "retail money-changer"),
        (lambda b: setattr(b.quote, "kind", "estimate"), "estimated exchange"),
        (lambda b: setattr(b.quote.source, "reviewed", False), "reviewed by a person"),
        (
            lambda b: setattr(
                b.quote.source, "data_date", research.today() - timedelta(days=8)
            ),
            "stale",
        ),
        (
            lambda b: setattr(
                b.items[0].destination.source,
                "data_date",
                research.today() - timedelta(days=31),
            ),
            "stale",
        ),
        (
            lambda b: setattr(b.items[0].destination, "kind", "estimate"),
            "observed replacement",
        ),
        (lambda b: setattr(b.quote, "fee_sgd", b.budget_sgd), "fee must be below"),
        (
            lambda b: setattr(
                b.quote.source, "data_date", research.today() + timedelta(days=1)
            ),
            "future",
        ),
    ],
)
def test_unreviewed_stale_and_inapplicable_data_fail_closed(bundle, mutation, expected):
    mutation(bundle)
    assert expected in " ".join(research.review_issues(bundle))
    with pytest.raises(ValueError):
        research.calculate(bundle)


def test_indicative_rate_requires_explicit_choice_and_is_named(bundle):
    bundle.retail_quote_required = False
    bundle.quote.kind = "indicative"
    assert not research.review_issues(bundle)
    assert "not a retail offer" in research.storyline(bundle)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "0", "-1", "0.000000000001"])
def test_unsafe_numbers_rejected(value):
    with pytest.raises(ValidationError):
        research.Price(amount=value)


def test_sources_round_trip_with_dates_units_and_calculations(bundle):
    record = json.loads(research.source_record(bundle))
    assert record["research_sha256"] == research.digest(bundle)
    assert record["research"]["items"][0]["unit"] == "one item"
    assert (
        record["research"]["quote"]["source"]["url"] == "https://example.com/test-only"
    )
    assert research.Research.model_validate_json(bundle.model_dump_json()) == bundle


def test_source_urls_do_not_persist_credentials(bundle):
    source = bundle.quote.source.model_dump()
    for url in (
        "https://user:secret@example.com",
        "https://example.com/?api_key=secret",
        "http://example.com",
    ):
        with pytest.raises(ValidationError):
            research.Source(**{**source, "url": url})


@pytest.fixture
def rendered(tmp_path, bundle):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"synthetic fixture")
    (tmp_path / "sources.json").write_bytes(research.source_record(bundle))
    factory.save_json(
        tmp_path / "travel-result.json",
        {
            "video": str(video),
            "video_sha256": factory.fingerprint(video),
            "research_sha256": research.digest(bundle),
            "sources_sha256": factory.fingerprint(tmp_path / "sources.json"),
        },
    )
    return tmp_path


def test_approval_is_bound_to_video_evidence_and_platforms(rendered, bundle):
    decision = factory.record_decision(rendered, bundle, True, ["instagram"])
    assert decision["status"] == "approved"
    bundle.items[0].singapore.amount += 1
    with pytest.raises(ValueError, match="Research changed"):
        factory.record_decision(rendered, bundle, True, ["instagram"])


def test_rejection_cannot_publish(rendered, bundle):
    factory.record_decision(rendered, bundle, False, ["tiktok"])
    with pytest.raises(ValueError, match="no unused human"):
        factory.publish(
            rendered, {}, title="Test", platforms=["tiktok"], made_for_kids=False
        )


def test_changed_video_or_source_record_invalidates_approval(rendered, bundle):
    factory.record_decision(rendered, bundle, True, ["instagram"])
    (rendered / "video.mp4").write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        factory.publish(
            rendered, {}, title="Test", platforms=["instagram"], made_for_kids=False
        )
    with pytest.raises(ValueError, match="changed"):
        factory.record_decision(rendered, bundle, True, ["instagram"])


def test_source_file_tampering_requires_new_render(rendered, bundle):
    (rendered / "sources.json").write_text("{}")
    with pytest.raises(ValueError, match="source record changed"):
        factory.record_decision(rendered, bundle, True, ["instagram"])


def test_only_explicit_publish_calls_service_once_and_defaults_youtube_private(
    rendered, bundle, monkeypatch
):
    from app.services.upload_post import UploadPostService

    calls = []
    monkeypatch.setattr(UploadPostService, "is_configured", lambda self: True)

    def send(self, path, title, **kwargs):
        calls.append(kwargs)
        return {"success": True, "request_id": "test-only"}

    monkeypatch.setattr(UploadPostService, "upload_video", send)
    factory.record_decision(rendered, bundle, True, ["youtube"])
    assert calls == []
    with pytest.raises(ValueError, match="Platforms changed"):
        factory.publish(
            rendered, {}, title="Test", platforms=["instagram"], made_for_kids=False
        )
    result = factory.publish(
        rendered, {}, title="Test", platforms=["youtube"], made_for_kids=False
    )
    assert result["status"] == "complete"
    assert calls[0]["youtube_extra"] == {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": False,
    }
    with pytest.raises(ValueError):
        factory.publish(
            rendered, {}, title="Test", platforms=["youtube"], made_for_kids=False
        )
    assert len(calls) == 1


def test_uncertain_upload_is_recorded_and_not_blindly_retried(
    rendered, bundle, monkeypatch
):
    from app.services.upload_post import UploadPostService

    monkeypatch.setattr(UploadPostService, "is_configured", lambda self: True)
    monkeypatch.setattr(
        UploadPostService,
        "upload_video",
        lambda *a, **k: {"success": False, "error": "must not persist this"},
    )
    factory.record_decision(rendered, bundle, True, ["tiktok"])
    outcome = factory.publish(
        rendered, {}, title="Test", platforms=["tiktok"], made_for_kids=False
    )
    assert outcome["status"] == "unconfirmed" and "error" not in outcome
    with pytest.raises(ValueError, match="attempt already exists"):
        factory.record_decision(rendered, bundle, True, ["tiktok"])


def test_codespaces_disables_legacy_automatic_publish(monkeypatch):
    from app.config import config
    from app.services.upload_post import UploadPostService

    monkeypatch.setitem(config.app, "upload_post_auto_upload", True)
    monkeypatch.setenv("MPT_REQUIRE_PUBLISH_APPROVAL", "1")
    assert UploadPostService().auto_upload is False


def test_mobile_page_missing_data_blocks_generation(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("MPT_HOME", str(tmp_path))
    root = Path(__file__).resolve().parents[2]
    page = AppTest.from_file(str(root / "webui/Main.py"), default_timeout=30).run()
    page.switch_page("pages/1_Travel_Factory.py").run()
    assert not page.exception
    assert any("Research needs review" in str(w.value) for w in page.warning)
    assert not any("Generate captioned" in b.label for b in page.button)


@pytest.mark.skipif(
    os.environ.get("MPT_RUN_TRAVEL_RENDER_TESTS") != "1",
    reason="opt-in full-resolution 36-second native media test",
)
def test_native_vertical_render_with_fixture_audio_and_captions(
    bundle, tmp_path, monkeypatch
):
    # This exercises encoding, graphics, subtitles and source export. The tone
    # deliberately makes no claim of live TTS, verified prices or real narration.
    from app.utils import utils

    monkeypatch.setattr(utils, "root_dir", lambda: str(tmp_path))
    task_id = str(uuid4())
    folder = Path(utils.task_dir(task_id))
    audio = folder / "fixture.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=36",
            "-y",
            str(audio),
        ],
        check=True,
    )
    captions = folder / "fixture.srt"
    words = research.storyline(bundle).split()
    chunks = [words[i : i + 12] for i in range(0, len(words), 12)]

    def stamp(seconds):
        milliseconds = round(seconds * 1000)
        return f"00:00:{milliseconds // 1000:02},{milliseconds % 1000:03}"

    captions.write_text(
        "\n\n".join(
            f"{i + 1}\n{stamp(i * 36 / len(chunks))} --> {stamp((i + 1) * 36 / len(chunks))}\n{' '.join(chunk)}"
            for i, chunk in enumerate(chunks)
        ),
        encoding="utf-8",
    )
    result = factory.render(bundle, task_id, "", audio=audio, captions=captions)
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                result["video"],
            ]
        )
    )
    stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert (stream["width"], stream["height"], stream["codec_name"]) == (
        1080,
        1920,
        "h264",
    )
    assert 35 <= float(probe["format"]["duration"]) <= 45
    assert any(s["codec_type"] == "audio" for s in probe["streams"])
    assert (folder / "sources.json").is_file()
    assert result["publication"] == "not_requested"


@pytest.mark.skipif(os.name != "posix", reason="Codespaces Linux lifecycle")
def test_codespaces_start_checks_private_port_before_serving(tmp_path):
    root = Path(__file__).resolve().parents[2]
    scripts = tmp_path / ".devcontainer"
    scripts.mkdir()
    script = scripts / "start.sh"
    script.write_text((root / ".devcontainer/start.sh").read_text())
    commands = tmp_path / "bin"
    commands.mkdir()
    gh = commands / "gh"
    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$CALL_RECORD"\nexit 1\n')
    gh.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(commands) + os.pathsep + os.environ["PATH"],
        "CODESPACE_NAME": "test-only",
        "CALL_RECORD": str(tmp_path / "calls"),
    }
    result = subprocess.run(
        ["bash", str(script)], cwd=tmp_path, env=env, capture_output=True
    )
    assert result.returncode == 1
    assert (
        tmp_path / "calls"
    ).read_text().strip() == "codespace ports visibility 8501:private -c test-only"
    assert not (tmp_path / "storage/codespaces/webui.pid").exists()


@pytest.mark.skipif(os.name != "posix", reason="Codespaces Linux lifecycle")
def test_start_reuses_healthy_process_after_enforcing_private_port(tmp_path):
    root = Path(__file__).resolve().parents[2]
    scripts = tmp_path / ".devcontainer"
    scripts.mkdir()
    script = scripts / "start.sh"
    script.write_text((root / ".devcontainer/start.sh").read_text())
    commands = tmp_path / "bin"
    commands.mkdir()
    for name in ("gh", "curl"):
        stub = commands / name
        stub.write_text("#!/bin/sh\nexit 0\n")
        stub.chmod(0o755)
    state = tmp_path / "storage/codespaces"
    state.mkdir(parents=True)
    (state / "webui.pid").write_text(str(os.getpid()))
    env = {
        **os.environ,
        "PATH": str(commands) + os.pathsep + os.environ["PATH"],
        "CODESPACE_NAME": "test-only",
    }
    for _ in range(2):
        result = subprocess.run(
            ["bash", str(script)], cwd=tmp_path, env=env, capture_output=True
        )
        assert result.returncode == 0
    assert (state / "webui.pid").read_text() == str(os.getpid())


def test_narration_rejects_network_playlists_before_media_pipeline(tmp_path):
    playlist = tmp_path / "fake.wav"
    playlist.write_text("#EXTM3U\n#EXTINF:36,\nhttps://example.com/private.wav\n")
    with pytest.raises(factory.TravelError, match="standalone MP3 or WAV"):
        factory.validate_narration(playlist)


def test_uploaded_captions_cannot_introduce_unreviewed_claims(
    bundle, tmp_path, monkeypatch
):
    from app.services import voice, video
    from app.utils import utils

    monkeypatch.setattr(utils, "root_dir", lambda: str(tmp_path))
    monkeypatch.setattr(factory, "validate_narration", lambda path: None)
    monkeypatch.setattr(voice, "get_audio_duration", lambda path: 36)
    monkeypatch.setattr(
        video,
        "preprocess_video",
        lambda *a, **k: pytest.fail("Unreviewed claims reached rendering"),
    )
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"fixture")
    captions = tmp_path / "extra-claim.srt"
    captions.write_text("1\n00:00:00,000 --> 00:00:36,000\nUnreviewed claim\n")
    with pytest.raises(factory.TravelError, match="match the reviewed storyline"):
        factory.render(bundle, str(uuid4()), "", audio=audio, captions=captions)


def test_can_reject_an_old_video_even_after_starting_another_research_draft(
    rendered, bundle
):
    factory.record_decision(rendered, bundle, True, ["instagram"])
    changed = research.Research.model_validate(research.template())
    result = factory.record_decision(rendered, changed, False, [])
    assert result["status"] == "rejected"
    with pytest.raises(factory.TravelError, match="no unused human"):
        factory.publish(
            rendered, {}, title="Test", platforms=["instagram"], made_for_kids=False
        )
