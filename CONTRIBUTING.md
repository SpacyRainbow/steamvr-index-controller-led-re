# Contributing

This is a research journal as much as it is a codebase — contributions are
welcome, but the bar is "does this help the next reverse engineer," not
"does this look polished."

## Ways to contribute

- **Verify an unconfirmed claim.** Several findings in this repository are
  explicitly marked as unconfirmed or user-reported rather than
  independently verified (e.g., the charging/pairing color mappings in
  [`docs/09_led_policy.md`](docs/09_led_policy.md)). Confirming or correcting one of these with
  direct evidence is exactly as valuable as a new discovery.
- **Continue the open research.** [`docs/18_future_work.md`](docs/18_future_work.md) is a
  prioritized, concrete task list — each item explains why it matters and
  what's already been tried.
- **Report a dead end.** If you try something and it doesn't work,
  that's still worth documenting — see [`docs/14_failed_attempts.md`](docs/14_failed_attempts.md) for
  the format this project uses (what was tried, why it seemed reasonable,
  why it failed, what was learned, whether it's worth retrying). Don't
  quietly drop a failed experiment; add it.
- **Test against different hardware or firmware.** Every live finding in
  this project was verified against exactly one controller unit and
  primarily one firmware build ([`hashes/firmware_hashes.txt`](hashes/firmware_hashes.txt)). Confirming
  (or finding a discrepancy in) any of this project's claims against a
  different unit or build is high-value — see [`docs/17_safety.md`](docs/17_safety.md)
  "Version compatibility warnings" first.
- **Fix a documentation bug.** Broken cross-references, unclear
  explanations, or claims that turn out to be wrong — see the
  "Corrected assumptions" section at the top of [`docs/14_failed_attempts.md`](docs/14_failed_attempts.md)
  for how this project prefers wrong claims to be handled: corrected in
  place, with the correction itself preserved and explained, not silently
  edited away.

## Ground rules

- **No Valve firmware binaries, ever.** This repository documents how to
  obtain firmware yourself and verifies it by SHA-256 hash
  ([`hashes/firmware_hashes.txt`](hashes/firmware_hashes.txt)); it does not and must not include the
  files themselves. If you're contributing a new patch, provide it as a
  generator script (see [`patches/README.md`](patches/README.md) for the pattern) or an
  `xdelta3` diff against the documented hash, never a full firmware image.
- **Distinguish proven facts from hypotheses.** This repository's stated
  style ([`docs/01_project_overview.md`](docs/01_project_overview.md)) uses explicit confidence levels
  (100%, 95%, 70%, etc.) and separates "proven," "evidence-supported,"
  and "hypothesis." Match that style — don't state something as fact
  because it seems likely.
- **Preserve history, don't rewrite it.** If a new finding corrects an
  earlier document, prefer adding a visible correction (see the pattern in
  [`docs/14_failed_attempts.md`](docs/14_failed_attempts.md)) over silently editing the original claim
  away. The point of a research journal is that you can see how
  understanding changed, not just where it landed.
- **Cite your evidence.** Every claim in this repository is expected to
  point at *why* it's believed — a specific experiment, a specific
  disassembly finding, a specific log line. If you add a claim, add its
  evidence in the same edit.
- **Live hardware experiments are inherently risky.** If your
  contribution involves flashing firmware to real hardware, read
  [`docs/17_safety.md`](docs/17_safety.md) first, and be explicit in your write-up about what
  hardware you tested against and what your own risk tolerance was (this
  project's own hands-on work was performed against hardware the
  researcher explicitly considered expendable — don't assume that risk
  tolerance applies to your own hardware without deciding that for
  yourself).

## Style notes

- Markdown files use real, relative links (`[text](path)`), not just
  backtick-styled path mentions — see any recent `docs/` file for the
  pattern. (This wasn't always true in this repository's own history; see
  the relevant daily log entry for when and why this was fixed.)
- New scripts should follow the pattern in [`scripts/README.md`](scripts/README.md): a purpose,
  requirements, usage example, expected output, and limitations, either in
  the script's own docstring or in [`scripts/README.md`](scripts/README.md) directly.
- New experiments should follow the format in [`docs/13_experiments.md`](docs/13_experiments.md):
  Goal, Background, Reasoning, Method, Expected result, Actual result,
  Evidence, Conclusion, Confidence, Repeatability, Recommendation.

## Running the automated tests

```bash
python3 -m unittest discover -s tests -v
```

See [`tests/README.md`](tests/README.md) for what is and isn't covered, and why.

## Questions

Open an issue on the repository. For anything you'd rather not raise
publicly (e.g., a security concern per [`SECURITY.md`](SECURITY.md)), note that in the
issue and a maintainer will follow up privately.
