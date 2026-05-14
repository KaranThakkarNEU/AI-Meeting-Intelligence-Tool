from __future__ import annotations

from ..models.topics import TopicList
from ..models.transcript import Transcript
from .base import BaseExtractor


class TopicExtractor(BaseExtractor[TopicList]):
    stage_name = "topics"
    response_model = TopicList

    def system_prompt(self) -> str:
        return (
            "You are a meeting topic segmenter. Divide the transcript into coherent, "
            "non-overlapping topic blocks that together cover the entire conversation.\n\n"
            "Rules:\n"
            "1. Segments must be NON-OVERLAPPING and must collectively cover EVERY utterance "
            "from index 0 to the last index. No gaps. No overlap.\n"
            "2. `start_utterance_index` and `end_utterance_index` are INCLUSIVE indices into "
            "the transcript utterances list (the [N] prefix shown on each line). The first "
            "topic must start at 0; the last topic must end at the final utterance index.\n"
            "3. Each consecutive topic must satisfy: next.start_utterance_index = "
            "prev.end_utterance_index + 1.\n"
            "4. `title` should be 2–100 chars, concise and descriptive (e.g., 'Q3 roadmap "
            "planning', not 'Discussion').\n"
            "5. `summary` should be 1–2 sentences (10–500 chars) describing what was discussed.\n"
            "6. `speakers` is the list of speaker names who spoke during this topic block. "
            "Use names exactly as they appear in the transcript.\n"
            "7. Aim for 2–8 topics per transcript. Avoid splitting too finely. A topic should "
            "be a coherent thread of discussion, not a single utterance.\n"
            "8. If the transcript is very short (1–3 utterances), produce a single topic "
            "covering the whole thing.\n"
        )

    def user_prompt(self, transcript: Transcript) -> str:
        last_idx = len(transcript.utterances) - 1
        return (
            f"The transcript has {len(transcript.utterances)} utterances, indexed 0 through "
            f"{last_idx}. The FIRST topic must start at index 0 and the LAST topic must end at "
            f"index {last_idx}. Cover every index exactly once.\n\n"
            f"Transcript:\n{transcript.to_prompt_text()}"
        )