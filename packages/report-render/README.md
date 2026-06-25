# lingtu-report-render

Turns structured JSON (or just a few fields) from any Lingtu skill into a shareable PNG long-image.

See [`SKILL.md`](./SKILL.md) for invocation rules, modes, and the full schema.

## Quick start

```bash
pip install playwright
playwright install chromium

# Fill mode — no AI, no key needed:
python3 scripts/lingtu_report_render.py \
  --template daily_report \
  --data '{"title":"今日小报","summary":"一切正常"}'

# AI mode (after backend is wired up):
python3 ../../shared/scripts/user_keys.py single bind
python3 scripts/lingtu_report_render.py \
  --template daily_report \
  --mode ai \
  --data daily.json
```

The output PNG path is printed to stdout as JSON.
