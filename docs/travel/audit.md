# Technical audit: phone-operated travel production

Audited against the existing checkout before adding the Travel Factory. The new
work is additive; it does not replace the API, CLI, provider registry or renderer.

| Area | Existing capability | Gap / decision |
| --- | --- | --- |
| Runtime | Python >=3.11, `.python-version` 3.11, `uv.lock`, dev test/lint groups | Reuse frozen sync; pin uv 0.12.12 in devcontainer |
| UI | Streamlit, translations, provider dialogs, task history, image/video/audio uploads, preview and MP4 download | Add a centered travel page and Safari touch styling |
| Media | MoviePy/Pillow/FFmpeg, portrait 1080×1920, Edge TTS with boundary subtitles, local images and footage | Reuse audio, local image preparation, combination and final rendering |
| LLM | Codex device-code, native ChatGPT OAuth, Ollama and many API providers | Native OAuth requires a same-computer loopback callback and is unsuitable for iPhone→Codespaces; deterministic sourced scripts avoid this dependency |
| Stock | Pexels, Pixabay and other providers already supported | Keep them in full studio; comparison graphics are the factual travel page's default visuals |
| Publishing | Upload-Post supports TikTok, Instagram and YouTube, account snapshots, background status, uncertainty handling | Existing auto-upload has no post-render human review. Codespaces startup disables it; Travel Factory binds manual approval to hashes and platforms |
| API | FastAPI, ping/OpenAPI, authenticated v1 routes when configured, protected file paths | Keep API internal; forward only UI 8501 |
| Containers | Production Dockerfiles/Compose with FFmpeg and localhost-bound published ports | Add a separate non-root Codespaces devcontainer; do not change production images |
| Research | No strict travel-price/FX evidence contract or deterministic budget calculation | Add dated sources, explicit observed/estimated status, retail-vs-indicative rates, fees and independent whole-item calculations |
| CI | Python 3.11/3.13, frozen dependencies, lint, pytest and native FFmpeg checks | Add focused offline travel regressions and an opt-in 36-second full-resolution render check |

No new runtime Python dependencies are required. Standard development needs no
Redis, database, GPU, paid API or account registration. Existing config and
storage are ignored by Git. Production Docker and the original general studio
retain their existing behavior outside the explicit approval-required profile.

## Live limitations found in this environment

No configured runtime provider secrets were reported; selected provider variable
names were checked for presence without printing values. Read-only Git access
works. Direct requests to CashChanger, SingStat and Edge speech were denied by
the cloud network policy (HTTP CONNECT 403). The Codespaces base-image pull was
also denied at `centralus.data.mcr.microsoft.com`. These are environment access
blockers, not evidence of bad credentials or unavailable remote services.

No current Singapore→RUB retail quote or Moscow/Singapore product price has been
verified. The Singapore/Moscow pilot template intentionally contains nulls.
There is no automatic price scraper: source discovery links and manual entry or
JSON import are explicit. Official aggregate statistics must not be silently
relabelled as a retailer's observed price. Automated retrieval requires separate,
source-specific adapters, licensing/terms review and live acceptance tests.
