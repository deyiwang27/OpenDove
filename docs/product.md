# Product

## Product Statement

OpenDove is an AI-native software delivery system that orchestrates coding assistants such as Claude Code, Codex, and Gemini through a structured process for specification, planning, implementation, integration, and validation.

Its purpose is to reduce human coordination work while keeping delivery aligned with user intent.

## Initial Users

The first target users are:

- solo technical builders who already use AI coding tools heavily
- startup teams that want more autonomy without losing control
- engineering teams experimenting with AI-assisted workflows and looking for stronger process guarantees

These users already believe in AI-assisted development. They are not asking whether AI should write code. They are asking how to make AI-driven delivery more reliable and less supervision-heavy.

## User Problem

AI coding tools help with implementation, but the overall workflow still breaks down because:

- the original goal is underspecified or forgotten
- work drifts as it moves across stages
- test evidence is weak or misleading
- integration quality is assumed instead of verified
- humans are forced to manually coordinate each step

OpenDove is designed to close that gap.

## v1 Product Promise

Give OpenDove a scoped engineering goal, and it will manage the delivery loop through spec, planning, design, implementation, integration review, and validation, escalating to humans only when intent is unclear, the task exceeds policy limits, or a final decision cannot be made safely.

## Product Scope For v1

The first version should focus on one bounded flow:

- one scoped engineering task at a time
- one orchestrated path through the core roles
- one persistent task record with state and artifacts
- one blocking validation decision before completion
- one explicit escalation path back to humans

This is enough to prove the core thesis without overbuilding.

## What Makes OpenDove Different

- It is built around alignment, not just code generation.
- It treats validation as a hard gate, not a suggestion.
- It uses coding assistants as execution engines inside a larger system.
- It aims to reduce coordination overhead, not only implementation effort.

## What OpenDove Is Not

- not another standalone coding assistant
- not a thin wrapper around existing models
- not multi-agent theater with no hard decision rules
- not full autonomy at the expense of trust

## Success Criteria For The First Product Phase

The first product phase should prove that OpenDove can:

- reduce the amount of manual orchestration required to complete a scoped task
- keep implementation aligned with the original intent and stated success criteria
- reject incomplete or misleading outputs consistently
- escalate uncertainty instead of pretending confidence

## Product Principle

Humans should define intent, constraints, and policy. OpenDove should handle the rest by default.
