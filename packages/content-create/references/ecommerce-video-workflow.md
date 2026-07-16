# Ecommerce Video Workflow

Use this workflow when the user asks for selling videos, UGC-style product videos, short product ads, target-market scripts, or multiple video variants.

## Inputs

Collect or infer:

- Product type and core selling points.
- Target market/country and language.
- Video count, duration, aspect ratio, resolution, and model.
- Whether subtitles, on-screen text, voiceover, product labels, or watermark are allowed.
- Reference images, ideally ordered as product main, selling-point/detail, lifestyle scene.

If the user asks for a current target market or audience and it could materially affect the script, check current marketplace/search context before writing prompts.

## Audience And Script Design

For each target market, convert the product into realistic use cases:

- Who buys it.
- Where it is used.
- What problem or mood it solves.
- What action proves the selling point in under 10 seconds.

For short ecommerce videos, avoid overloading the prompt. One video should usually contain:

- One product.
- One setting.
- One action.
- One short spoken line or voiceover if language is requested.

## Prompt Rules

- Keep prompts compact, especially for 10-second videos.
- Every AI video prompt must strictly use this exact field format and order: `Video style:`, `Scene:`, `Camera:`, `Tone & pacing:`, `Character:`, `Spoken script:`, `Audio:`, `Overall feeling:`.
- Do not add extra top-level prompt fields, bullet labels, or prose outside those eight fields when submitting the prompt to the API.
- Use the target-market language for dialogue or voiceover.
- If the user says no subtitles, explicitly include "No subtitles, no on-screen text."
- For realistic videos, specify handheld phone footage, real home/store lighting, authentic reaction, and no flashy effects.
- Avoid asking the model to show long product copy or exact text; video models often render text poorly.
- Preserve product identity by referencing the 3-image pack and keeping reference order stable.
- Use `gemini-omni-video` for 10-second videos when that is the confirmed model. Use `720x1280` for 9:16 720px vertical output.

## 10-Second Variant Pattern

Generate variants by changing scenario and buyer motivation, not by rewriting the same shot:

1. Bedroom or personal space transformation.
2. Couple, family, or gift use.
3. Desk, study, work, or daily routine.
4. Social proof or casual gathering.
5. Close product demo or key action.

## Prompt Template

```text
Video style:
10s vertical realistic iPhone-style handheld UGC video, 9:16, natural phone footage, no flashy effects.

Scene:
[Target market setting]. [Target user] uses one [product] to [single action / selling point]. [Visible realistic result].

Camera:
[Handheld phone camera behavior, framing, close-ups, movement, and what product details must stay visible.]

Tone & pacing:
[Authentic tone and pacing, usually quick hook, simple demo, natural reaction within 10 seconds.]

Character:
[Target user / creator description, outfit or lifestyle context, and how they interact with the product.]

Spoken script:
[Target-language spoken line or short voiceover. Keep it one sentence for 10-second videos.]

Audio:
[Natural room audio / casual voice / no music or subtle platform-native background music. Include subtitle/text restrictions here if needed.]

Overall feeling:
[The final impression: realistic, useful, everyday, trustworthy, not polished studio advertising.]
```

## Generation And Result Handling

Only submit separate tasks for different scripts when the user explicitly requests multiple videos or variants. For an ordinary request, submit one task with `--nums 1`, return the first completed video, and stop. If the current video task is pending or processing, keep polling that same task and do not create another task unless the API explicitly returns a failure status (FAILED, CANCELLED, EXPIRED, error). If a video task times out but remains pending, query the schedule id once more before reporting failure; video tasks may complete shortly after the polling deadline. A script crash or network error during polling does NOT mean the task failed — always re-poll the existing task/schedule first.

Download completed videos to a local output directory and return both local media embeds and useful remote URLs.

## Failure Handling

- If `veo3.1-lite-extend` / `veo3.1-extend` is requested for 10 seconds but those models only support 8 seconds, switch to a confirmed 10-second model such as `gemini-omni-video` or `seedance2.0-fast`.
- If a model returns `未知模型`, stop retrying that model name and ask for or use a confirmed model.
- If a provider fails with retry exhaustion, simplify the prompt: fewer people, one action, no complex camera moves, no exact text.
