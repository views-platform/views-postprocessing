"""A dated tripwire for the platform key expiry (register C-84, issue #224).

**What this is not.** C-84 considered a key-validity preflight and rejected it: *"this
is a date to act on, not a mechanism to build, and inventing a mechanism would be
building the wrong thing to feel busy."* That verdict stands, and this is not that.
There is no authenticated call here, no credential, and no network — only a calendar.

**What this is.** C-84's trigger reads *"act when the un_fao delivery is next scheduled
within a month of it, or when anyone plans a rotation, whichever is first."* That is a
trigger nobody can notice: it fires in someone's memory or not at all, and this
repository has written down more than once that a trigger nobody can notice is a wish
(ADR-014 §4; the third arm of C-94's trigger was withdrawn for exactly this). The date
is known 90 days in advance and the consequence is a total, foreseeable outage of every
identity on the seam. So the trigger is made to fire on its own.

**Why the date is declared here rather than read from anywhere.** It cannot be derived:
the coordinate registry records secret *slots*, never values or their lifetimes, which
is #224's closing observation — no amount of drift detection will surface this one. The
values below come from an operator console read on 2026-08-05, recorded in views-appwrite
registry v1.4.4 and in C-84.

**When this fails, there are exactly two honest responses**, and both are stated in the
failure: rotate the keys and update the dates below, or — if a key was replaced early —
update the dates below to the new expiry. Deleting the test is the third option and it
is the one that produces the outage.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

#: The platform keys this repository's deliveries authenticate with, and when they die.
#: Read from the operator console 2026-08-05 (þing-02 A3(i)); recorded in views-appwrite
#: coordinate registry v1.4.4 and in register C-84. Both of this repo's paths — the FAO
#: delivery and the CRAF'd delivery — run under `VIEWS Pipeline Core`, the earlier one.
#: Naive datetimes, deliberately: the console reports local time and the window here is
#: 30 days, so an hour of timezone either way changes nothing. Do not add tzinfo to make
#: it look rigorous — it would imply a precision the source does not have.
KEY_EXPIRY: dict[str, datetime] = {
    "VIEWS Pipeline Core": datetime(2026, 11, 17, 12, 35),
    "UN FAO": datetime(2026, 11, 17, 16, 10),
}

#: How long before the earliest expiry this starts failing. A month, because that is the
#: window C-84's own trigger names, and because rotation needs an overlap period that
#: has to be scheduled with an operator rather than squeezed in on the day.
LEAD_DAYS = 30


def days_until_earliest_expiry(today: date) -> tuple[str, int]:
    """(which key dies first, how many days until it does) — a pure function of a date.

    Split out so the FAILING branch below can be exercised in the suite. A tripwire
    whose firing path has never run is unproven however carefully it was written
    (register C-102), and this one would otherwise first execute in October, live, on
    the day it matters.
    """
    name = min(KEY_EXPIRY, key=lambda k: KEY_EXPIRY[k])
    return name, (KEY_EXPIRY[name].date() - today).days


def expiry_warning(name: str, days_left: int) -> str:
    """What the tripwire says when it fires. Separate so it can be read without waiting."""
    spread = max(KEY_EXPIRY.values()) - min(KEY_EXPIRY.values())
    listing = "\n".join(
        f"    {key:22} {when:%Y-%m-%d %H:%M}"
        for key, when in sorted(KEY_EXPIRY.items(), key=lambda kv: kv[1])
    )
    return (
        f"the platform Appwrite keys expire in {days_left} days:\n{listing}\n\n"
        f"Both of this repository's delivery paths — un_fao and crafd — authenticate "
        f"with {name!r}, the earlier one. The two keys are {spread} apart, which is not "
        "a stagger: neither can carry traffic while the other is replaced, so a rotation "
        "that assumes a window has none. After the later time every identity on the seam "
        "is dead at once — model and ensemble writes, both partner deliveries, and FAO's "
        "own read access.\n\n"
        "This repository cannot rotate anything and must not hold credentials "
        "(þing-01 D3). Issuing and installing keys is an operator console action "
        "(views-appwrite#12); the key split is views-faoapi#338.\n\n"
        "Two honest ways to make this pass: rotate, then update KEY_EXPIRY; or, if a key "
        "was replaced early, update KEY_EXPIRY to the new expiry. Deleting this test is "
        "the third way and it is the one that produces the outage "
        "(register C-84, issue #224)."
    )


def test_the_platform_keys_are_not_about_to_expire():
    """Fails 30 days out, so the date cannot pass unnoticed (C-84, #224)."""
    name, days_left = days_until_earliest_expiry(date.today())
    if days_left > LEAD_DAYS:
        return
    pytest.fail(expiry_warning(name, days_left))


def test_the_tripwire_actually_fires_inside_the_lead_window():
    """The failing branch, exercised now rather than first executing in October.

    C-102: a guard that has never run is unproven, however carefully it was written.
    """
    name, days_left = days_until_earliest_expiry(date(2026, 10, 25))
    assert name == "VIEWS Pipeline Core", "the earlier key is the one both paths use"
    assert days_left == 23
    assert days_left <= LEAD_DAYS, (
        f"a date 23 days out must be inside the lead window, and LEAD_DAYS is "
        f"{LEAD_DAYS}. Shrinking it is how this tripwire gets quietly neutered — "
        "the window is C-84's own, and rotation needs an overlap period scheduled "
        "with an operator rather than squeezed in on the day."
    )
    message = expiry_warning(name, days_left)
    assert "expire in 23 days" in message
    assert "3:35:00 apart" in message, "the gap is C-84's finding, not the dates"
    assert "not a stagger" in message
    assert "views-appwrite#12" in message, "the reader must be told who can act"
    assert "Deleting this test" in message, (
        "the third option must be named, or it is the one that gets taken quietly"
    )


def test_the_tripwire_is_silent_outside_the_lead_window():
    _, days_left = days_until_earliest_expiry(date(2026, 1, 1))
    assert days_left > LEAD_DAYS, "a tripwire that is always red is a tripwire nobody reads"


def test_the_recorded_expiries_are_the_ones_C_84_names():
    """The dates are load-bearing, so a typo must fail here rather than silently.

    A tripwire keyed to a date nobody re-checked is worth very little; this pins the
    two values against the entry that sourced them, so editing one without the other
    is a failure rather than a drift.
    """
    assert KEY_EXPIRY["VIEWS Pipeline Core"] == datetime(2026, 11, 17, 12, 35)
    assert KEY_EXPIRY["UN FAO"] == datetime(2026, 11, 17, 16, 10)
    gap = KEY_EXPIRY["UN FAO"] - KEY_EXPIRY["VIEWS Pipeline Core"]
    assert gap.total_seconds() == 3 * 3600 + 35 * 60, (
        "C-84's finding is the 3h35m gap, not the dates themselves — if these move, "
        "re-read the entry rather than adjusting the constant to match"
    )
