#!/usr/bin/env python3
"""Mechanical checks on the AI documentation. Reports violations; fixes nothing.

Run from the repo root:  python3 .claude/skills/doc-check/check.py
Exit code 1 if anything failed (warnings alone do not fail the run).

This copy belongs to this project. Fill in PATH_EXCEPTIONS and DEAD_SYMBOLS below
as the repo earns them; both are meant to grow.
"""
import io, os, re, sys, glob, datetime, subprocess

HUB = '.github/copilot-instructions.md'
README = 'AI-MD/README.md'
GLOBAL_RULES = os.path.expanduser('~/.claude/CLAUDE.md')
PROSE_MAX, HUB_MAX, PARA_MAX, STALE_DAYS = 10240, 25600, 600, 90
CODE_DRIFT_DAYS = 7  # grace before covered code moving ahead of a doc is worth saying
HUB_WARN_AT = 0.95  # warn once the hub's RAW size passes this share of HUB_MAX
CONTEXT_MAX = 40960  # every-request context: warn past this, in bytes
DRIFT_COMMITS = 5  # how many commit subjects to name before saying "and N more"

# Source paths the docs may name that legitimately don't exist:
# files documented as deleted, SDK paths, placeholders inside command examples.
PATH_EXCEPTIONS = {
}
# Symbols the docs may name that are NOT in the code — the record of what you
# have deliberately deleted. It does two jobs. Adding a name here acknowledges a
# function the source-tree walk below has already spotted, so it stops asking;
# and it is the ONLY way to cover what a `name()` pattern cannot see at all —
# types, classes, constants, config keys.
DEAD_SYMBOLS = [
]
# Phrases that mark a mention of a dead symbol as history rather than a claim.
# Only a WARNING depends on this list, deliberately: it is a substring heuristic
# and will always be incomplete, so nothing that fails a run may rest on it.
NEGATIONS = ('not exist', 'never exist', 'no longer', 'none of', 'removed',
             "don't go looking", 'dead code', 'zero callers', 'fiction',
             'outdated', 'made moot', 'deleted', 'invented', 'wrong',
             'does not', 'no such', 'there is no', 'and no ', 'not a route',
             'never once', 'no callers', 'never fire', 'stale', 'what went',
             'withdrawn', 'never built', 'was built')

# One extension list, used both to decide whether a path named in a doc is a
# source path worth resolving and to walk the tree for identifiers.
SRC_EXT = ('dart', 'ts', 'tsx', 'js', 'jsx', 'mjs', 'py', 'go', 'rs', 'java',
           'kt', 'kts', 'rb', 'php', 'cs', 'swift', 'c', 'h', 'cc', 'cpp',
           'hpp', 'm', 'mm', 'sh', 'sql')
SKIP_DIRS = {'node_modules', 'build', 'dist', 'vendor', 'target', 'archived',
             '__pycache__', 'coverage', 'out'}

# A source path is checked only when its first segment is a real directory here,
# so one rule covers lib/ in a Flutter repo, src/ in a JS one, and neither elsewhere.
SRC_RE = re.compile(
    r'\b([a-z][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_.-]+)+\.(?:' + '|'.join(SRC_EXT) + r'))\b')

fail, warn, note = [], [], []
def bad(m): fail.append(m)
def soft(m): warn.append(m)
def say(m): note.append(m)
def read(p): return io.open(p, encoding='utf-8').read()

def prose_bytes(path):
    """Size excluding fenced code blocks and table rows."""
    n, incode = 0, False
    for line in io.open(path, encoding='utf-8'):
        if line.startswith('```'):
            incode = not incode; continue
        if incode or line.startswith('|'):
            continue
        n += len(line.encode('utf-8'))
    return n

docs = sorted(glob.glob('AI-MD/*.md'))
if not docs:
    print("nothing to check: AI-MD/*.md matched no files here")
    sys.exit(0)
has_hub = os.path.exists(HUB)
if not has_hub:
    soft(f"{HUB}: missing — hub size and index checks skipped")
prose_files = docs + ([HUB] if has_hub else [])

# 1. prose budget
for f in docs:
    n = prose_bytes(f)
    if n > PROSE_MAX:
        bad(f"{f}: {n} bytes of prose (limit {PROSE_MAX}) — split it by topic")

# 2. hub budget: prose fails, raw warns.
#
# The two numbers answer different questions and both are worth having. Prose is
# what a writer can actually shorten, so that is what may fail a run. Raw bytes
# are what Copilot loads on every request, so that stays on screen as a warning.
#
# Charging the hub raw size — as this did until 2026-09-09 — priced a table row
# and a paragraph the same, and a table row carries far more per token. The first
# thing that pressure deleted was five rows of an architecture map.
if has_hub:
    n = prose_bytes(HUB)
    if n > HUB_MAX:
        bad(f"{HUB}: {n} bytes of prose (limit {HUB_MAX}) — move detail into AI-MD/")
    raw = os.path.getsize(HUB)
    if raw > HUB_MAX * HUB_WARN_AT:
        pct = round(raw * 100 / HUB_MAX)
        soft(f"{HUB}: {raw} bytes on disk — {pct}% of {HUB_MAX}; every byte loads on "
             f"every request, tables included")

# 3. paragraph budget
for f in prose_files:
    incode = False
    for i, line in enumerate(io.open(f, encoding='utf-8'), 1):
        if line.startswith('```'): incode = not incode; continue
        if incode or line.startswith('|'): continue
        if len(line.rstrip('\n')) > PARA_MAX:
            bad(f"{f}:{i}: paragraph is {len(line.rstrip())} chars (limit {PARA_MAX})")

# 4. source paths resolve
for f in prose_files:
    s = read(f)
    for p in sorted(set(SRC_RE.findall(s))):
        if p in PATH_EXCEPTIONS or not os.path.isdir(p.split('/')[0]):
            continue
        if not os.path.exists(p):
            bad(f"{f}: names a file that does not exist -> {p}")

# 5. cross-links resolve, in both the path form and the [[wiki]] form.
# The wiki form is the one the AI-MD docs actually use, and a typo in it used to
# fail silently forever because nothing looked at it.
for f in prose_files + ['CLAUDE.md']:
    if not os.path.exists(f): continue
    s = read(f)
    for link in sorted(set(re.findall(r'AI-MD/[A-Za-z0-9_]+\.md', s))):
        if not os.path.exists(link):
            bad(f"{f}: broken link -> {link}")
    for name in sorted(set(re.findall(r'\[\[([A-Za-z0-9_-]+)\]\]', s))):
        if not os.path.exists(f'AI-MD/{name}.md'):
            bad(f"{f}: broken wiki-link -> [[{name}]] (no AI-MD/{name}.md)")

# 6. indexes agree in both directions
hub_s = read(HUB) if has_hub else None
rd_s = read(README) if os.path.exists(README) else None
if rd_s is None:
    soft(f"{README}: missing — index agreement checked against the hub only")
for f in docs:
    b = os.path.basename(f)
    if b == 'README.md': continue
    if hub_s is not None and b not in hub_s:
        bad(f"{b}: exists but is not in the hub index")
    if rd_s is not None and b not in rd_s:
        bad(f"{b}: exists but is not in {README}")
if rd_s is not None:
    for listed in sorted(set(re.findall(r'`([A-Za-z0-9_]+\.md)`', rd_s))):
        if listed != 'README.md' and not os.path.exists('AI-MD/' + listed):
            bad(f"{README} indexes a file that does not exist -> {listed}")

# 7. symbols the docs name that the code does not have.
#
# Two halves. The derived half walks the source tree and asks whether each
# `name()` in the docs is an identifier anywhere in it — that closes the leak a
# hand-maintained list always has, which is that it catches only what somebody
# remembered to add. The DEAD_SYMBOLS half covers what a function-shaped pattern
# cannot see at all: types, classes, constants.
#
# Both report WARNINGS. Whether a mention is a false claim or an honest "this was
# removed" can only be judged by reading the sentence, and NEGATIONS is a
# substring guess at that. A guess may raise a warning; it may not fail a run.

def source_identifiers():
    """Every identifier in the repo's source files, as one set."""
    words = set()
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in files:
            if f.rsplit('.', 1)[-1] not in SRC_EXT:
                continue
            try:
                words |= set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*',
                                        read(os.path.join(root, f))))
            except (OSError, UnicodeDecodeError):
                pass
    return words

doc_fns = set()
for f in prose_files:
    doc_fns |= set(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)\(\)`', read(f)))
in_code = source_identifiers() if doc_fns else set()
unrecorded = sorted(s for s in doc_fns if s not in in_code and s not in DEAD_SYMBOLS)
for s in unrecorded:
    soft(f"'{s}()' is named in the docs and is not in the code — fix the doc, or add "
         f"it to DEAD_SYMBOLS so this stops asking")

gone = set(DEAD_SYMBOLS) | set(unrecorded)
for f in prose_files:
    L = read(f).split('\n')
    for i, line in enumerate(L, 1):
        for sym in gone:
            if sym not in line:
                continue
            window = ' '.join(L[max(0, i-3):i+3]).lower()
            if not any(x in window for x in NEGATIONS):
                soft(f"{f}:{i}: '{sym}' is not in the code and this does not read as "
                     f"history — check the sentence")

# 8. staleness (warnings, not failures)
#
# Three questions, because they fail differently:
#   a. has this doc gone stale on the calendar?  -> the 90-day rule
#   b. was it edited without being re-verified?  -> compare against git
#   c. did the CODE IT COVERS move on without it? -> compare its Source: line
# (b) catches a falsehood introduced in an edit; (c) catches one introduced by
# an edit somewhere else entirely, which is the commoner way a doc goes wrong
# and the way nothing here used to look for. (a) never fires for a doc that is
# being actively changed.
#
# (c) has a grace period because it would otherwise fire the morning after any
# commit and become noise. A week is long enough for ordinary work to settle.
# It also NAMES THE COMMITS, so the re-read is scoped to a diff rather than to a
# whole subsystem — a two-minute job instead of a twenty-minute one.

def git(*args):
    """Run a git command, returning stdout, or None if git could not answer."""
    try:
        r = subprocess.run(['git', *args], capture_output=True, text=True, timeout=5)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def last_change_date(*paths):
    """Newest change date across `paths`: today if any has uncommitted edits,
    else the last commit date touching any of them. Returns None outside a git
    repo, or when git knows none of them."""
    if not paths:
        return None
    dirty = git('status', '--porcelain', '--', *paths)
    if dirty is None:
        return None
    if dirty.strip():
        return datetime.date.today()
    out = git('log', '-1', '--format=%cs', '--', *paths)
    if not out or not out.strip():
        return None
    try:
        return datetime.date.fromisoformat(out.strip())
    except ValueError:
        return None


def commits_since(date, paths):
    """Subjects of the commits touching `paths` since `date`, newest first."""
    out = git('log', '--oneline', '--no-merges', f'--since={date.isoformat()}',
              '--', *paths)
    return [l for l in (out or '').split('\n') if l.strip()]


def covered_paths(text):
    """The code a doc says it covers, read off its own `Source:` sentence —
    every backticked token there that looks like a path and is really on disk.
    No new field to maintain: every AI-MD doc already opens with that line."""
    m = re.search(r'\bSource:((?:.|\n)*?)(?:\n\s*\n|\Z)', text)
    if not m:
        return []
    seen = []
    for tok in re.findall(r'`([^`]+)`', m.group(1)):
        tok = tok.strip().rstrip('.,;')
        # A path has a slash or an extension. Requiring the slash alone drops
        # every root-level file, `next.config.ts` among them. Existing on disk
        # is what rejects the symbol names that share the line — `pickFefo`,
        # `stockRows` — and the `[[wikilinks]]` beside them.
        if ('/' in tok or '.' in tok) and os.path.exists(tok) and tok not in seen:
            seen.append(tok)
    return seen

today = datetime.date.today()
for f in docs:
    if os.path.basename(f) == 'README.md': continue
    body = read(f)
    m = re.search(r'\*\*Last verified:\*\*\s*(\d{4})-(\d{2})-(\d{2})', body)
    if not m:
        soft(f"{f}: no 'Last verified' header")
        continue
    verified = datetime.date(*map(int, m.groups()))

    age = (today - verified).days
    if age > STALE_DAYS:
        soft(f"{f}: last verified {age} days ago — re-check it against the code")

    changed = last_change_date(f)
    if changed and changed > verified:
        soft(f"{f}: changed {changed}, verified {verified} — re-read it against the "
             f"code, then update 'Last verified'")

    covers = covered_paths(body)
    if not covers:
        soft(f"{f}: no 'Source:' line naming the code it covers — drift not checked")
        continue
    moved = last_change_date(*covers)
    if moved and (moved - verified).days > CODE_DRIFT_DAYS:
        log = commits_since(verified, covers)
        shown = '; '.join(l.split(' ', 1)[-1] for l in log[:DRIFT_COMMITS])
        more = f" (+{len(log) - DRIFT_COMMITS} more)" if len(log) > DRIFT_COMMITS else ""
        tail = f" — read: {shown}{more}" if shown else ""
        soft(f"{f}: covers code last changed {moved}, verified {verified} — "
             f"{(moved - verified).days} days behind{tail}")

# 9. what loads on every request, always reported.
#
# The hub had a budget and the files beside it had none, including the global
# rules file, which loads in EVERY project on this machine and was watched by
# nothing at all. A total nobody can see is a cost nobody steers by, so this
# prints whether or not it breaches.
ctx = [p for p in (GLOBAL_RULES, 'CLAUDE.md', 'CLAUDE.local.md', HUB, 'AGENTS.md')
       if os.path.exists(p)]
if ctx:
    total = sum(os.path.getsize(p) for p in ctx)
    label = lambda p: '~/CLAUDE.md' if p == GLOBAL_RULES else os.path.basename(p)
    parts = ', '.join(f"{label(p)} {os.path.getsize(p)}" for p in ctx)
    say(f"every-request context: {total} bytes ≈ {round(total / 4000)}k tokens "
        f"({parts})")
    if total > CONTEXT_MAX:
        soft(f"every-request context is {total} bytes (limit {CONTEXT_MAX}) — move "
             f"detail into AI-MD/, which loads only when it is asked for")
if os.path.exists(GLOBAL_RULES):
    n = prose_bytes(GLOBAL_RULES)
    if n > PROSE_MAX:
        soft(f"{GLOBAL_RULES}: {n} bytes of prose (limit {PROSE_MAX}) — it loads in "
             f"every project on this machine")

for m in note: print(f"      {m}")
for m in warn: print(f"WARN  {m}")
for m in fail: print(f"FAIL  {m}")
print(f"\n{len(docs)} docs checked · {len(fail)} failures · {len(warn)} warnings")
sys.exit(1 if fail else 0)
