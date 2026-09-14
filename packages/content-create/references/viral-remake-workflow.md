# Reference-based Video Generation

Use this video-generation workflow when a user wants to adapt a reference video’s script, shots, pacing, or selling structure to their own product. Requests for 爆款复刻 or segment-by-segment redrawing and merging belong to lingtu-video-remake.

## Goal

Recreate the selling structure and pacing of a successful video without copying protected creative elements verbatim. Keep the user's product, target market, and reference images as the source of truth.

## Source video inputs

Accept any of these as the source to analyze, then remake:

- Public URL: **TikTok, Douyin (抖音), Xiaohongshu (小红书), WeChat Channels (视频号), YouTube, or Instagram** (full or short share links, e.g. `v.douyin.com`, `xhslink.com`, `channels.weixin.qq.com`).
- Local video file or already-uploaded Lingtu material/file.

When the user pastes a link (including 抖音 / 小红书 / 视频号), first read `../../video-understand/references/api.md`, then run `python3 ../video-understand/scripts/lingtu_video_understand.py replicate --url ...` to obtain the replication prompt / structure brief. Do not scrape the page yourself. Use that brief as the Analysis Pass input below, then generate remake videos via `scripts/lingtu_content_task.py`.

For a local file use `replicate --file ./source.mp4`; for an uploaded material use `replicate --business-id <id> --business-type MATERIAL`. Reuse an existing analysis brief when available. Script paths are relative to the Skill root.

Before generation, read `../SKILL.md` for generation parameters, polling/recovery and result handling, and `api.md` for the API contract. Use these as helper documentation within this remake workflow.

## Analysis Pass

Before generating, summarize the source video into reusable structure:

- Product category and likely buyer.
- Hook in the first 1-2 seconds.
- Scene sequence and shot count.
- Demonstrated problem, transformation, or benefit.
- Camera style: handheld, close-up, POV, home demo, unboxing, reaction, before/after.
- Audio style: voiceover, dialogue, ambient sound, music, no audio.
- Text/subtitle usage, if any.
- Final call-to-action style, if requested.

Do not copy exact spoken lines, brand names, faces, logos, or unique identifiable creative assets unless the user owns them and explicitly asks.

## Remake Planning

Translate the viral structure into the user's product:

1. Map the hook to the user's strongest selling point.
2. Replace scenes with realistic product use cases.
3. Keep one clear action per 10-second variant.
4. Use the user's available product images in the supplied order; do not require a three-image pack or automatically generate reference images first.
5. Adapt language and setting to the target market.

## Prompt Template

For Wan (`wan3.0-video`), read `wan-prompt-guide.md` and use its reference-media or multi-shot formula. Check the effective model before writing the prompt; if not explicitly specified, run `python3 scripts/lingtu_content_task.py --kind video --show-default-model`.

For other video models, use the 8-field template below:

```text
Video style:
[Vertical realistic phone video / UGC handheld / close-up demo — inspired by hook -> demo -> result]

Scene:
[Target-market setting with one clear product action; no copied logos or competitor branding]

Camera:
[Handheld / POV / close-up detail — match the remake plan, not the source shot-for-shot]

Tone & pacing:
[Fast hook in 1-2s, one clear benefit beat, natural ending]

Character:
[Optional: one realistic user type matching the target market; omit if product-only]

Spoken script:
[Optional short voiceover/dialogue in the target language; do not copy source lines]

Audio:
[Ambient / soft music / voiceover only — as planned]

Overall feeling:
[Authentic remake of the selling structure, not a frame copy; no on-screen text unless requested]
```

## Variants

Default to one remake (`--nums 1`). Only create multiple outputs when the user requests them, varying:

- Hook: problem, curiosity, transformation, gift, social proof.
- Setting: bedroom, kitchen, desk, car, outdoor, store, party.
- User: student, parent, couple, renter, office worker, beauty user, pet owner.
- Camera: POV hand demo, close-up detail, before/after room reveal, quick reaction.

## Validation

Before returning results, state what was copied structurally and what was changed:

- Structural match: pacing, shot type, hook style, demo style.
- Product-specific changes: setting, action, language, buyer, benefit.
- Compliance: no subtitles/text if forbidden, no unrelated branding, product remains consistent.
