"""
One-shot dataset builder. Run once to materialize the benchmark transcripts
and matching ground-truth labels under benchmark/transcripts/ and benchmark/labels/.

Each transcript has hand-authored ground truth for action items and decisions
(the two most objectively measurable extractor outputs). Topics, sentiment,
and summary are checked structurally via the post-extraction validator,
not against per-transcript ground truth (those judgments are too subjective
to label by hand at this scale).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent
TX = ROOT / "transcripts"
LB = ROOT / "labels"
TX.mkdir(exist_ok=True)
LB.mkdir(exist_ok=True)

DATASET = [
    {
        "id": "T01",
        "category": "standup",
        "meeting_date": "2026-05-14T09:30:00",
        "transcript": (
            "Alice: Quick standup. What did everyone do yesterday?\n"
            "Bob: Finished the login flow. Today I'll start on the password reset endpoint.\n"
            "Carol: I'm blocked on the design review. Need Alice to sign off by EOD.\n"
            "Alice: Got it, I'll review the mockups this morning.\n"
            "Dave: Shipping the migration script today."
        ),
        "action_items": [
            {"description": "Start work on the password reset endpoint", "assignee": "Bob"},
            {"description": "Sign off on the design review", "assignee": "Alice"},
            {"description": "Ship the migration script", "assignee": "Dave"},
        ],
        "decisions": [],
    },
    {
        "id": "T02",
        "category": "sprint_planning",
        "meeting_date": "2026-05-15T10:00:00",
        "transcript": (
            "Alice: Let's lock the sprint scope. We have two weeks.\n"
            "Bob: I propose we focus on payment integration and skip the analytics rebuild.\n"
            "Carol: Agreed, analytics can wait one more sprint.\n"
            "Alice: Decision: payment integration is in, analytics rebuild is out.\n"
            "Bob: I'll take the Stripe webhook work, due end of next week.\n"
            "Carol: I'll handle the checkout UI, also end of next week.\n"
            "Dave: I'll cover QA — full test plan by Wednesday."
        ),
        "action_items": [
            {"description": "Take the Stripe webhook work", "assignee": "Bob"},
            {"description": "Handle the checkout UI", "assignee": "Carol"},
            {"description": "Cover QA and produce a full test plan", "assignee": "Dave"},
        ],
        "decisions": [
            {"decision": "Payment integration is in scope; analytics rebuild is deferred"},
        ],
    },
    {
        "id": "T03",
        "category": "executive_review",
        "meeting_date": "2026-05-16T14:00:00",
        "transcript": (
            "CEO: Q1 revenue missed by 12%. We need to course-correct.\n"
            "VP_Sales: I'd push back on the targets — pipeline is healthy, just slower close cycles.\n"
            "CFO: Either way, we need to reduce burn. I propose freezing non-critical hiring.\n"
            "CEO: Agreed. Hiring freeze on everything except eng and sales until Q3.\n"
            "VP_Sales: I'll get you a revised forecast by Friday.\n"
            "CFO: I'll send the updated runway model tomorrow."
        ),
        "action_items": [
            {"description": "Deliver a revised sales forecast", "assignee": "VP_Sales"},
            {"description": "Send the updated runway model", "assignee": "CFO"},
        ],
        "decisions": [
            {"decision": "Hiring freeze on all teams except engineering and sales until Q3"},
        ],
    },
    {
        "id": "T04",
        "category": "brainstorm",
        "meeting_date": "2026-05-17T11:00:00",
        "transcript": (
            "Alice: Brainstorm time — onboarding ideas.\n"
            "Bob: What about a guided product tour?\n"
            "Carol: Or a checklist that unlocks features as you complete steps.\n"
            "Dave: We could do a Slack bot that nudges new users.\n"
            "Alice: All good options. Let's not decide today — Bob, can you write a one-pager comparing them by Monday?\n"
            "Bob: Sure, will do."
        ),
        "action_items": [
            {"description": "Write a one-pager comparing the onboarding options", "assignee": "Bob"},
        ],
        "decisions": [],
    },
    {
        "id": "T05",
        "category": "one_on_one",
        "meeting_date": "2026-05-18T15:00:00",
        "transcript": (
            "Manager: How are you feeling about the last sprint?\n"
            "Report: Honestly, a bit stretched. The on-call rotation plus the new project is heavy.\n"
            "Manager: That's fair. Let's reduce your project scope — drop the analytics dashboard for this cycle.\n"
            "Report: That would help, thank you.\n"
            "Manager: I'll talk to Dave about reassigning the dashboard work today."
        ),
        "action_items": [
            {"description": "Talk to Dave about reassigning the analytics dashboard work", "assignee": "Manager"},
        ],
        "decisions": [
            {"decision": "Drop the analytics dashboard from Report's scope for this cycle"},
        ],
    },
    {
        "id": "T06",
        "category": "conflict",
        "meeting_date": "2026-05-19T13:00:00",
        "transcript": (
            "Alice: We need to migrate to the new auth provider.\n"
            "Bob: I strongly disagree. Our current setup works and the migration risk is huge.\n"
            "Carol: I see Bob's point but our current provider is sunsetting next year.\n"
            "Alice: Right. We don't have a choice on the timeline. Decision: we migrate, starting Q3.\n"
            "Bob: Logged my objection. I'll still help with the migration plan.\n"
            "Alice: Bob, please draft the migration plan by next Friday.\n"
            "Carol: I'll handle the user-facing communication."
        ),
        "action_items": [
            {"description": "Draft the migration plan", "assignee": "Bob"},
            {"description": "Handle the user-facing communication", "assignee": "Carol"},
        ],
        "decisions": [
            {"decision": "Migrate to the new auth provider, starting in Q3"},
        ],
    },
    {
        "id": "T07",
        "category": "all_hands",
        "meeting_date": "2026-05-20T16:00:00",
        "transcript": (
            "CEO: Welcome everyone. Three announcements.\n"
            "CEO: First, we closed the Series B. Eighty million.\n"
            "CEO: Second, we're opening a London office in September.\n"
            "CEO: Third, we're rolling out a new performance review process — HR will share details.\n"
            "HR: Yes, I'll send the new review framework email tomorrow.\n"
            "Engineer: Will the London office include engineering roles?\n"
            "CEO: Yes, primarily engineering and product."
        ),
        "action_items": [
            {"description": "Send the new performance review framework email", "assignee": "HR"},
        ],
        "decisions": [
            {"decision": "Open a London office in September"},
        ],
    },
    {
        "id": "T08",
        "category": "brief",
        "meeting_date": "2026-05-21T09:00:00",
        "transcript": (
            "Alice: Just need a quick yes/no — should we delay the launch a week?\n"
            "Bob: Yes. The bug list is too long.\n"
            "Alice: OK, delayed by a week. I'll update the calendar."
        ),
        "action_items": [
            {"description": "Update the calendar for the delayed launch", "assignee": "Alice"},
        ],
        "decisions": [
            {"decision": "Delay the launch by one week"},
        ],
    },
    {
        "id": "T09",
        "category": "ambiguous",
        "meeting_date": "2026-05-22T10:00:00",
        "transcript": (
            "Alice: We should probably think about pricing at some point.\n"
            "Bob: Yeah, eventually. Not urgent.\n"
            "Carol: I might draft something next week if I have time."
        ),
        "action_items": [],
        "decisions": [],
    },
    {
        "id": "T10",
        "category": "multi_decision",
        "meeting_date": "2026-05-23T11:00:00",
        "transcript": (
            "Alice: Three things to decide today.\n"
            "Alice: One — the new logo. Bob, you've seen the options.\n"
            "Bob: I vote for option B.\n"
            "Carol: Same.\n"
            "Alice: Decision: logo B is approved.\n"
            "Alice: Two — annual offsite location. Lisbon or Mexico City?\n"
            "Dave: Lisbon. Easier visas for the EU team.\n"
            "Carol: Agreed.\n"
            "Alice: Decision: Lisbon.\n"
            "Alice: Three — should we acquire the Acme dataset for training?\n"
            "Bob: It's expensive. Let's negotiate first.\n"
            "Alice: OK, Bob, you lead negotiations and report back by next Thursday.\n"
            "Bob: Will do."
        ),
        "action_items": [
            {"description": "Lead negotiations for the Acme dataset acquisition and report back", "assignee": "Bob"},
        ],
        "decisions": [
            {"decision": "Approve logo option B"},
            {"decision": "Hold the annual offsite in Lisbon"},
        ],
    },
]


def main() -> None:
    for entry in DATASET:
        tid = entry["id"]
        (TX / f"{tid}.json").write_text(json.dumps({
            "id": tid,
            "category": entry["category"],
            "meeting_date": entry["meeting_date"],
            "transcript": entry["transcript"],
        }, indent=2))
        (LB / f"{tid}.json").write_text(json.dumps({
            "id": tid,
            "action_items": entry["action_items"],
            "decisions": entry["decisions"],
        }, indent=2))
    print(f"Wrote {len(DATASET)} transcript+label pairs to {TX} and {LB}")


if __name__ == "__main__":
    main()