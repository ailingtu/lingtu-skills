# Lingtu AI Agent Instructions

Use this repository when a user asks for Lingtu AI content generation, TK shop data analysis, or TikTok creator/competitor monitoring.

## Repository Source

- GitHub: https://github.com/ailingtu/lingtu-skills
- When the user asks to update Lingtu AI skills, pull the latest version from this repository.

## Available Packages

- `packages/content-create`: media generation, product reference images, ecommerce videos, and viral remake workflows.
- `packages/tkshop-query`: TK shop list lookup, daily reports, and shop operations analysis.
- `packages/tiktok-monitor`: TikTok creator/competitor monitoring with group-level lists, daily subscriptions, and yesterday-vs-today digest reports.
- `packages/video-understand`: video understanding for local files and TikTok/YouTube URLs — produces a natural-language replication prompt for remixing, tagging, or video breakdown.

## Shared Rules

- Require `LINGTU_API_KEY` in the process environment.
- Send the key as `x-api-key`.
- Read the package `references/api.md` before changing endpoint paths, request fields, response fields, or status handling.
- Prefer the package scripts over ad hoc API calls.
- Do not store customer API keys in this repository.

## Routing

Use `packages/content-create` for product images, image references, ecommerce videos, viral remakes, and media-generation tasks.

Use `packages/tkshop-query` for shop lists, daily reports, merchant/store metrics, and business-operation questions.

Use `packages/tiktok-monitor` for TikTok creator links, usernames, 达人/竞品监控, group-level monitoring lists, daily digest subscriptions, and yesterday-vs-today TikTok content reports.

Use `packages/video-understand` when the user asks to analyze, summarize, tag, break down, or 二创 a single video — local file, uploaded material, or TikTok/YouTube URL — and wants a replication prompt or content readout.
