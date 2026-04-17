# Session Prompt Generator

Last updated: 2026-04-16
Status: Active workflow standard

## Goal

At the end of every session, leave behind a ready-to-paste prompt for the next AI session.

This removes restart friction and makes handoffs deterministic.

## Rule

Every session must end with an updated `.tmp/codex_handoff.md` that includes:

- current project state
- exact next move
- a copy-paste prompt for the next session

## Source Of Truth

Use `.tmp/codex_handoff.md` as the primary live handoff file.

If a feature has its own implementation spec, that spec may also include a handoff block, but the cross-session restart prompt must still be reflected in `.tmp/codex_handoff.md`.

## Required Handoff Sections

The handoff file should contain these sections:

1. `## Active Goal`
2. `## Current State`
3. `## What Was Fixed This Session`
4. `## Recommended Next Steps`
5. `## Next Session Prompt`
6. `## Constraint Reminder`

## Prompt Template

Use this template in `## Next Session Prompt` and replace placeholders with the real task.

```text
Read d:/Web App/Converter/.tmp/codex_handoff.md first.

Then continue the next highest-priority task for ConvertFlow.

Current objective:
[insert current objective]

Exact next move:
[insert the next concrete implementation step]

Files to read first:
[file 1]
[file 2]
[file 3]

Constraints:
- Follow AGENTS.md instructions in d:/Web App/Converter
- Prefer existing execution/ tools and directives before inventing new scripts
- Do not rewrite unrelated parts of the app
- Do not claim proprietary copying; frame work as local-first implementation, UX parity, and workflow upgrade

Before stopping:
- update d:/Web App/Converter/.tmp/codex_handoff.md
- include what changed, what remains, and the next session prompt
```

## How To Generate The Next Prompt

At the end of the session:

1. Identify the single highest-priority next action
2. Name the exact files the next AI should open first
3. Write the prompt so it starts with the handoff file
4. Keep it specific enough that the next session can begin without re-discovery

## Good Prompt Characteristics

- starts from the handoff file
- names one concrete next move
- points to exact files
- preserves important constraints
- tells the next AI to refresh the handoff before stopping

## Bad Prompt Characteristics

- vague goals like "keep working"
- no file references
- no priority order
- no constraints
- no required end-of-session update

## Session Close Checklist

Before ending any session:

- update `.tmp/codex_handoff.md`
- refresh `## Recommended Next Steps`
- replace `## Next Session Prompt` with a current prompt
- make sure the prompt names the next concrete action, not just a broad goal

## Default Fallback Prompt

If there is no active spec and no better next step is known, use:

```text
Read d:/Web App/Converter/.tmp/codex_handoff.md first.
Then inspect the highest-priority unfinished item referenced there and continue from that point.
Follow AGENTS.md instructions, prefer existing execution/ tools, avoid unrelated refactors, and update the handoff again before stopping.
```
