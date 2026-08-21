"""A dated tripwire for the platform key expiry (register C-84, issue #224).

**What this is not.** C-84 considered a key-validity preflight and rejected it: *"this is
a date to act on, not a mechanism to build, and inventing a mechanism would be building
the wrong thing to feel busy."* That verdict stands. There is no authenticated call here,
no credential, no network — only a calendar.

**What this is.** C-84's trigger reads *"act when the un_fao delivery is next scheduled
within a month of it"*. That is a trigger nobody can notice: it fires in someone's memory
or not at all, which ADR-014 §4 forbids and which withdrew the third arm of C-94's
trigger. The date is known 90 days ahead and the consequence is a total outage of every
identity on the seam, so the trigger is made to fire on its own.

**The acknowledgement is the load-bearing part, and the first draft did not have it.**
A gate that goes red on a date, cannot be cleared from inside the repository, and blocks
every unrelated pull request is a gate that gets deleted — `pyproject.toml` says exactly
that about ruff, citing ADR-014 §3. Rotation is an operator console action this repo
cannot perform, so without an in-repo escape the tripwire would hold the merge queue
hostage from 2026-10-18 until someone with console access acted. ``ACKNOWLEDGED_UNTIL``
is that escape: a declared date that says *we have seen this and will act by then*. It is
a deliberate, reviewed, dated edit — and it **cannot be set past the expiry**, so it can
postpone attention but never replace it.

**There is deliberately no test pinning these datetimes to literals.** The first draft had
one, and it made the remediation the tripwire itself prescribes — *rotate, then update
``KEY_EXPIRY``* — fail a second test whose message said not to adjust the constant. A
guard that refuses its own documented fix is worse than no guard, and it would have landed
on the one person who could not route around it.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

#: The platform keys this repository's deliveries authenticate with, and when they die.
#: Read from the operator console 2026-08-05 (þing-02 A3(i)); recorded in views-appwrite
#: coordinate registry v1.4.4 and in register C-84. Both of this repo's paths — the FAO
#: delivery and the CRAF'd delivery — run under `VIEWS Pipeline Core`, the earlier one.
#:
#: Naive datetimes, deliberately: the console reports local time and the window below is
#: 30 days, so an hour either way changes nothing. Adding tzinfo would imply a precision
#: the source does not have.
KEY_EXPIRY: dict[str, datetime] = {
    "VIEWS Pipeline Core": datetime(2026, 11, 17, 12, 35),
    "UN FAO": datetime(2026, 11, 17, 16, 10),
}

#: How long before the earliest expiry this starts failing. C-84's own window, and the
#: time a rotation needs to be scheduled with an operator rather than squeezed in.
LEAD_DAYS = 30

#: Set to a date to silence the tripwire until then — *"seen, and being acted on"*.
#: Must be before the expiry (asserted below), so it postpones attention rather than
#: removing it. ``None`` means unacknowledged.
ACKNOWLEDGED_UNTIL: date | None = None


def days_until_earliest_expiry(today: date) -> tuple[str, int]:
    """(which key dies first, days until it does) — a pure function of a date.

    Split out so the FAILING branch can be exercised in the suite. A tripwire whose
    firing path has never run is unproven however carefully it was written (C-102), and
    this one would otherwise first execute live in October, on the day it matters.
    """
    name = min(KEY_EXPIRY, key=lambda k: KEY_EXPIRY[k])
    return name, (KEY_EXPIRY[name].date() - today).days


def expiry_warning(name: str, days_left: int) -> str:
    """What the tripwire says when it fires."""
    spread = max(KEY_EXPIRY.values()) - min(KEY_EXPIRY.values())
    hours, remainder = divmod(int(spread.total_seconds()), 3600)
    gap = f"{hours}h{remainder // 60:02d}m"
    when = (
        f"in {days_left} days" if days_left > 0
        else "TODAY" if days_left == 0
        else f"{-days_left} days ago — the seam is already dead"
    )
    listing = "\n".join(
        f"    {key:22} {stamp:%Y-%m-%d %H:%M}"
        for key, stamp in sorted(KEY_EXPIRY.items(), key=lambda kv: kv[1])
    )
    return (
        f"the platform Appwrite keys expire {when}:\n{listing}\n\n"
        f"Both of this repository's delivery paths — un_fao and crafd — authenticate with "
        f"{name!r}, the earlier one. The two keys are {gap} apart, which is not a stagger: "
        "neither can carry traffic while the other is replaced, so a rotation that assumes "
        "a window has none. After the later time every identity on the seam is dead at "
        "once — model and ensemble writes, both partner deliveries, and FAO's own read "
        "access.\n\n"
        "This repository cannot rotate anything and must not hold credentials "
        "(þing-01 D3). Issuing and installing keys is an operator console action "
        "(views-appwrite#12); the key split is views-faoapi#338.\n\n"
        "THREE ways to make this pass, in order of preference:\n"
        "  1. rotate the keys, then update KEY_EXPIRY to the new expiries;\n"
        "  2. if a key was replaced early, update KEY_EXPIRY to match;\n"
        "  3. set ACKNOWLEDGED_UNTIL to a date before the expiry — this says the rotation "
        "is scheduled and stops the tripwire blocking unrelated work until then.\n"
        "Deleting this test is the fourth way and it is the one that produces the outage "
        "(register C-84, issue #224)."
    )


def test_the_platform_keys_are_not_about_to_expire():
    """Fails inside the lead window unless the date is explicitly acknowledged."""
    today = date.today()
    name, days_left = days_until_earliest_expiry(today)
    if days_left > LEAD_DAYS:
        return
    if ACKNOWLEDGED_UNTIL is not None and today <= ACKNOWLEDGED_UNTIL:
        return
    pytest.fail(expiry_warning(name, days_left))


def test_an_acknowledgement_cannot_outlive_the_expiry():
    """The escape hatch postpones attention; it must not be able to remove it.

    An open-ended acknowledgement is just the deletion in finding 4's clothing, and it
    would read as a live guard while being none.
    """
    if ACKNOWLEDGED_UNTIL is None:
        return
    earliest = min(KEY_EXPIRY.values()).date()
    assert ACKNOWLEDGED_UNTIL < earliest, (
        f"ACKNOWLEDGED_UNTIL is {ACKNOWLEDGED_UNTIL}, on or after the earliest expiry "
        f"({earliest}). An acknowledgement that outlives the thing it acknowledges is a "
        "silent deletion — the suite would stay green straight through the outage."
    )


def test_the_tripwire_actually_fires_inside_the_lead_window():
    """The failing branch, exercised now rather than first executing in October (C-102).

    The probe date is DERIVED from `KEY_EXPIRY`, so this keeps proving something after a
    rotation. Hardcoding it — as the first draft did — meant the proof quietly expired
    the moment the constant was legitimately updated.
    """
    earliest = min(KEY_EXPIRY.values()).date()
    probe = earliest - timedelta(days=LEAD_DAYS - 7)
    name, days_left = days_until_earliest_expiry(probe)

    assert name == "VIEWS Pipeline Core", "the earlier key is the one both paths use"
    assert 0 < days_left <= LEAD_DAYS, "the probe must sit inside the window it tests"

    message = expiry_warning(name, days_left)
    assert f"expire in {days_left} days" in message
    assert "3h35m apart" in message, "the gap is C-84's finding, not the dates"
    assert "not a stagger" in message
    assert "views-appwrite#12" in message, "the reader must be told who can act"
    assert "ACKNOWLEDGED_UNTIL" in message, "and how to clear it without deleting it"
    assert "Deleting this test" in message, (
        "the last option must be named, or it is the one that gets taken quietly"
    )


def test_the_tripwire_is_silent_outside_the_lead_window():
    earliest = min(KEY_EXPIRY.values()).date()
    _, days_left = days_until_earliest_expiry(earliest - timedelta(days=LEAD_DAYS + 60))
    assert days_left > LEAD_DAYS, "a tripwire that is always red is one nobody reads"


def test_the_lead_window_is_not_quietly_shrunk():
    """Shaving days off `LEAD_DAYS` neuters this without deleting anything.

    A floor rather than an equality: widening the window is always safe, and pinning the
    exact value would recreate the problem the removed literal-pin caused.
    """
    assert LEAD_DAYS >= 30, (
        f"LEAD_DAYS is {LEAD_DAYS}. C-84's window is a month, and rotation needs an "
        "overlap period scheduled with an operator — shortening the warning is how a "
        "dated guard gets neutered while still looking present."
    )


def test_the_outage_day_message_still_reads(tmp_path):
    """The text an operator reads while the seam is down must not say '-3 days'."""
    earliest = min(KEY_EXPIRY.values()).date()
    for probe, expected in ((earliest, "TODAY"), (earliest + timedelta(days=3), "3 days ago")):
        name, days_left = days_until_earliest_expiry(probe)
        assert expected in expiry_warning(name, days_left)
