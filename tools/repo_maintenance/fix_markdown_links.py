#!/usr/bin/env python3
"""Convert backtick-styled file-path mentions in this repo's Markdown docs
into real, correctly-relative clickable links, without touching backtick
spans that aren't actual file references (inline code, flags, etc.).

Why this exists: an early audit of this repository found it had over 200
cross-references between documents (e.g. `docs/17_safety.md` mentioned
inside another doc), and every single one was written as plain
backtick-styled text -- not one was an actual clickable Markdown link.
This script mechanically converts them, computing the correct relative
path from each referencing file's own location (the repo's authoring
convention writes paths as if relative to the repo root, which is NOT
what Markdown link resolution actually uses, so a naive find/replace would
have produced broken links from any file not sitting at the repo root).

Usage: python3 fix_markdown_links.py
  (run from anywhere -- it locates the repo root from its own path)

Idempotent: re-running after all links are already converted reports 0
conversions, since the pattern only matches bare backtick spans, not
existing `[`text`](path)` links.

After running, verify with a link-integrity check (walk every .md file,
confirm every [text](path) target exists on disk) before committing --
see docs/14_failed_attempts.md and the relevant daily log entry for the
audit that produced this script, which used exactly that verification
step before trusting the result.
"""
import os
import re

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# Build the set of all real files in the repo (relative to REPO root)
real_files = set()
for root, dirs, files in os.walk(REPO):
    if '.git' in root:
        continue
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, REPO)
        real_files.add(rel.replace(os.sep, '/'))

# candidate backtick-span pattern: `word/word...ext` possibly with a
# trailing §-anchor mentioned separately in prose (we don't try to link
# anchors, just files).
#
# The (?<!\[) / (?!\]\() guards are load-bearing, not decorative: without
# them this regex also matches the backtick span INSIDE an
# already-converted [`text`](path) link, and re-running the script wraps
# it again -- [[`text`](path)](path) -- silently, since that's still
# technically valid (if useless and eventually broken-looking) Markdown.
# This exact bug shipped once during this project's own repo-maintenance
# work and produced triple-nested broken links before being caught by a
# link-integrity check; see the relevant daily log entry. Do not remove
# these guards without adding an equivalent idempotency test first.
backtick_re = re.compile(
    r'(?<!\[)`((?:\.\./)*[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*\.(?:md|py|txt|java|c|xdelta3|sh))`(?!\]\()'
)

def resolve_target(current_dir, ref):
    """Given the ref text as written, and the directory the doc lives in,
    figure out which real repo file it means. Two conventions are used in
    this repo: repo-root-relative (e.g. 'docs/17_safety.md' written inside
    docs/ itself) and already-relative (e.g. '../../docs/x.md' from deep in
    research/). Try repo-root-relative first (matches actual authoring
    convention used throughout), then path-relative-to-current-dir."""
    candidates = []
    # strip any leading ../ the author may have already included
    stripped = ref
    while stripped.startswith('../'):
        stripped = stripped[3:]
    if stripped in real_files:
        candidates.append(stripped)
    # also try as literally relative to current_dir
    joined = os.path.normpath(os.path.join(current_dir, ref)).replace(os.sep, '/')
    if joined in real_files:
        candidates.append(joined)
    if not candidates:
        return None
    return candidates[0]

changed_files = {}
total_conversions = 0
unresolved = []

for root, dirs, files in os.walk(REPO):
    if '.git' in root:
        continue
    for f in files:
        if not f.endswith('.md'):
            continue
        full = os.path.join(root, f)
        rel_dir = os.path.relpath(root, REPO).replace(os.sep, '/')
        if rel_dir == '.':
            rel_dir = ''
        text = open(full, encoding='utf-8').read()

        def repl(m):
            global total_conversions
            ref = m.group(1)
            target_repo_rel = resolve_target(rel_dir, ref)
            if target_repo_rel is None:
                unresolved.append((full, ref))
                return m.group(0)
            # don't relink the file to itself pointlessly if identical
            target_full = os.path.join(REPO, target_repo_rel)
            link_path = os.path.relpath(target_full, root).replace(os.sep, '/')
            total_conversions += 1
            return f'[`{ref}`]({link_path})'

        new_text = backtick_re.sub(repl, text)
        if new_text != text:
            changed_files[full] = new_text

for path, content in changed_files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Converted {total_conversions} backtick references into real links across {len(changed_files)} files.")
if unresolved:
    print(f"{len(unresolved)} backtick spans looked like paths but didn't resolve to a real file (left untouched):")
    for path, ref in unresolved[:30]:
        print(f"  {path}: `{ref}`")
