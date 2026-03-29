"""
Prompt templates for the adaptive analysis pipeline.

Each module exports a SYSTEM_PROMPT constant and a build_*_prompt() function
that assembles the user-turn from structured evidence. All prompts instruct the
model to respond with a single valid JSON object — no markdown fences, no prose.
"""
