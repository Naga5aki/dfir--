---
name: persistent-memory
description: Maintain durable memory safely and verify mutations.
version: 0.1.0
author: User, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memory, persistence, verification, housekeeping]
    related_skills: []
---

# Persistent Memory Skill

Maintain Hermes persistent memory as a small, high-signal knowledge base. This skill covers deciding what belongs in memory, writing it to the correct store, deleting only the requested entries, and verifying the post-mutation state. It does not replace session history for temporary progress, task logs, or one-off facts.

## When to Use

- The user asks to remember, save, record, update, replace, or forget a durable fact.
- The user asks to extract long-term lessons from a conversation and write them to memory.
- The user asks whether a memory deletion succeeded.
- A memory entry has become stale, duplicated, overly specific, or contradicted.

Don't use for:

- Temporary task progress or completed-work logs; use the current conversation or session history.
- Raw technical knowledge that is easy to look up and is not a stable user preference, environment fact, or reusable workflow.
- Editing skills; use the skill-management workflow instead.

## Memory Stores

- `target: user` stores stable facts about the person: preferences, role, communication style, and personal details.
- `target: memory` stores compact, stable facts about the operating environment and cross-task conventions, not task progress.
- Reusable workflows, procedures, troubleshooting lessons, and task-type preferences belong in the relevant skill, not either always-injected memory store.
- Treat the target as part of the data model. A correct sentence in the wrong store is still a bad mutation.

## Selection Rules

1. Prefer high-signal, future-useful facts that will remain valid beyond the current task.
2. Do not store task identifiers, transient state, completed-work logs, raw dumps, or facts likely to expire within a week.
3. Store workflow lessons in the relevant skill; store stable personal facts in `user` and stable operating-environment facts in `memory`. A preference specific to one task type belongs in that task's skill.
4. Compress related points into one entry when doing so preserves the decision rule and its caveats.
5. Before adding, check the supplied context and existing memory when available so the result is not a duplicate.

## Mutation Contract

Every `memory` call must use an explicit mutation shape:

- Add: `action: add`, `target`, and `content`.
- Replace: `action: replace`, `target`, `old_text`, and the complete replacement `content` (or the supported alias).
- Remove: `action: remove`, `target`, and a unique `old_text` substring.
- Batch: `operations`, where every operation explicitly contains its own `action`; keep the outer `target` consistent for all operations in that batch.

There is no read/list action in the memory tool. Do not probe memory by calling it with only `target`; that is an invalid mutation request. If the current memory contents are already present in context, use those entries as the deletion targets. Otherwise, ask for or use the supported memory-management interface rather than inventing a read shape.

## Procedure: Add or Update

1. Classify each candidate as `user` or `memory`; discard transient and easily retrievable material.
2. Normalize it into a compact declarative statement, not an instruction to the future agent.
3. Check for duplicates or stale wording in the available memory context.
4. Use one explicit mutation call. Batch independent additions or replacements atomically when they share a target.
5. Verify the tool result reports success, the intended target, and the expected entry count or usage change.
6. Report exactly what was saved without claiming more than the result proves.

Completion criterion: every retained fact has an explicit store, a concise declarative form, and a successful mutation result.

## Procedure: Delete or Forget

1. Define scope precisely: a named entry, all entries added in the current session, or a particular topic. Do not infer a broader deletion scope.
2. Build unique `old_text` selectors from the exact entry text or a distinctive phrase. Avoid selectors that could match unrelated entries.
3. Group deletions by target. Use one `operations` batch per target when multiple entries must be removed.
4. Make every operation explicit: `{"action":"remove","old_text":"..."}`.
5. Verify `success: true`, the target, and the reported count/usage. If the result is ambiguous, do not tell the user deletion succeeded.
6. Preserve unrelated pre-existing entries and report that preservation when it is relevant.

Completion criterion: every requested entry is covered by a successful remove operation, and no unrelated target was included.

## Procedure: Recovery from a Failed Mutation

1. Stop immediately after a schema error; do not repeat the same payload.
2. Inspect the error for a missing or invalid `action`, `target`, `old_text`, or `operations` shape.
3. Reissue a corrected explicit mutation, preferably as one atomic batch.
4. If a tool warning indicates repeated identical failures or a loop, stop further retries and change the request shape before continuing.
5. Verify the corrected result. Report any entries that could not be verified rather than converting the attempt into a success claim.

## Verification Checklist

- [ ] The requested scope is explicit.
- [ ] The store (`user` or `memory`) is correct.
- [ ] Every mutation has an explicit action.
- [ ] Remove selectors are unique and match only requested entries.
- [ ] Batch operations do not mix stores.
- [ ] The tool returned success before reporting completion.
- [ ] Unrelated memories were not removed.
- [ ] The response states the actual result, including any blocker.

## Pitfalls

- **Missing action:** `target` alone is not a read request; it produces an invalid mutation shape.
- **Blind retries:** repeated identical calls can create a tool-call loop and add no evidence.
- **Over-broad deletion:** “delete what I just added” means identify the entries added in this session, not wipe the entire memory store.
- **Wrong store:** user preferences and operational lessons have different homes; preserve that separation.
- **Premature confirmation:** an attempted call is not proof. Confirm the structured success result first.
- **Memory bloat:** keep durable notes compact; move detailed procedures to skills and session-specific details to references.

## Supporting Reference

See `references/session-memory-deletion.md` for the validated deletion pattern and the failure mode observed while correcting a multi-entry deletion request.
