# Session Memory Deletion Reference

## Validated pattern

When removing several entries that were written in one session:

1. Separate entries by store (`user` versus `memory`).
2. For each store, send one batch with `operations`.
3. Give every operation an explicit `action: remove` and a unique `old_text` selector.
4. Verify the returned `success`, `target`, and `entry_count`/`usage`.

Example shape:

```json
{
  "operations": [
    {"action": "remove", "old_text": "unique text from entry A"},
    {"action": "remove", "old_text": "unique text from entry B"}
  ],
  "target": "memory"
}
```

Repeat the batch with `target: user` for user-store entries; do not mix stores in one batch.

## Failure lesson captured from this session

A call containing only `target` was rejected with `Unknown action 'None'. Use: add, replace, remove`. The correct response was not to retry the same shape or to treat the tool as a reader. Stop, construct an explicit remove batch, and verify its success result. In the validated correction, the user-store batch reported zero remaining entries and the operational-memory batch reported the pre-existing entries still present after two requested entries were removed.

## Scope rule

“Delete what was written this session” means remove only the entries attributable to that session. Preserve older entries and state that preservation only when the verification output supports it.
