# Validation record

Local validation on 2026-11-07 with Python 3.11.17. No paid service was activated,
no external account was registered, and no video was published.

| Check | Result |
| --- | --- |
| `uv sync --frozen --python 3.11` via lifecycle install script | Passed; 126 dependencies checked, lockfile unchanged |
| Lifecycle startup and second start | Passed locally with loopback binding; second invocation reused the healthy process |
| Codespaces private-port enforcement | Offline shell tests passed, including stopping before serving if GitHub privacy enforcement fails |
| Official Dev Containers CLI 0.80.2 `read-configuration` | Passed; devcontainer, lifecycle paths, private-workflow profile and feature parsed |
| Full devcontainer image build | Blocked during Microsoft base-image download: policy denied `centralus.data.mcr.microsoft.com`; no successful build or new Codespace claimed |
| Repository Ruff lint, Python compilation, shell syntax, diff whitespace | Passed |
| Focused travel regression tests | 31 passed, 1 opt-in native-render test skipped in normal mode |
| Opt-in native render | Passed separately: real 36-second, 1080×1920 H.264 MP4 with audio, visible captions and comparison graphics; dated JSON source export retained |
| Mobile Chromium at iPhone 13 / 390 CSS pixels | Passed navigation, no horizontal overflow, 44-pixel controls, JSON upload, review gate, template and MP4 download, and publication approval |
| Download integrity | Browser-downloaded MP4 SHA-256 exactly matched the rendered MP4 |
| API | `/ping` returned `pong`; OpenAPI contained 13 routes including video endpoints |
| Full existing offline suite plus initially collected travel tests | 3,222 passed, 72 skipped, 12,891 subtests passed; no failures (14m29s) |

The native test uses clearly named synthetic observations, a fictitious currency
and **tone audio**. It verifies the media engine and export path, not real prices,
spoken narration, live Edge TTS or the requested Singapore/Moscow pilot. Browser
checks used a temporary synthetic receipt, then removed it and reset the draft to
the blank pilot. No sample is presented as research or a publishable pilot.
Mobile Chromium emulation does not prove physical iPhone Safari compatibility.

## Reproduce the local checks

From the repository root, after dependency installation:

```bash
uv run --no-sync ruff check app cli.py main.py webui test docs/skill
uv run --no-sync python -X utf8 -m pytest -q test/services/test_travel_factory.py
MPT_RUN_TRAVEL_RENDER_TESTS=1 uv run --no-sync python -X utf8 -m pytest -q \
  test/services/test_travel_factory.py::test_native_vertical_render_with_fixture_audio_and_captions
uv run --no-sync python -X utf8 -m pytest -q test
bash -n .devcontainer/install.sh .devcontainer/start.sh
```

FFmpeg and FFprobe are required for the opt-in full-resolution check. It takes
roughly two minutes on the validation machine; resource use varies. Final follow-up tests cover additions made after full-suite collection. Unit tests
exercise missing/stale data, estimates, indicative-rate substitution, decimal
calculation, evidence review, playlist rejection, caption/script consistency,
source/video tampering, approval rejection, platform changes, publication
uncertainty and preventing duplicate sends. Upload-Post is mocked in tests.

## Remaining external checks

- Get and personally review a current retail SGD→RUB quote applicable to S$50,
  plus comparable dated Singapore/Moscow prices. None was retrieved or verified.
  The pilot must stay blocked until these exist. Manual source import is
  implemented; automatic price/retail-rate retrieval is not.
- Research source and Edge speech probes returned HTTP CONNECT 403 from this
  machine's enforced cloud policy. Required starting domains include
  `cashchanger.co`, `www.singstat.gov.sg` and `speech.platform.bing.com`, plus
  actual retailer/statistics hosts and any redirects. Request only destinations
  you actually choose. Codespaces has its own network policy; these denials do
  not establish service availability there. No existing allowlist was replaced.
- Complete an authenticated Codespace build/start and check the forwarded HTTPS
  port remains Private. This session did not create paid compute or validate a
  new Codespace or physical Safari session.
- Test live Edge narration or your own narration with exact matching SRT, then
  review the real pilot MP4 and its source record.
- Upload-Post requires your account, connected platforms, credentials and any
  needed plan. Its live API connection and actual publication are untested and
  must not run without separate explicit approval of the completed video.
- GitHub API requests were denied by the current network policy. Git transport
  read and a branch-push dry run worked; PR creation may require API access or
  the manual GitHub compare page.
