# Job State Schema

任务目录是恢复执行的唯一事实来源：

```text
remake-job/
├── manifest.json
├── transcript.json
├── segments/
├── generated/
├── normalized/
└── final/
```

`manifest.json` 的关键字段：

```json
{
  "schema_version": 1,
  "job_id": "remake-20260906-120000",
  "source": "/absolute/source.mp4",
  "source_duration": 61.2,
  "transcription": {
    "source": "json|srt|vtt|whisper|http",
    "path": "/absolute/remake-job/transcript.json"
  },
  "segments": [
    {
      "id": "segment-001",
      "start": 0.0,
      "end": 12.8,
      "duration": 12.8,
      "text": "对应文字",
      "source_clip": "/absolute/remake-job/segments/segment-001-muted.mp4",
      "status": "waiting_review",
      "attempts": [
        {
          "number": 1,
          "client_task_id": "a1b2c3d4",
          "schedule_id": "206...",
          "task_ids": ["206..."],
          "status": "completed",
          "output": "/absolute/remake-job/generated/segment-001-attempt-1.mp4",
          "review_note": null
        }
      ],
      "approved_attempt": null
    }
  ]
}
```

## 状态约束

- `cut_ready`：消音参考片段已准备，可首次生成。
- `generating`：已创建外部任务或正在轮询；只能使用原 ID 恢复。
- `waiting_review`：有完整结果，等待用户确认。
- `approved`：用户确认了一个具体 attempt。
- `rejected`：用户明确拒绝当前结果；只有显式 `regenerate` 才能创建新任务。
- `failed`：服务端明确返回失败；只有显式 `regenerate` 才能创建新任务。
- `skipped`：用户明确跳过。
- `merged`：该段已被纳入最终合成结果。

不得从 `generating` 自动进入新的 attempt。不得在 `approved` 后覆盖原批准版本。重新生成时保留所有历史 attempt。

## 合成约束

只有全部片段均为 `approved` 或 `skipped` 时允许合成。按片段原始顺序取每段 `approved_attempt` 指向的文件。合成成功后记录最终输出路径，但不删除任何原始片段或历史生成版本。

