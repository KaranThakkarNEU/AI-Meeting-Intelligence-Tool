from __future__ import annotations

from ..models.action_items import ActionItemList
from .base import BaseExtractor


class ActionItemExtractor(BaseExtractor[ActionItemList]):
    stage_name = "action_items"
    response_model = ActionItemList

    def system_prompt(self) -> str:
        return (
            "You are a meeting action item extractor. Your job is to extract every "
            "commitment, task, or to-do that was discussed in the meeting transcript.\n\n"
            "Rules:\n"
            "1. Extract only action items that are EXPLICITLY discussed in the transcript. "
            "Never invent items not present in the text.\n"
            "2. For each item, include a `source_quote` that is a verbatim or near-verbatim "
            "substring of the transcript (5+ characters) where the action item was discussed. "
            "This is mandatory — every item must be grounded in actual transcript text.\n"
            "3. Set `assignee` to the speaker who took on the task. If no clear assignee is "
            "stated, leave it null. Never guess or pick a random speaker.\n"
            "4. Set `due_date` only if a specific date or clearly resolvable relative date is "
            "stated (e.g. 'by Friday', 'next Monday'). If only vague timing is given "
            "(e.g. 'soon', 'eventually'), leave it null.\n"
            "5. Set `priority` to high for urgent or time-critical items, medium by default, "
            "and low for nice-to-haves or optional follow-ups.\n"
            "6. Set `confidence` between 0.0 and 1.0 based on how clearly the action was "
            "committed to. Items below 0.5 should be borderline; never extract items below 0.3.\n"
            "7. Deduplicate items mentioned multiple times — merge into one entry with the most "
            "complete fields.\n"
            "8. `description` must be a clear, specific sentence (5+ chars). Never use generic "
            "placeholders like 'TBD', 'TODO', or 'N/A'.\n"
            "9. If no action items are present, return an empty `items` list. Do not invent any.\n"
        )