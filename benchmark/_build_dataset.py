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
        "id": "T11",
        "category": "technical_discussion",
        "meeting_date": "2026-05-24T10:00:00",
        "transcript": (
            "Priya: The p99 latency on the search endpoint jumped to 800ms yesterday.\n"
            "Marcus: I traced it to the new embedding cache. The TTL is too short, we're recomputing too often.\n"
            "Priya: What's a reasonable TTL?\n"
            "Marcus: Probably six hours. The embeddings don't change that often.\n"
            "Priya: Agreed. Marcus, can you ship that fix today?\n"
            "Marcus: Yes, I'll deploy after lunch and monitor for 24 hours.\n"
            "Sara: While we're on perf, we should also add a circuit breaker to the upstream LLM call.\n"
            "Priya: Good idea. Sara, write up a design doc this week?\n"
            "Sara: I can have a draft by Thursday."
        ),
        "action_items": [
            {"description": "Deploy the embedding cache TTL fix and monitor for 24 hours", "assignee": "Marcus"},
            {"description": "Write a design doc for the upstream LLM circuit breaker", "assignee": "Sara"},
        ],
        "decisions": [
            {"decision": "Set the embedding cache TTL to six hours"},
        ],
    },
    {
        "id": "T12",
        "category": "customer_call",
        "meeting_date": "2026-05-25T14:00:00",
        "transcript": (
            "Customer: Overall we like the product but the reporting is a real gap for us.\n"
            "AM: Can you tell me more about what you'd want?\n"
            "Customer: We need weekly PDF exports for our board. Right now we're screenshotting dashboards.\n"
            "PM: Got it. We have PDF export on the roadmap for Q3 already.\n"
            "Customer: If we get it earlier we'd expand to two more business units.\n"
            "PM: Let me check feasibility. I'll come back to you by Friday with a timeline.\n"
            "AM: Thanks for the feedback. I'll loop in our solutions engineer to help with the screenshot workaround in the meantime."
        ),
        "action_items": [
            {"description": "Check feasibility of accelerating PDF export and reply with a timeline", "assignee": "PM"},
            {"description": "Loop in a solutions engineer to help with a screenshot workaround", "assignee": "AM"},
        ],
        "decisions": [],
    },
    {
        "id": "T13",
        "category": "retrospective",
        "meeting_date": "2026-05-26T15:00:00",
        "transcript": (
            "Alice: Sprint retro. What went well?\n"
            "Bob: We shipped the auth migration ahead of schedule.\n"
            "Carol: Daily standups felt tighter — fifteen minutes flat.\n"
            "Alice: What didn't go well?\n"
            "Dave: Too many last-minute scope additions from product.\n"
            "Carol: And the staging environment was down twice.\n"
            "Alice: Actions for next sprint?\n"
            "Dave: I'll set up a Friday cutoff for scope changes.\n"
            "Bob: I'll automate staging health checks so we catch issues earlier.\n"
            "Alice: Decision: we'll lock scope every Friday from now on."
        ),
        "action_items": [
            {"description": "Set up a Friday scope-change cutoff process", "assignee": "Dave"},
            {"description": "Automate staging environment health checks", "assignee": "Bob"},
        ],
        "decisions": [
            {"decision": "Lock sprint scope every Friday going forward"},
        ],
    },
    {
        "id": "T14",
        "category": "vendor_negotiation",
        "meeting_date": "2026-05-27T11:00:00",
        "transcript": (
            "Buyer: Your renewal quote came in 40% higher. We can't accept that.\n"
            "Vendor: Usage has more than doubled — the new tier reflects actual consumption.\n"
            "Buyer: Understood, but we'd need to evaluate alternatives at that price.\n"
            "Vendor: We could offer a multi-year commit at the old rate plus 15%.\n"
            "Buyer: Two-year commit at plus 12% and we have a deal.\n"
            "Vendor: I need to clear that with finance. I'll come back tomorrow.\n"
            "Buyer: Works. I'll have legal start reviewing the contract template in parallel."
        ),
        "action_items": [
            {"description": "Get finance approval for the two-year commit at +12% and respond tomorrow", "assignee": "Vendor"},
            {"description": "Have legal start reviewing the contract template", "assignee": "Buyer"},
        ],
        "decisions": [],
    },
    {
        "id": "T15",
        "category": "long_planning",
        "meeting_date": "2026-05-28T09:00:00",
        "transcript": (
            "Alice: Q3 planning. We have four initiatives to slot in.\n"
            "Bob: Mobile app rewrite is my top priority — current code is unmaintainable.\n"
            "Carol: SOC2 audit prep is non-negotiable. Deadline is September 15th.\n"
            "Dave: Self-serve onboarding flow — sales has been blocked on this for months.\n"
            "Eve: Internal admin tools rewrite. Lower urgency but a constant tax.\n"
            "Alice: We can't do all four. Let's rank.\n"
            "Carol: SOC2 first. Hard deadline.\n"
            "Bob: Then mobile rewrite — it's blocking three product launches.\n"
            "Dave: Self-serve next. I'll own this.\n"
            "Alice: Eve, internal admin slides to Q4.\n"
            "Eve: Fair enough.\n"
            "Alice: Decision: Q3 priorities are SOC2, mobile rewrite, self-serve, in that order. Admin tools deferred to Q4.\n"
            "Carol: I'll have a SOC2 work breakdown by Monday.\n"
            "Bob: I'll start the mobile rewrite RFC this week.\n"
            "Dave: I'll draft a self-serve PRD by next Friday.\n"
            "Alice: Reconvene in two weeks to check progress."
        ),
        "action_items": [
            {"description": "Produce a SOC2 work breakdown", "assignee": "Carol"},
            {"description": "Start the mobile rewrite RFC", "assignee": "Bob"},
            {"description": "Draft the self-serve onboarding PRD", "assignee": "Dave"},
            {"description": "Reconvene in two weeks to check progress", "assignee": "Alice"},
        ],
        "decisions": [
            {"decision": "Q3 priority order is SOC2, mobile rewrite, then self-serve onboarding"},
            {"decision": "Defer the internal admin tools rewrite to Q4"},
        ],
    },
    {
        "id": "T16",
        "category": "international_team",
        "meeting_date": "2026-05-29T13:00:00",
        "transcript": (
            "Yuki: Tokyo office reports the new release works smoothly.\n"
            "Aisha: Same in Lagos, no regressions on slower connections.\n"
            "Lukas: Berlin sees one issue — the date format is American by default for European users.\n"
            "Yuki: Should we localize that?\n"
            "Aisha: Yes, please. It's a small thing but it signals we care.\n"
            "Lukas: I'll open a ticket and take it this sprint.\n"
            "Yuki: Also, Tokyo would like the help center translated to Japanese.\n"
            "Aisha: Lagos too — at least French support.\n"
            "Sven: Let me check with localization budget and get back next week.\n"
            "Lukas: Decision today: locale-aware date formatting ships this sprint."
        ),
        "action_items": [
            {"description": "Open a ticket and implement locale-aware date formatting this sprint", "assignee": "Lukas"},
            {"description": "Check localization budget and report back on Japanese and French help center translation", "assignee": "Sven"},
        ],
        "decisions": [
            {"decision": "Ship locale-aware date formatting this sprint"},
        ],
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