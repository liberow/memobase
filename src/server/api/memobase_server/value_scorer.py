from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from .env import CONFIG, TRACE_LOG
from .llms import llm_complete


async def score_session_event_value(
    project_id: str,
    user_id: str,
    content: str,
    created_at: Optional[datetime] = None,
) -> float:
    """
    Score how valuable a session-level event is for long-term memory.

    The score is in [0.0, 1.0]. Higher score means we should keep the event.
    This score is used as the Value factor in QAMR retrieval.
    """
    # Fast path: trivial acknowledgements and chit-chat are always low value.
    zh_trivial_markers = ["哈哈", "嗯嗯", "好啊", "收到"]
    en_trivial_patterns = [r"\bok\b", r"\bOK\b"]
    
    is_trivial = any(marker in content for marker in zh_trivial_markers) or \
                 any(re.search(pattern, content) for pattern in en_trivial_patterns)
    
    if is_trivial:
        TRACE_LOG.debug(
            project_id,
            user_id,
            f"Trivial markers found in content: {content[:100]}...",
        )
        return 0.0

    # Prepare time strings for the prompt.
    tz = CONFIG.timezone
    now = datetime.now(tz)
    created = (created_at or now).astimezone(tz)
    now_str = now.strftime("%Y-%m-%d")
    created_str = created.strftime("%Y-%m-%d")

    system_prompt = """You are a long-term conversation memory filtering assistant. Your job is to keep events that may be useful for future QA tasks.

Context:
- A user and their friend have multiple long conversations (split by sessions/days).
- Later, there will be many questions about these conversations. Typical questions ask about:
  - Specific times, dates, or relative time spans (year, month, "last week", "10 years ago", etc.)
  - Concrete events and activities (trips, races, courses, workshops, meetups, conferences, etc.)
  - Personal identity and relationships (gender identity, family members, relationship status, career/education plans)
  - Long-term preferences and habits (hobbies, ways to relax, favorite books/activities, places they often go, etc.)
  - Hypothetical or reasoning questions based on these facts ("would X still... if...", "is it likely that...", etc.)

Your goal:
- Decide whether this event summary contains new information that could be useful for such future questions.
- If the event contains any concrete facts, plans, time information, places, book titles, activity names, long-term preferences, or changes in relationships, you should treat it as valuable and prefer to keep it.
- Only when the event is almost entirely small talk, greetings, or generic emotional support with no new concrete facts, may you treat it as low value and consider dropping it.

Scoring (0.0–1.0):
- 0.8–1.0: Clear personal facts, specific timestamps or time ranges, concrete events or plans, or summaries/reflections/reasoning about such facts.
- 0.5–0.8: Contains meaningful preferences, feelings, motivations, or relationship dynamics that still help understand the person.
- 0.3–0.5: Mostly generic interaction or emotional expression, but with a small amount of potentially useful information (these should still be slightly biased toward keeping).
- 0.0–0.3: Almost only greetings, repeated confirmations, or empty encouragement/acknowledgements, with no new factual information.

Important principles:
- If you are unsure whether this event will be useful in the future, **bias toward a higher score (>= 0.5)**. It is better to keep some extra events than to accidentally delete useful memory.
- Do NOT give a low score just because the information looks "too detailed" or "too trivial". Many details (exact dates, locations, activities) are exactly the evidence needed for later QA.

Output:
Return only a single floating-point number between 0.000 and 1.000 (for example: 0.750). Do not output any other text."""

    user_prompt = (
        f"Event content:\n{content}\n\n"
        f"Event time: {created_str}\n"
        f"Current time: {now_str}\n\n"
        "Score:"
    )

    use_model = CONFIG.value_scorer_model or CONFIG.thinking_llm_model or CONFIG.best_llm_model

    r = await llm_complete(
        project_id,
        prompt=user_prompt,
        system_prompt=system_prompt,
        model=use_model,
        max_tokens=8,
        prompt_id="value_scorer_event",
        no_cache=True,
    )
    if not r.ok():
        TRACE_LOG.error(
            project_id,
            user_id,
            f"Value scorer LLM call failed: {r.msg()}",
        )
        return 1.0

    text = str(r.data()).strip()

    # Extract the first float between 0 and 1 from the model output.
    match = re.search(r"\b(0\.\d+|1\.0+|0|1)\b", text)
    if not match:
        match = re.search(r"(\d+\.?\d*)", text)
        if match:
            try:
                score = float(match.group(1))
                if score < 0.0 or score > 1.0:
                    TRACE_LOG.warning(
                        project_id,
                        user_id,
                        f"Score {score} out of range [0,1] from LLM output: {text}",
                    )
                    return 1.0
            except ValueError:
                TRACE_LOG.warning(
                    project_id,
                    user_id,
                    f"Unable to parse value score from LLM output: {text}",
                )
                return 1.0
        else:
            TRACE_LOG.warning(
                project_id,
                user_id,
                f"Unable to parse value score from LLM output: {text}",
            )
            return 1.0
    else:
        try:
            score = float(match.group(1))
        except ValueError:
            TRACE_LOG.warning(
                project_id,
                user_id,
                f"Failed to convert value score to float from: {match.group(1)}",
            )
            return 1.0

    # Clamp score into [0.0, 1.0].
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    return score
