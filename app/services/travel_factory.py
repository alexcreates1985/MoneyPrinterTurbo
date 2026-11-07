"""Travel Factory adapters for the existing MoneyPrinterTurbo media engine."""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import os
import re
import tempfile
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.services.travel_research import (
    Research,
    calculate,
    digest,
    source_record,
    storyline,
)
from app.utils import utils
from app.utils.subtitle_reader import moviepy_subtitles


class TravelError(ValueError):
    """A public, credential-free action message."""


def fingerprint(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".travel-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def comparison_card(research: Research, output: Path, background: Path | None = None):
    rows = calculate(research)
    canvas = Image.new("RGB", (1080, 1920), "#101d2d")
    if background:
        with Image.open(background) as image:
            canvas = ImageOps.fit(image.convert("RGB"), canvas.size)
        canvas = Image.blend(canvas, Image.new("RGB", canvas.size, "#101d2d"), 0.88)
    draw = ImageDraw.Draw(canvas)
    font_path = str(Path(utils.font_dir()) / "BeVietnamPro-Bold.ttf")

    def text(value, xy, size=42, color="#ffffff", width=920):
        font = ImageFont.truetype(font_path, size)
        while draw.textlength(str(value), font=font) > width and size > 14:
            size -= 1
            font = ImageFont.truetype(font_path, size)
        draw.text(xy, str(value), font=font, fill=color)

    text("THE TRAVEL COMPARISON", (80, 110), 32, "#67ead9")
    text(f"What can S${research.budget_sgd} buy?", (80, 210), 64)
    text(f"Singapore vs {research.city}", (80, 380), 44)
    text("SGD price / whole units     |     local price / whole units", (80, 470), 25)
    for index, row in enumerate(rows):
        y = 570 + index * 245
        draw.rounded_rectangle((60, y - 20, 1020, y + 200), radius=22, fill="#203448")
        text(row["label"], (85, y), 38)
        text(f"per {row['unit']}", (85, y + 58), 25, "#c3d0e0")
        text(
            f"S${row['sg_price']} / {row['sg_quantity']}", (85, y + 115), 36, "#67ead9"
        )
        text(
            f"{research.currency} {row['local_price']} / {row['local_quantity']}",
            (550, y + 115),
            32,
            "#ffbda1",
            width=430,
        )
    text(
        f"1 SGD = {research.quote.local_per_sgd} {research.currency} | fee S${research.quote.fee_sgd}",
        (80, 1330),
        27,
        "#67ead9",
    )
    text(
        f"FX dated {research.quote.source.data_date} | {research.quote.kind.replace('_', ' ')}",
        (80, 1390),
        25,
    )
    text("Each item gets the full budget separately. Not a basket.", (80, 1445), 25)
    text(
        "Dated examples, not city averages. Sources in accompanying JSON.",
        (80, 1510),
        25,
        "#c3d0e0",
    )
    if background:
        text(
            "Illustrative background; not the listed retailer or product.",
            (80, 1580),
            23,
            "#c3d0e0",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return output


def validate_narration(audio: Path):
    """Reject playlists/external-reference formats before the renderer probes media."""
    from app.services import bgm

    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mp3,wav",
                "-show_entries",
                "format=format_name",
                "-of",
                "json",
                str(audio),
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
        if json.loads(probe.stdout)["format"]["format_name"] not in {"mp3", "wav"}:
            raise ValueError("Unexpected media container")
        bgm.validate_audio_file(str(audio), timeout_seconds=60)
    except (
        ValueError,
        KeyError,
        OSError,
        subprocess.SubprocessError,
        bgm.BgmServiceError,
    ) as error:
        raise TravelError(
            "Uploaded narration must be a complete, standalone MP3 or WAV audio file."
        ) from error


def render(
    research: Research,
    task_id: str,
    voice_name: str,
    background: Path | None = None,
    audio: Path | None = None,
    captions: Path | None = None,
    voice_rate: float = 1.0,
) -> dict:
    """No LLM, paid footage, music or publishing calls; reuse audio/subtitle/render stages."""
    from app.config import config
    from app.models.schema import (
        ImageMotion,
        MaterialInfo,
        VideoConcatMode,
        VideoParams,
    )
    from app.services import task, video, voice

    script = storyline(research)  # Fails closed on incomplete/unreviewed research.
    task_dir = Path(utils.task_dir(task_id))
    params = VideoParams(
        video_subject=f"S${research.budget_sgd}: Singapore vs {research.city}",
        video_script=script,
        video_language="en",
        voice_name=voice_name,
        voice_rate=voice_rate,
        video_source="local",
        video_concat_mode=VideoConcatMode.sequential,
        image_motion=ImageMotion.static,
        bgm_type="",
        bgm_volume=0,
        font_name="BeVietnamPro-Bold.ttf",
        font_size=42,
        n_threads=2,
    )
    if audio:
        if not captions:
            raise TravelError("Uploaded narration requires its matching SRT captions.")
        validate_narration(audio)
        audio_file, duration = str(audio), voice.get_audio_duration(str(audio))
        subtitle_file = str(captions)
        # Reject malformed and out-of-range captions before expensive rendering.
        entries = moviepy_subtitles(subtitle_file)
        if not entries or any(
            start < 0 or end <= start or end > duration + 0.1
            for (start, end), _ in entries
        ):
            raise TravelError(
                "Captions are empty or outside the uploaded narration timeline."
            )

        def normalize(text):
            return re.findall(r"\w+", text.casefold())

        if normalize(" ".join(text for _, text in entries)) != normalize(script):
            raise TravelError(
                "Uploaded captions must match the reviewed storyline exactly."
            )
    else:
        with config.runtime_config_lock():
            audio_file, _, sub_maker = task.generate_audio(task_id, params, script)
        if not audio_file or sub_maker is None:
            raise TravelError(
                "Edge TTS did not produce narration. Check connectivity or upload narration and matching SRT."
            )
        duration = voice.get_audio_duration(audio_file)
        subtitle_file = str(task_dir / "subtitle.srt")
        voice.create_subtitle(
            sub_maker=sub_maker, text=script, subtitle_file=subtitle_file
        )
    if not 35 <= duration <= 45:
        raise TravelError(
            f"Narration is {duration:.1f}s; target is 35–45s. Adjust item count or upload a matching narration and SRT."
        )
    if not Path(subtitle_file).is_file() or not Path(subtitle_file).stat().st_size:
        raise TravelError(
            "Subtitles were not produced; a captioned video cannot be claimed."
        )
    card = comparison_card(
        research,
        Path(utils.storage_dir("local_videos", create=True)) / f"travel-{task_id}.png",
        background,
    )
    params.video_clip_duration = math.ceil(duration)
    materials = video.preprocess_video(
        [MaterialInfo(provider="local", url=str(card))],
        clip_duration=math.ceil(duration),
        image_motion=ImageMotion.static,
    )
    if not materials:
        raise TravelError("Comparison card could not be prepared for rendering.")
    with config.runtime_config_lock():
        videos, _, warnings = task.generate_final_videos(
            task_id,
            params,
            [m.url for m in materials],
            audio_file,
            subtitle_file,
            duration,
        )
    if not videos or not Path(videos[0]).is_file():
        raise TravelError("Rendering produced no MP4.")
    (task_dir / "sources.json").write_bytes(source_record(research))
    receipt = {
        "video": str(videos[0]),
        "video_sha256": fingerprint(Path(videos[0])),
        "research_sha256": digest(research),
        "sources_sha256": fingerprint(task_dir / "sources.json"),
        "duration": duration,
        "width": 1080,
        "height": 1920,
        "warnings": warnings,
        "publication": "not_requested",
        "narration": script,
    }
    save_json(task_dir / "travel-result.json", receipt)
    return receipt


@contextmanager
def publication_lock(folder: Path):
    from filelock import FileLock

    with FileLock(str(folder / ".publication.lock"), timeout=1):
        yield


def record_decision(
    folder: Path, research: Research, approved: bool, platforms: list[str]
) -> dict:
    if (approved and not platforms) or any(
        p not in {"instagram", "tiktok", "youtube"} for p in platforms
    ):
        raise TravelError("Choose supported publication platforms.")
    with publication_lock(folder):
        result = json.loads((folder / "travel-result.json").read_text())
        if approved:
            calculate(research)
            if result["sources_sha256"] != fingerprint(folder / "sources.json"):
                raise TravelError("The source record changed. Render and review again.")
            if result["research_sha256"] != digest(research):
                raise TravelError(
                    "Research changed after rendering. Render and review again."
                )
            if result["video_sha256"] != fingerprint(Path(result["video"])):
                raise TravelError(
                    "The rendered video changed. Render and review again."
                )
        if (folder / "publication.json").exists():
            previous = json.loads((folder / "publication.json").read_text())
            if previous.get("status") in {"sending", "unconfirmed", "complete"}:
                raise TravelError(
                    "A publication attempt already exists; reconcile it before another submission."
                )
        decision = {
            "approved": approved,
            "platforms": sorted(set(platforms)),
            "video_sha256": result["video_sha256"],
            "research_sha256": result["research_sha256"],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "status": "approved" if approved else "rejected",
        }
        save_json(folder / "publication.json", decision)
        return decision


def publish(
    folder: Path,
    account: dict,
    *,
    title: str,
    platforms: list[str],
    made_for_kids: bool,
) -> dict:
    """Called only by the explicit post-review Publish button. Persist before sending."""
    from app.services.upload_post import UploadPostService

    with publication_lock(folder):
        decision = json.loads((folder / "publication.json").read_text())
        result = json.loads((folder / "travel-result.json").read_text())
        if not decision.get("approved") or decision.get("status") != "approved":
            raise TravelError("This video has no unused human publication approval.")
        if sorted(set(platforms)) != decision["platforms"]:
            raise TravelError("Platforms changed; review again.")
        if (
            result["sources_sha256"] != fingerprint(folder / "sources.json")
            or decision["research_sha256"] != result["research_sha256"]
            or decision["video_sha256"] != fingerprint(Path(result["video"]))
        ):
            raise TravelError("Approved evidence or video changed; review again.")
        stored_research = Research.model_validate(
            json.loads((folder / "sources.json").read_text())["research"]
        )
        calculate(stored_research)
        service = UploadPostService(account)
        if not service.is_configured():
            raise TravelError("Upload-Post account and credentials are missing.")
        decision["status"] = "sending"
        save_json(folder / "publication.json", decision)
        try:
            outcome = service.upload_video(
                result["video"],
                title,
                platforms=platforms,
                youtube_extra={
                    "privacyStatus": "private",
                    "selfDeclaredMadeForKids": made_for_kids,
                },
            )
        except Exception:
            outcome = {"success": False}
        decision["status"] = (
            "complete" if outcome.get("success") is True else "unconfirmed"
        )
        # Avoid storing raw upstream error strings, account data or arbitrary headers.
        decision["request_id"] = outcome.get("request_id")
        save_json(folder / "publication.json", decision)
        return decision
