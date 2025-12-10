from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from ..env import CONFIG, TRACE_LOG
from ..llms import llm_complete


async def score_session_event_value(
    project_id: str,
    user_id: str,
    content: str,
    created_at: Optional[datetime] = None,
) -> float:
    """
    Score how valuable a session-level event is for long-term memory.

    The score is in [0.0, 1.0]. Higher score means we should keep the event.
    This helper is intentionally lightweight and only used when the
    value-based scoring feature is enabled.
    """
    if CONFIG.value_scoring_mode == "off":
        # Feature disabled, always keep events.
        return 1.0

    # Fast path: trivial acknowledgements and chit-chat are always low value.
    # 中文标记使用子串匹配，英文 "ok"/"OK" 使用完整单词匹配（避免误杀 "took", "book", "Tokyo" 等）
    zh_trivial_markers = ["哈哈", "嗯嗯", "好啊", "收到"]
    en_trivial_patterns = [r"\bok\b", r"\bOK\b"]  # \b = word boundary
    
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

    # 原始中文设计（保留在注释中，方便对照和论文撰写）：
    # 你是一个长期对话记忆筛选助手，需要为后续的问答任务保留有用的记忆事件。
    # 【数据背景】
    # - 用户和朋友之间有多次长对话（按天/会话切分）。
    # - 之后会有很多关于这些对话的提问，这些问题经常问：
    #   - 具体时间、日期或相对时间（某年某月、上周、几年前等）
    #   - 真实发生过的事件和活动（旅行、比赛、课程、工作坊、聚会、会议等）
    #   - 个人身份与关系（性别认同、家庭成员、关系状态、职业/教育规划）
    #   - 长期的偏好和习惯（爱好、减压方式、喜欢的书/活动、经常去的地方等）
    #   - 基于这些事实的推理或假设性判断（如果……会怎样、是否仍然……）
    # 【你的目标】
    # - 你要判断：这一段事件摘要，是否包含对未来这类问题可能有用的新信息。
    # - 只要事件里有任何一个具体事实、计划、时间信息、地点、书名、活动名、长期偏好、关系变化等，都应该视为有价值，倾向于保留。
    # - 只有在几乎完全是寒暄、客套、简单情绪性赞美，且没有新的具体事实时，才可以认为是低价值，可以考虑丢弃。
    # 【评分标准（0.0-1.0）】
    # - 0.8-1.0：包含清晰的个人事实、时间点/时间跨度、具体事件或计划，或者对上述内容的总结、反思、推理。
    # - 0.5-0.8：包含有一定信息量的偏好、感受、动机、关系动态等，对理解人物仍然有帮助。
    # - 0.3-0.5：主要是一般性的互动或情绪表达，但带有少量可能有用的信息（此类也建议偏向保留）。
    # - 0.0-0.3：几乎只有寒暄、重复确认、空洞的鼓励/附和，没有新的事实信息。
    # 【重要原则】
    # - 如果不确定这一段将来是否会有用，请偏向打高分（>= 0.5），宁可多保留一些，也不要误删有用记忆。
    # - 不要因为信息看起来“太细节”“太琐碎”就给低分——很多看似细节的信息（具体日期、地点、活动）正是后续问答所需要的证据。

    # 英文版本 prompt（实际用于实验）
    system_prompt = """You are a long-term conversation memory filtering assistant. Your job is to keep events that may be useful for future QA tasks.

Context:
- A user and their friend have multiple long conversations (split by sessions/days).
- Later, there will be many questions about these conversations. Typical questions ask about:
  - Specific times, dates, or relative time spans (year, month, \"last week\", \"10 years ago\", etc.)
  - Concrete events and activities (trips, races, courses, workshops, meetups, conferences, etc.)
  - Personal identity and relationships (gender identity, family members, relationship status, career/education plans)
  - Long-term preferences and habits (hobbies, ways to relax, favorite books/activities, places they often go, etc.)
  - Hypothetical or reasoning questions based on these facts (\"would X still... if...\", \"is it likely that...\", etc.)

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
- Do NOT give a low score just because the information looks \"too detailed\" or \"too trivial\". Many details (exact dates, locations, activities) are exactly the evidence needed for later QA.

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
        # Fail-open: keep the event when scoring fails.
        return 1.0

    text = str(r.data()).strip()

    # Extract the first float between 0 and 1 from the model output.
    match = re.search(r"\b(0\.\d+|1\.0+|0|1)\b", text)
    if not match:
        # Fallback: 尝试匹配任何数字
        match = re.search(r"(\d+\.?\d*)", text)
        if match:
            try:
                score = float(match.group(1))
                # 如果数字超出范围，记录警告
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