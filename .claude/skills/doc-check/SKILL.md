---
name: doc-check
description: Run the mechanical checks on the AI documentation - size budgets, the every-request context budget, broken links, index agreement, symbols the docs name that the code does not have, and staleness. Use after editing AI-MD/, .github/copilot-instructions.md or CLAUDE.md, and whenever asked whether the docs are still in good shape.
---

# Checking the AI docs

```bash
python3 .claude/skills/doc-check/check.py
```

A few hundred milliseconds — a walk of the source tree for the dead-symbol check, plus a couple of
git calls per doc. Exit code 1 on any failure; warnings alone don't fail the run.

**It reports, it does not fix.** Several violations need a judgment call — which file a fact
belongs in, whether a table-shaped doc should stay long — and those are not decisions to automate.

## When to run it

After editing anything in `AI-MD/`, `.github/copilot-instructions.md` or `CLAUDE.md`.

This is the *mechanical* pass only. It is deliberately **not** a prompt to re-verify every doc
against the code — see "The three triggers" in the hub for why.

## What it checks

| Check | Rule |
|---|---|
| Prose size | ≤ 10 KB per `AI-MD/` file, **excluding tables and fenced code** |
| Hub size | **fails** over 25 KB of prose; **warns** on raw bytes past 95% of it |
| Context budget | always **reports** the every-request total; **warns** past 40 KB |
| Line length | ≤ 600 characters |
| Source paths | every code path named in a doc must exist |
| Cross-links | every `AI-MD/*.md` reference **and** every `[[wiki-link]]` must resolve |
| Indexes | hub ↔ `AI-MD/README.md` ↔ filesystem must agree **both ways** |
| Dead symbols | **warns** on any `` `name()` `` the source tree doesn't have, and on any such mention that doesn't read as history |
| Staleness | **warns** when `Last verified` is over 90 days old |
| Re-verification | **warns** when a doc changed after its `Last verified` date (git-aware) |
| Code drift | **warns**, naming the commits, when the code a doc's `Source:` line covers changed more than `CODE_DRIFT_DAYS` after it was verified |

**Source-path checking adapts to the repo.** A path is only checked when its first segment is a
real directory here — so `lib/…dart` gets checked in a Flutter project, `src/…ts` in a JS one, and
a path rooted somewhere that doesn't exist is left alone. Nothing to configure.

## The hub is charged prose, and warned on raw

Two numbers, because they answer different questions. Prose is what a writer can actually shorten,
so prose is what may fail a run. Raw bytes are what Copilot loads on every request, so that stays
on screen as a warning you can't act on by rewriting.

Charging the hub raw size — as this did until 2026-09-09 — priced a table row and a paragraph the
same. A table row carries far more per token, so the pressure fell on exactly the wrong thing: the
first casualty in the first project to hit the limit was five rows of an architecture map.

## The context budget is the one number worth watching

Every run prints what loads into context on **every** request: the global `~/.claude/CLAUDE.md`,
this repo's `CLAUDE.md` and `CLAUDE.local.md`, the hub, and `AGENTS.md`. It warns past
`CONTEXT_MAX` (40 KB, roughly 10k tokens).

Printed whether or not it breaches, because a total nobody sees is a cost nobody steers by. The
global file matters most and was watched by nothing at all before this: it loads in every project
on the machine, so a paragraph added there is paid for everywhere. It gets the same 10 KB prose
budget a subsystem doc gets.

What the budget pushes you toward is right: `AI-MD/` loads only when something asks for it, so
moving detail there costs nothing per request.

## Dead symbols are derived from the code, not remembered

Every `` `name()` `` in the docs is checked against a walk of the source tree. Anything absent gets
a warning naming it. That closes the leak every hand-maintained list has, which is that it catches
only what somebody remembered to add — in the project this was rewritten for, the docs named five
functions that no longer existed and the list held four of them.

`DEAD_SYMBOLS` still exists and still matters. Adding a name acknowledges one the walk has already
found, so it stops asking; and it is the only way to cover what a function-shaped pattern cannot
see at all — types, classes, constants, config keys.

**Everything here is a warning, never a failure.** Whether a mention is a false claim or an honest
"this was removed" can only be settled by reading the sentence, and `NEGATIONS` is a list of
substrings guessing at that. It will always be incomplete, so nothing that fails a run may rest on
it. Adding a phrase to quiet a warning is fine; adding one to unbreak a build is not.

## Code drift reads the `Source:` line — there is no second field to maintain

Every `AI-MD/` doc opens with a sentence naming the code it covers. The drift check takes the
backticked paths out of it, asks git when any of them last changed, and warns when that is more than
`CODE_DRIFT_DAYS` (7) after the doc's `Last verified` date. A doc with no `Source:` line gets a
warning of its own, because otherwise it would be silently exempt.

**It names the commits.** Re-reading a whole doc against a whole subsystem is a twenty-minute job;
reading four commit subjects and deciding whether any could have made the doc false is a two-minute
one. Same signal, a fraction of the cost.

The grace period is the rest of the design. Without it the check fires the morning after any commit
and becomes noise you learn to scroll past; a week is long enough for ordinary work to settle and
short enough to catch real rot. It is one constant at the top of `check.py`.

## Keeping it current

Two lists at the top of `check.py` are meant to grow with the project:

- **`DEAD_SYMBOLS`** — see above. Add a name when the derived check asks, or when you delete a
  type or constant the docs still mention.
- **`PATH_EXCEPTIONS`** — add a path when a doc legitimately names a file that isn't there: one
  documented as deleted, an SDK path, or a placeholder inside a command example.

This copy belongs to this project. It was stamped from a template and is not kept in sync with it;
edit it here freely.

## Why these particular checks

Each corresponds to a failure that actually happened:

- **Dead symbols** — three separate docs documented a `setCustomForegroundHandler` API that had
  never existed, in six copies. Nothing caught it because nothing looked.
- **Broken links and index drift** — a planning doc was indexed nowhere and referenced nowhere for
  months.
- **Size** — a hub reached 82 KB, and one paragraph reached 5,670 characters.
- **Staleness** — a `Status: Current` line rots silently. A date doesn't.
- **Code drift** — one re-read against the code found thirteen false statements across four docs,
  every one introduced by a commit somewhere else. Every other check passed the whole time,
  because none of them looked at the code.
- **Context budget** — a hub sat at 99% of a limit measured the wrong way, and the fix applied
  under that pressure deleted table rows, which are the cheapest form in the file.

## Three honest limits

1. **It only catches what it is pointed at.** Nothing runs it unasked unless this repo wires it
   into a lint script. Remembering to run it is on the person.
2. **It cannot tell you a doc is *wrong*.** Every check here is structural. A confidently worded,
   entirely false paragraph passes all of them — that is what the `Last verified` date and a real
   read of the code are for. The code-drift check narrows this but does not close it: it knows the
   covered code moved, never whether the move mattered.
3. **Code drift cannot tell a rewrite from a rename.** A sweep touching every screen — adding a
   shared component, say — dates every doc whose `Source:` line names `app/`, and each has to be
   dismissed by hand. Cheap to dismiss, and the alternative is a heuristic that would miss real
   changes; but expect a burst of these after any repo-wide edit.

## Known-good exceptions

<!-- Record anything that trips a check but is correct as-is, and why. For example:
     table-heavy docs that exceed 10 KB on disk still pass, because the budget measures prose —
     splitting a lookup table across files makes it worse. -->
