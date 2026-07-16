# Viral Remake Workflow

Use this workflow when a user provides a viral product video, competitor ad, or asks to recreate a popular structure ("爆款复刻").

## Goal

Recreate the selling structure and pacing of a successful video without copying protected creative elements verbatim. Keep the user's product, target market, and reference images as the source of truth.

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
4. Use the user's optimized 3-image reference pack or create one first with `product-reference-workflow.md`.
5. Adapt language and setting to the target market.

## Prompt Template

Use the same 8-field AI video prompt format required by `SKILL.md`:

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

Create multiple remakes by varying:

- Hook: problem, curiosity, transformation, gift, social proof.
- Setting: bedroom, kitchen, desk, car, outdoor, store, party.
- User: student, parent, couple, renter, office worker, beauty user, pet owner.
- Camera: POV hand demo, close-up detail, before/after room reveal, quick reaction.

## Validation

Before returning results, state what was copied structurally and what was changed:

- Structural match: pacing, shot type, hook style, demo style.
- Product-specific changes: setting, action, language, buyer, benefit.
- Compliance: no subtitles/text if forbidden, no unrelated branding, product remains consistent.
