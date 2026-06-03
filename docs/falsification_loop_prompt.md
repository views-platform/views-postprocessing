# Falsification Campaign Loop Prompt

Copy the block below and paste it as a `/loop` prompt in Claude Code.
It processes one claim at a time from `docs/falsification_campaign.md`.

---

## Loop Prompt

```
Read docs/falsification_campaign.md. Find the first claim with status PENDING in the Progress Tracker.

If no PENDING claims remain, say "Campaign complete — all claims processed" and stop.

Otherwise, for the current claim:

CRITICAL: This is a READ-ONLY campaign. Do NOT modify mapping.py, unfao.py, or any source file. Do NOT modify existing tests. The ONLY files you may create or modify are: falsification test stub files (new), the risk register, CICs/ADRs (to correct documentation that misdescribes actual code behavior), and the progress tracker.

1. Run /falsify with the claim text (the content inside the ``` block under that claim heading). Follow the full falsification protocol: present probes, wait for confirmation, execute, classify, generate test stubs, report verdict.

2. After the /falsify verdict, immediately run /register-risk to register any findings from the falsification. Follow the full registration protocol: extract, deduplicate, assign tiers, append, report.

3. Update the Progress Tracker row for this claim in docs/falsification_campaign.md:
   - Set Status to the /falsify verdict (SURVIVED, CONTESTED, or FALSIFIED)
   - Set Round to 1
   - Set Findings to a short summary (e.g., "2H/1S" for 2 hard + 1 soft, or "clean" for SURVIVED)
   - Set Date to today

4. Do NOT fix source code. Do NOT re-run the claim. Do NOT enter a fix-and-reaudit loop. Register the findings, update the tracker, and STOP this iteration. The next loop invocation will pick up the next PENDING claim.

5. Report what was found and what the verdict was.

Important:
- Process ONE claim per loop iteration
- NEVER modify source code (mapping.py, unfao.py, __init__.py, conftest.py, test_mapping.py, test_validation.py)
- Always present probes and wait for user confirmation before executing
- Always register risks after the falsification
- Always update the progress tracker
- The claim text is inside the ``` code block under each claim heading in falsification_campaign.md
- "Fix" means: register finding + write test stub + update docs to match reality. NOT change source code.
```
