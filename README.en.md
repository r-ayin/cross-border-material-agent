<div align="center">

[![version](https://img.shields.io/badge/version-1.1.0-2F6FEB?style=flat-square)](agent/agent.json)
[![python](https://img.shields.io/badge/python-3.12%2B-2F6FEB?style=flat-square)](https://www.python.org/)
[![dependencies](https://img.shields.io/badge/dependencies-zero-1A7F5A?style=flat-square)](agent/requirements.txt)
[![tests](https://img.shields.io/badge/tests-183%20offline-1A7F5A?style=flat-square)](tests/)
[![markets](https://img.shields.io/badge/markets-US%20%7C%20KR%20%7C%20BR-2F6FEB?style=flat-square)](research/localization.md)
[![license](https://img.shields.io/badge/license-MIT-1A7F5A?style=flat-square)](#-license)

</div>

---

# Cross-Border Material Generation Agent

**One product record in, 11 marketplace-ready localized assets out. Rehearse offline, generate on authorization.**

Built for cross-border e-commerce (AliExpress and comparable marketplaces):
it reads a product source JSON plus the platform's category and attribute libraries,
then produces three localized listings, six product images, one product video,
and a content-strategy document — all with strict filenames, bounded sizes,
and parsable structure.

[中文](README.md) · [Task Specification](docs/problem-detail.html) · [Pipeline SOP](docs/pipeline-sop.md) · [Research](research/)

---

## 📖 Table of Contents

| | |
|---|---|
| [🎯 Capabilities](#-capabilities) | [📦 Output Set](#-output-set) |
| [⚡ Quick Start](#-quick-start) | [🔧 Configuration](#-configuration) |
| [🧭 CLI](#-cli) | [🏗 Pipeline Architecture](#-pipeline-architecture) |
| [🛡 Quality Gates](#-quality-gates) | [📸 Image Generation](#-image-generation) |
| [🎬 Video Generation](#-video-generation) | [✍️ Copy Generation](#-copy-generation) |
| [🗂 Category and Attribute Mapping](#-category-and-attribute-mapping) | [🖥 Material Workbench](#-material-workbench) |
| [📁 Project Structure](#-project-structure) | [🧪 Tests](#-tests) |
| [📄 License](#-license) | |

---

## 🎯 Capabilities

### Two-phase execution: offline planning first, authorized generation second

The agent's default state is **network-denied**. Given `--plan-only`, it reads the source data,
derives a complete creative plan, and writes `generation_plan.json` with
**zero model calls and zero network requests** — storyboard, subtitles, frame allocation,
and the role contract for each of the six image slots, all on paper before a single credit is spent.

Model calls only happen once you explicitly set `AGENT_ALLOW_CALLS` (`AGENT_ALLOW_PAID_CALLS=1`).
Supplying an API key is configuration, not authorization — they are separate switches,
and the agent refuses to treat one as the other.

### Facts outrank rhetoric

The usual failure mode of a material-generation agent isn't a missing image —
it's a beautiful, wrong one: invented fabric composition, fabricated certifications,
converted sizes that were never measured. This agent encodes "do not invent"
in code, not merely in prompts:

- **Attributes are never invented.** Every category and attribute value must come from the platform
  library. An `attrId` absent from the library is dropped; a `valueId` absent from its enumeration is
  dropped. Free text is accepted only for attributes the library defines no enumeration for at all.
- **Sizes are never converted.** Without measured data, the size chart is marked as missing.
  Centimetre/inch and international-equivalent conversions are **never** computed — any form of
  size equivalence is caught by the quality checker.
- **Claim words require evidence.** Composition, care, logistics, certification, performance,
  season, and currency are all flagged as unverified unless found verbatim in the source.
- **Material words require evidence.** Same for 13 material descriptors — and evidence containing a
  negation ("no", "does not contain", "not") downgrades the claim rather than confirming it.

### Structural acceptance, not "it finished"

Completion is not usability. The agent structurally validates all 11 artifacts locally and emits a
**three-level verdict** with a matching exit code, so a CI job can auto-advance or block on it.

### Zero dependencies

Pure Python standard library (`urllib` / `json` / `concurrent.futures` / `threading` / `struct`).
`requirements.txt` contains two comment lines and nothing else. No `pip install`, no compiler,
unzip and run inside a network-isolated sandbox. 5049 lines of source, and deliberately no
LangGraph / CrewAI / Dify: this task is deterministic batch processing, where an agent framework's
autonomous planning is over-engineering that costs time and tokens.

---

## 📦 Output Set

A run produces **11 required artifacts** with fixed filenames that downstream scripts can parse directly:

| Type | Artifact | Spec |
|:---:|---|---|
| Copy | `product_description_en.md` | English (US) · six sections · 5–7 bullets |
| Copy | `product_description_ko.md` | Korean (KR) · localized section headings |
| Copy | `product_description_pt.md` | Brazilian Portuguese (BR) |
| Image | `main_image.png` | 1328×1328 · pure white background · product ≥70% of frame |
| Image | `detail_image_1.png` | Overall selling point |
| Image | `detail_image_2.png` | Craftsmanship close-up |
| Image | `detail_image_3.png` | Material close-up |
| Image | `detail_image_4.png` | Lifestyle scene |
| Image | `detail_image_5.png` | Complete overview |
| Video | `product_video.mp4` | 1280×720 · 5s · < 200 MB |
| Document | `strategy_document.md` | Content and placement strategy |

**Companion artifacts**

| File | Purpose |
|---|---|
| `listing.json` | Structured listing; assets indexed as arrays |
| `quality_report.json` | Per-artifact technical validity and acceptance status |
| `run_manifest.json` | Stage event timeline + request-count snapshot |
| `generation_plan.json` | Offline plan emitted by `--plan-only` |
| `copy_quality.json` | Copy fact and language quality audit |
| `video_manifest.json` / `product_video_srt.srt` | Video generation metadata and sidecar subtitles |

---

## ⚡ Quick Start

### Prerequisites

```
Python 3.12+ · no dependencies to install · a Qwen platform API key (real generation only)
```

Obtain an API key from the [Qwen platform](https://platform.qianwenai.com).

### 1 · Offline rehearsal (no key, no network)

See exactly what it intends to do:

```bash
cd agent
python3 agent.py --plan-only --prompt "Read all information files for the target product under /path/to/input/, extract the specified content, and write the generated files to /path/to/output/."
```

Output:

```
offline plan: 11 required slots; model calls=0
```

Plus a complete `generation_plan.json`. This step **spends nothing** and is designed to run inside
review and regression pipelines.

### 2 · Full-pipeline rehearsal (no key, all network stubbed)

```bash
python3 tests/mock_e2e.py
```

`mock_e2e.py` replaces `socket` and `urlopen` with stubs that raise,
so any real network call fails the test by construction. It verifies orchestration,
structural completeness, and exit-code semantics — and it deliberately asserts that a mock run is
**not** publish-ready (a structurally complete run must exit `2`, not `0`).

### 3 · Real generation (key + explicit authorization)

```bash
export DASHSCOPE_API_KEY="<your-key>"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/api/v1"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export AGENT_ALLOW_PAID_CALLS=1          # ← the authorization switch, separate from the key

cd agent
python3 agent.py --version               # 1.1.0
python3 agent.py --prompt "Read all information files for the target product under /path/to/input/ ... write to /path/to/output/."
```

> Ensure the output directory is empty. If artifacts from a previous run are present,
> the agent refuses to start, so stale files can never be mistaken for this run's output.

### 4 · Open the material workbench

```bash
python3 -m http.server 18765 --bind 127.0.0.1 --directory frontend
# open http://127.0.0.1:18765/workbench.html
```

For scrubbable video, use the Range-capable preview server:

```bash
python3 tools/preview_server.py          # defaults to 18766, supports Range requests
```

---

## 🔧 Configuration

| Variable | Required | Purpose |
|:---|:---:|---|
| `DASHSCOPE_API_KEY` | Real generation | Qwen platform API key |
| `DASHSCOPE_BASE_URL` | Real generation | DashScope async-task endpoint |
| `OPENAI_BASE_URL` | Real generation | OpenAI-compatible endpoint (Chat / Image) |
| `AGENT_ALLOW_PAID_CALLS` | Real generation | Authorization switch; must be `1`, otherwise all network calls are refused |

Runtime limits enforced inside `RuntimePolicy`:

| Constraint | Value |
|---|---|
| Requests per run | 64 |
| Media requests per run | 24 |
| Hard deadline | 28 minutes (from 45s before budget end) |
| Network egress | HTTPS only; URLs with embedded credentials rejected |
| Redaction | tokens, `api_key`/`authorization` values, and URL query strings replaced before logging or output |

---

## 🧭 CLI

```
python3 agent.py [--prompt TEXT] [--version] [--plan-only]
                 [--audit OUTPUT_DIR] [--check-plan JSON_FILE]
```

| Flag | Behavior |
|---|---|
| `--prompt TEXT` | Natural-language instruction; the agent parses input and output directories from it |
| `--version` | Print the version (`1.1.0`) and exit |
| `--plan-only` | **Plan without generating.** Reads no key, sends no request, writes `generation_plan.json` |
| `--audit OUTPUT_DIR` | **Read-only** inspection of an existing artifact directory; JSON to stdout, no generation |
| `--check-plan JSON_FILE` | Validate an exported plan file; **never executes anything inside it** |

### Exit codes

| Code | Meaning |
|:---:|---|
| `0` | All 11 artifacts accepted (`publish_ready`) |
| `2` | Structurally complete, still needs human review |
| `1` | Not structurally complete |
| `124` | Hard deadline fired; process terminated by the watchdog |

> `2` is a first-class outcome, not a failure. Structural completeness and publish-readiness are
> different things, and the agent will not let the first masquerade as the second.

---

## 🏗 Pipeline Architecture

**Stage-based pipeline + thread-pool concurrency + exponential backoff + model fallback chains.**
Four stages, with media generation running three ways in parallel under `ThreadPoolExecutor(max_workers=3)`.

```
P0  Input parsing ─────────▶ visual observation ──┐
                                                  │
P1  Category + attribute mapping ─────────────────┤
                                                  ▼
P2  Copy ∥ Images ∥ Video    (three worker threads)
                                                  │
P3  Format fixup → strategy doc → listing.json → quality report → exit code
```

| Stage | Task | Model |
|---|---|---|
| P0 | Parse `--prompt`; load product / categories / attributes | — |
| P0 | Visual observation of source images (visible geometry, colour, pattern only) | `qwen-vl-max` |
| P1 | Select target leaf category (66 attribute-bearing candidates) | `qwen3.7-max` |
| P1 | Attribute / sales-attribute enumeration mapping (three-tier strategy) | `qwen3.7-max` |
| P2 | Three-language copy (en / ko / pt in parallel) | `qwen3.8-max` → `qwen3.7-max` |
| P2 | Main image ×1 + detail images ×5 (six slots) | see [Image Generation](#-image-generation) |
| P2 | Product video ×1 (source image as first frame) | `wan2.7-i2v-2026-04-25` → `happyhorse-1.1-r2v` → `happyhorse-1.1-t2v` |
| P3 | Strategy document | `qwen3.7-max` |
| P3 | Format adaptation → `listing.json` → quality report | — |

### Three tiers of fault tolerance

| Tier | Mechanism |
|---|---|
| **API** | Exponential backoff on 429 / 5xx / network errors. Base 4s → cap 60s, up to 4 attempts, 0–2s jitter. The chat channel is wider: 6 attempts / 90s cap |
| **Model** | Every generation path carries a fallback chain; on failure it **advances to the next model** rather than repeating the same call |
| **Stage** | `Budget` guard plus a `HardDeadline` watchdog. Under time pressure it degrades deliberately; if a vendor trickles bytes to defeat cooperative HTTP timeouts, the watchdog hard-kills the process at 28 minutes |

### Credential discipline

`PolicyError` is **non-retryable** inside `with_retry`. An authorization failure is a policy signal,
not a transient fault — retrying only repeats the refusal against the same target.

---

## 🛡 Quality Gates

### Three-level verdict

| Verdict | Meaning |
|---|---|
| `technical_valid` | The artifact passes local structural checks (dimensions, size, sections, non-empty, container integrity) |
| `structurally_complete` | **All 11** artifacts are `technical_valid` |
| `publish_ready` | **All 11** artifacts are `accepted` — both technical and content checks passed |

### Structural checks

| Artifact | Checks |
|---|---|
| Copy / strategy | 0–1 MB · no NUL bytes · all six sections present with localized headings · title ≤128 characters |
| Images | ≤5 MB · valid format · main image min edge ≥800 · detail image min edge ≥261 |
| Video | Deep-validated by `media_probe` |

### `media_probe` — an MP4 validator that never decodes

Pure standard-library ISO BMFF box parsing. **It never decodes a video frame**,
which lets it perform a bounded check on a large file inside a constrained environment:

- Top-level `ftyp` / `moov` / non-empty `mdat` all present
- Fragmented MP4 (`moof` / `mvex`) and multi-video-track rejected → status `unsupported`, not `invalid`
- Track count 1–128
- Per-sample table consistency: `stsd` / `stts` / `stsz` / `stsc` / `stco`–`co64` bounds and ordering
- `ctts` / `stts` composition coverage plus `elst` edit lists (rate-1, at most two, optional leading empty edit)
- **Duration is the intersection of video composition coverage and the edit list** — not the audio
  track duration and not the container duration. A long audio track cannot inflate video duration
- Emits `video_start_seconds`, locating real content start after a leading empty edit
- File modified during inspection → judged `invalid`
- Bounded: caps of `20000` boxes and `1000000` table entries, so malformed files cannot exhaust memory

---

## 📸 Image Generation

### Six slots, six distinct responsibilities

Every slot is bound to an explicit role contract and **roles must not bleed into each other** —
one image cannot try to be both a selling-point frame and a craftsmanship close-up:

| Slot | Role | Hard requirements |
|---|---|---|
| `main_image` | `overall_product` | Single complete product · pure white background RGB(255,255,255) · square composition |
| `detail_image_1` | `overall_selling_point` | Highlights design features visible in the source image |
| `detail_image_2` | `craftsmanship` | Visible stitching / edges / construction close-up, detail occupying 60–80% of frame |
| `detail_image_3` | `material_appearance` | Surface texture and drape close-up, 70–85% of frame |
| `detail_image_4` | `lifestyle` | Real indoor or outdoor everyday scene, **not** a white-background cutout |
| `detail_image_5` | `complete_overview` | Complete uncropped view; **no** collages, no invented back side |

### Model chains

| Target | Fallback chain |
|---|---|
| Main image | `qwen-image-3.0-pro` → `wan2.7-image-pro` → `wan2.7-image` |
| Detail images | `wan2.7-image-pro` → `wan2.7-image` → `qwen-image-3.0-pro` |

Up to three candidates per slot, advancing the model on each failure. Endpoints are probed in the
order `multimodal-generation` → `text2image/image-synthesis`, switching only on `400/404/405/422` —
a task-already-accepted error propagates immediately rather than being retried pointlessly.

### White background is measured, not assumed

White background is **measured**, not **trusted**: `WHITE_BG_NEAR = 245`, white-pixel ratio must be
≥ `0.9`, sampled from a band covering the outer 5% of the image. A "white background" image with a
dark backdrop will not pass. JPEG has no alpha channel, so its white-background status is always
`unknown` and it lands under a `.needs_review` suffix instead of the canonical filename.

### Aesthetic critic

`aesthetic_critic` scores every candidate on four dimensions (background cleanliness, product
fidelity, aesthetic appeal, artifact-free) on a 0–10 scale. It **compares against the source
reference image and never reads the generated image** — it judges "does this match the product",
not "does this look good".

Rejection gate:

| Condition | Verdict |
|---|---|
| Total `< 26` | Retry |
| Any dimension `< 5` | Retry |
| Role mismatch | Retry |
| No reference image | Forced downgrade to `unknown` |

Any `failed` check rejects the candidate outright; any `unknown` result writes the file under a
`.needs_review` suffix and **never** lets it impersonate a canonical artifact.

---

## 🎬 Video Generation

### Local model selection, no blind re-submission

The video path differs from the image path in one decisive way: **the model is chosen locally
before submission, and a failure stops the run**. Re-submitting the same clip burns credits and may
bill twice.

```
wan2.7-i2v-2026-04-25  (image-to-video, source product image as first frame)
        ↓ capability mismatch
happyhorse-1.1-r2v     (reference-driven)
        ↓ capability mismatch
happyhorse-1.1-t2v     (text-to-video, requires explicit allow_unreferenced_video=True)
```

Exactly **one** generation POST per run (`submission_count_limit: 1`).

### Five-shot storyboard

`hook → problem → product → proof → CTA`, with separate time boundaries for 30s and 15s.
Under a 300-second budget it automatically degrades to the 15s variant.

| Variant | Shot boundaries (seconds) |
|---|---|
| 30s | `0 · 3 · 8 · 20 · 25 · 30` |
| 15s | `0 · 2 · 4 · 10 · 13 · 15` |

`creative_plan` further compiles the storyboard into a frame-exact EDL (720 frames for 30s) and
reserves hold-back regions on the subtitle track so captions never cover key frames.

### Motion prompt discipline

Every shot prompt enforces three constraints: **the reference image is authoritative** (no pivoting
to unseen sides), **no added text / watermarks / price graphics**, and **subtle camera movement only**.

### Subtitles

Subtitles are sidecar files only and are **never burned into the picture**. Only cues verified
against a measured timeline are accepted, capped at 10. BGM is a constant declaration whose status
is permanently `not_generated` — the agent does not pretend to have produced music.

---

## ✍️ Copy Generation

Three languages, each with its own localized section headings: **English (US) / Korean (KR) /
Brazilian Portuguese (BR)**. An English heading does **not** satisfy the Korean section requirement.

### Fixed six sections

`Key Features` → `Product Information` → `Size Chart` → `Source Information` → `Image Guide` → `Video`

### Schema

| Field | Constraint |
|---|---|
| `title` | ≤128 characters |
| `bullets` | 5–7 items, each ≤60 characters, no duplicates |
| `keywords` | 8–12 items, no duplicates |
| Structure | All four fields present; duplicate keys, NaN, and nested objects rejected |

### Fact audit

| Check | Trigger |
|---|---|
| Source platform / offer_id / URL not reproduced exactly in Source Information | Fact mismatch |
| Quoted source SKU JSON block not byte-identical | Quoted data in doubt |
| Any URL absent from the source | Unknown URL |
| Any number in the text absent from source evidence or source size labels | Unsupported number |
| A claim word hit without verbatim source evidence | Unverified claim |
| A material word lacking source evidence, or evidence containing a negation | Material pending review |
| International size-equivalence conversion present | Size conversion pending review |
| Residual Chinese, or cross-language mixing between the three languages | Language purity |

Any `facts:` or `language:` issue triggers a source-template fallback rewrite.
Even when every mechanical check passes, the status stays `needs_review` —
**a machine can verify facts, but native fluency and semantic sense require a human.**

---

## 🗂 Category and Attribute Mapping

| Source | Size | Purpose |
|---|---|---|
| `clothing_attributes.json` | **66** attribute-bearing leaf categories | Semantic mapping candidate set |
| `clothing_categories.json` | **3546** leaf categories | Category-tree traversal |

### Three-tier attribute mapping

Tried in ascending cost order; anything resolved deterministically never reaches a model:

```
1. Deterministic alias match (zero model calls)
   Exact / substring matching against Chinese aliases
        ↓ miss
2. Batch LLM mapping (one call covers all attributes)
        ↓ miss
3. Per-attribute LLM mapping (legacy fallback)
```

Deterministic results take precedence on `attrId` conflicts.

### Where "never invent" is enforced

- Returned categories are forced to come from the library; a missing leaf raises rather than
  approximately matching
- `attrId` absent from the library → dropped; `valueId` absent from its enumeration → dropped
- Sales-attribute values must hit the enumeration whitelist, or the whole attribute is abandoned
- Free text is accepted only for attributes the library defines no enumeration for (`customized`)
- Brand and certification are absent from the libraries entirely, so they are **structurally**
  impossible to "map" into existence

---

## 🖥 Material Workbench

`frontend/workbench.html` is a dependency-free single-file workbench for review and demos:

- Product selector · asset lightbox · thumbnail strip
- Built-in rendering for the three listings, rejecting payloads over 1 MB
- Language filter (All / EN / KO / PT) and asset-type filter (images / video / copy)
- Per-asset download and full-text copy
- Hash routing (`#cover` / `#work` / `#work/video`) with working back/forward

Preview servers:

```bash
python3 -m http.server 18765 --bind 127.0.0.1 --directory frontend
python3 tools/preview_server.py --port 18766    # Range-capable, scrubbable video
```

---

## 📁 Project Structure

```
cross-border-material-agent/
├── agent/                      # submission package root
│   ├── agent.py                # entry: --prompt / --version / --plan-only / --audit
│   ├── agent.json              # {"runtime":"python","version":"1.1.0"}
│   ├── requirements.txt        # standard library only, zero dependencies
│   └── src/
│       ├── runtime_policy.py   # authorization, request budget, hard deadline, redaction
│       ├── input_parse.py      # --prompt parsing + product/category/attribute loading
│       ├── creative_plan.py    # offline creative compiler (storyboard/EDL/subs/fact ledger)
│       ├── planning.py         # offline plan packaging + external plan validation
│       ├── style_router.py     # product signal analysis + cross-market style profile
│       ├── category_map.py     # leaf category selection + three-tier attribute mapping
│       ├── copy_gen.py         # three-language copy + fact audit
│       ├── image_gen.py        # six-slot image generation + background/format validation
│       ├── aesthetic_critic.py # four-dimension visual review + rejection gate
│       ├── video_gen.py        # video generation + storyboard + subtitles
│       ├── media_probe.py      # standard-library MP4 structural validation
│       ├── strategy.py         # strategy document
│       ├── prompts.py          # prompt templates
│       ├── dsapi.py            # DashScope / OpenAI-compatible clients
│       ├── budget.py           # time budget guard + structured logging
│       └── assemble.py         # artifact validation + listing.json + quality report
├── tests/                      # 183 offline regression tests
├── frontend/                   # material workbench
├── tools/                      # film finishing, Range-capable preview server
├── scripts/                    # film build, vendor runner, deployment services
├── docs/                       # SOP, prompt specs, task specification
├── research/                   # 20 research reports
├── audit/                      # adversarial audit findings and resolutions
└── deploy/                     # systemd unit + HTTPS proxy
```

---

## 🧪 Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'   # 183 tests, ~16s
python3 tests/mock_e2e.py                               # sealed full-pipeline rehearsal
python3 tests/build_offline_evidence.py                 # rebuild offline evidence
```

| Test file | Coverage |
|---|---|
| `test_copy_quality.py` | Copy schema, fact consistency, three-language purity, no model call on budget exhaustion |
| `test_image_quality.py` | Six-slot role contracts, critic thresholds, dark-background rejection, malformed PNG, fallback paths off by default |
| `test_video_quality.py` | media_probe full matrix + local model selection, single POST, subtitle evidence binding |
| `test_creative_plan.py` | EDL frame ranges, frame provenance, forged-provenance rejection, subtitle hold-back |
| `test_runtime_quality.py` | Fail-closed before network, budget and deadline, input parsing edges, redaction |
| `test_studio_finish.py` | Local ffmpeg finishing (skipped unless `ffmpeg` / `ffprobe` are present) |

The entire suite runs offline and consumes no model credits.

---

## 📄 License

MIT License. Research outputs are synthesized from publicly available sources.
