"""Conservative, intentionally narrow offline checks. No generated demo results."""

import re
from dataclasses import dataclass

from .document import Paragraph, digest, evidence


@dataclass(frozen=True)
class Fact:
    subject: str
    attribute: str
    value: str
    category: str
    paragraph_id: str
    quote: str
    transition: bool = False


# Whole-paragraph exclusions trade recall for fewer misleading accusations.
NONFACTUAL = re.compile(
    r"回忆|回想|梦中|梦见|假如|假设|如果|谎言|撒谎|曾经|多年前|据说|传闻|冒充|化名|flashback|dream|what if|imagined|rumou?r|lied|years (?:ago|earlier)|disguised",
    re.I,
)
ZH_NAME = r"([\u4e00-\u9fffA-Za-z·]{2,12})"
EN_NAME = r"([A-Z][a-z]+(?: [A-Z][a-z]+)?)"

PATTERNS = [
    (rf"{ZH_NAME}的眼睛是([蓝绿棕黑灰褐琥珀]+)色", "eye_color", "character", False),
    (rf"{ZH_NAME}惯用(左|右)手", "handedness", "character", False),
    (rf"{ZH_NAME}的血型是(AB|A|B|O)型", "blood_type", "character", False),
    (rf"{ZH_NAME}出生于(\d{{4}})年", "birth_year", "timeline", False),
    (rf"{EN_NAME} has (blue|green|brown|black|grey|gray|amber) eyes", "eye_color", "character", False),
    (rf"{EN_NAME} is (left|right)-handed", "handedness", "character", False),
    (rf"{EN_NAME} was born in (\d{{4}})", "birth_year", "timeline", False),
]
STATE_PATTERNS = [
    (rf"{ZH_NAME}被(?:彻底)?(?:熔毁|烧毁|摧毁)", "object_state", "destroyed", "object", False),
    (rf"{ZH_NAME}被(?:成功)?(?:修复|重铸|重建)", "object_state", "intact", "object", True),
    (rf"取出{ZH_NAME}(?:开门|开锁|使用)", "object_state", "intact", "object", False),
    (rf"{ZH_NAME}(?:已经死亡|已确认死亡)", "life_state", "dead", "character", False),
    (rf"{ZH_NAME}(?:仍然活着|还活着)", "life_state", "alive", "character", False),
    (rf"{ZH_NAME}(?:已经复活|被复活)", "life_state", "alive", "character", True),
    (r"[Tt]he ([a-z]+(?: [a-z]+){0,2}?) was destroyed", "object_state", "destroyed", "object", False),
    (
        r"[Tt]he ([a-z]+(?: [a-z]+){0,2}?) was (?:repaired|reforged|rebuilt)",
        "object_state",
        "intact",
        "object",
        True,
    ),
    (r"used the ([a-z]+(?: [a-z]+){0,2}?) to (?:unlock|open)", "object_state", "intact", "object", False),
    (rf"{EN_NAME} was confirmed dead", "life_state", "dead", "character", False),
    (rf"{EN_NAME} is still alive", "life_state", "alive", "character", False),
    (rf"{EN_NAME} was resurrected", "life_state", "alive", "character", True),
]


def extract(paragraphs: list[Paragraph]) -> list[Fact]:
    found = []
    for p in paragraphs:
        if NONFACTUAL.search(p.text) or re.search(r'[“”「」"]', p.text):
            continue
        # Separating sentences avoids capturing preceding narrative as a name.
        for sentence in re.split(r"[。！？.!?;；\n]", p.text):
            for pattern, attribute, category, transition in PATTERNS:
                for match in re.finditer(pattern, sentence):
                    quote = match.group(0)
                    if len(quote) >= 4 and p.text.count(quote) == 1:
                        value = match[2].lower()
                        if value == "grey":
                            value = "gray"
                        found.append(
                            Fact(match[1].strip(), attribute, value, category, p.id, quote, transition)
                        )
            for pattern, attribute, value, category, transition in STATE_PATTERNS:
                for match in re.finditer(pattern, sentence):
                    quote = match.group(0)
                    if len(quote) >= 4 and p.text.count(quote) == 1:
                        found.append(
                            Fact(match[1].strip(), attribute, value, category, p.id, quote, transition)
                        )
    return found


def key(fact: Fact):
    return (re.sub(r"\s+", " ", fact.subject).strip().casefold(), fact.attribute.casefold())


def candidates(facts: list[Fact], paragraphs: list[Paragraph], max_pairs=120):
    positions = {p.id: p.index for p in paragraphs}
    ordered = sorted(
        facts,
        key=lambda f: (positions[f.paragraph_id], paragraphs[positions[f.paragraph_id]].text.find(f.quote)),
    )
    groups: dict[tuple, list[Fact]] = {}
    pairs, seen = [], set()
    for fact in ordered:
        previous = groups.setdefault(key(fact), [])
        if fact.transition:
            previous.clear()
        else:
            for old in previous:
                if old.value.casefold() == fact.value.casefold():
                    continue
                # Intact -> destroyed and alive -> dead are ordinary progression.
                if fact.attribute == "object_state" and old.value != "destroyed":
                    continue
                if fact.attribute == "life_state" and old.value != "dead":
                    continue
                # A changed explanation between two unchanged quotes must reopen
                # the review. Edits outside the evidence span preserve decisions.
                context = "\n".join(
                    p.text for p in paragraphs[positions[old.paragraph_id] : positions[fact.paragraph_id] + 1]
                )
                fingerprint = digest("|".join((str(key(fact)), old.quote, fact.quote, context)))[:24]
                if fingerprint not in seen:
                    pairs.append((fingerprint, old, fact))
                    seen.add(fingerprint)
                    if len(pairs) > max_pairs:
                        return pairs[:max_pairs], True
        if all(old.value.casefold() != fact.value.casefold() for old in previous):
            previous.append(fact)
    return pairs[:max_pairs], len(pairs) > max_pairs


LABELS = {
    "eye_color": "瞳色 / eye color",
    "handedness": "惯用手 / handedness",
    "blood_type": "血型 / blood type",
    "birth_year": "出生年份 / birth year",
    "object_state": "物品状态 / object state",
    "life_state": "生死状态 / life state",
}

STATE_LABELS = {"destroyed": "已毁坏", "intact": "可使用", "dead": "已死亡", "alive": "仍存活"}


def finding(pair, paragraphs, *, reason=None, title=None, category=None):
    fingerprint, before, after = pair
    lookup = {p.id: p for p in paragraphs}
    return {
        "id": fingerprint,
        "subject": after.subject,
        "category": category or after.category,
        "title": title or f"{after.subject} · {LABELS.get(after.attribute, after.attribute)}",
        "reason": reason
        or (
            f"两处明确陈述不同：{STATE_LABELS.get(before.value, before.value)} → "
            f"{STATE_LABELS.get(after.value, after.value)}。请结合剧情判断是否已有解释。 / "
            f"Explicit statements differ: {before.value} → {after.value}. "
            "Check whether the story explains the change."
        ),
        "before": evidence(lookup[before.paragraph_id], before.quote),
        "after": evidence(lookup[after.paragraph_id], after.quote),
        "status": "pending",
        "note": "",
    }
