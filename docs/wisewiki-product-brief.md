# wisewiki Product Brief

## Positioning

`wisewiki` is local session memory for AI-assisted coding. It turns coding conversations into browsable, trustworthy project knowledge.

## Who It Is For

- Solo developers who use Claude Code or Cursor heavily
- Developers who repeatedly lose context between coding sessions
- Developers who want human-visible session output, not just hidden AI memory

## Core Value

After a coding session ends, the developer should be able to open `wisewiki` and immediately see:

- what the AI actually learned
- which conclusions are trustworthy
- which modules were touched
- which questions remain open

## Product Principles

1. Prefer fewer high-signal claims over many weak captures.
2. Tie knowledge back to source files whenever possible.
3. Make session output human-visible through HTML first.
4. Keep graph views lightweight and filtered.
5. Preserve local-first storage and inspectability.

## Current Product Shape

The current runtime publishes:

- module pages
- a session recap page
- a session-centric repo home
- a lightweight graph view

This keeps `wisewiki` differentiated from generic memory tools and generic documentation generators.
