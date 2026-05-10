"""
Persona Extractor — scoped to a SINGLE conversation.
Every field has an evidence array. Habits require 3+ occurrences.
"""
import re
from collections import Counter, defaultdict
from typing import List, Dict

from config import HABIT_MIN_OCCURRENCES, KNOWN_JOB_TITLES
from models.message import Message
from models.persona_model import (
    Persona, Habit, PersonalFact, PersonalityTrait,
    CommunicationStyle, PersonaEvidence,
)

STOPWORDS_FOR_TOP_WORDS = {
    'i', 'me', 'my', 'you', 'your', 'the', 'a', 'an', 'is', 'are', 'was',
    'were', 'be', 'been', 'am', 'do', 'does', 'did', 'have', 'has', 'had',
    'it', 'its', 'we', 'they', 'he', 'she', 'to', 'of', 'in', 'for', 'on',
    'with', 'at', 'by', 'from', 'as', 'and', 'or', 'but', 'not', 'so',
    'that', 'this', 'what', 'just', 'like', 'yeah', 'yes', 'no', 'ok',
    'okay', 'well', 'really', 'very', 'too', 'also', 'about', 'would',
    'could', 'should', 'will', 'can', 'if', 'up', 'out', 'all', 'been',
    'get', 'got', 'going', 'go', 'know', 'think', 'one', 'than',
}

EMOJI_RE = re.compile(
    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
    r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
    r'\U00002702-\U000027B0\U000024C2-\U0001F251'
    r'\U0001f926-\U0001f937\U00010000-\U0010ffff]+'
)

# --- Habit patterns (category: [(compiled_regex, description_template)]) ---
HABIT_PATTERNS = {
    'sleep': [
        (re.compile(r'\b(?:good\s+night|going\s+to\s+bed|bedtime|sleep\s+early|sleep\s+late)\b', re.I), "goes to bed"),
        (re.compile(r'\b(?:woke\s+up|wake\s+up|morning\s+routine|early\s+morning|slept\s+in)\b', re.I), "waking patterns"),
        (re.compile(r'\b(?:insomnia|can\'t\s+sleep|tired|exhausted|nap)\b', re.I), "sleep issues"),
    ],
    'food': [
        (re.compile(r'\b(?:breakfast|lunch|dinner|supper|brunch|snack)\b', re.I), "meal patterns"),
        (re.compile(r'\b(?:cooking|cooked|baked|baking|made\s+(?:food|dinner|lunch|breakfast))\b', re.I), "cooking"),
        (re.compile(r'\b(?:eating|ate|ordered\s+(?:food|pizza|takeout))\b', re.I), "eating"),
    ],
    'exercise': [
        (re.compile(r'\b(?:went\s+(?:to\s+the\s+)?gym|worked\s+out|workout|exercise[ds]?)\b', re.I), "gym/workout"),
        (re.compile(r'\b(?:went\s+(?:for\s+a\s+)?(?:run|jog|walk|hike)|running|jogging|hiking)\b', re.I), "outdoor exercise"),
        (re.compile(r'\b(?:yoga|stretching|swim|swimming|cycling)\b', re.I), "other exercise"),
    ],
    'routine': [
        (re.compile(r'\b(?:every\s+(?:morning|day|night|week)|daily\s+routine|always\s+do|habit)\b', re.I), "daily routine"),
        (re.compile(r'\b(?:usually\s+(?:i|we)|i\s+always|my\s+routine)\b', re.I), "routine mention"),
    ],
}

RELATIONSHIP_PATTERNS = [
    (re.compile(r'\bmy\s+(?:wife|husband|partner|boyfriend|girlfriend|spouse|fianc[eé]+)\b', re.I), 'romantic_partner'),
    (re.compile(r'\bmy\s+(?:mom|mother|dad|father|parents?)\b', re.I), 'parent'),
    (re.compile(r'\bmy\s+(?:son|daughter|kids?|children|child|baby|babies)\b', re.I), 'child'),
    (re.compile(r'\bmy\s+(?:brother|sister|siblings?)\b', re.I), 'sibling'),
    (re.compile(r'\bmy\s+(?:dog|cat|pet|puppy|kitten)\b', re.I), 'pet'),
    (re.compile(r'\bmy\s+(?:uncle|aunt|cousin|grandma|grandpa|grandfather|grandmother)\b', re.I), 'extended_family'),
]

LOCATION_RE = re.compile(
    r'(?:i\s+live\s+in|i\'m\s+from|i\s+moved\s+to|i\'m\s+moving\s+to|i\s+grew\s+up\s+in|i\'m\s+in)\s+(.+?)(?:[.!?,]|$)',
    re.I
)

PREFERENCE_RE = re.compile(
    r'(?:i\s+(?:love|really\s+love|enjoy|adore)\s+(.+?)(?:[.!?,]|$))',
    re.I
)

# Sentiment word lists (simple, no external dependency)
POSITIVE_WORDS = {
    'love', 'great', 'awesome', 'amazing', 'wonderful', 'fantastic', 'excellent',
    'beautiful', 'happy', 'glad', 'excited', 'perfect', 'incredible', 'brilliant',
    'lovely', 'delightful', 'terrific', 'superb', 'magnificent', 'outstanding',
    'enjoy', 'fun', 'cool', 'sweet', 'nice', 'kind', 'grateful', 'blessed',
}
NEGATIVE_WORDS = {
    'hate', 'terrible', 'awful', 'horrible', 'worst', 'angry', 'frustrated',
    'annoyed', 'upset', 'disappointed', 'sad', 'depressed', 'miserable',
    'disgusted', 'furious', 'pathetic', 'boring', 'stupid', 'ridiculous',
    'ugly', 'nasty', 'dreadful', 'lousy', 'rotten',
}


def extract_persona_for_conversation(messages: List[Message], conversation_id: int) -> Persona:
    """
    Extract persona from ONLY User 1's messages in a single conversation.
    This is NEVER called globally across all conversations.
    """
    user1_msgs = [m for m in messages if m.sender.strip() == "User 1"]

    if not user1_msgs:
        return Persona(conversation_id=conversation_id, total_messages_analyzed=0)

    persona = Persona(
        conversation_id=conversation_id,
        habits=_extract_habits(user1_msgs),
        personal_facts=_extract_facts(user1_msgs),
        personality_traits=_extract_traits(user1_msgs),
        communication_style=_analyze_comm_style(user1_msgs),
        total_messages_analyzed=len(user1_msgs),
    )
    return persona


def _extract_habits(messages: List[Message]) -> List[Habit]:
    """Extract habits requiring HABIT_MIN_OCCURRENCES (3+) before marking."""
    category_hits = defaultdict(list)

    for msg in messages:
        text = msg.text
        for category, patterns in HABIT_PATTERNS.items():
            for regex, desc_template in patterns:
                if regex.search(text):
                    category_hits[category].append(
                        PersonaEvidence(text=text[:150], message_idx=msg.global_idx)
                    )

    habits = []
    for category, evidences in category_hits.items():
        if len(evidences) >= HABIT_MIN_OCCURRENCES:
            habits.append(Habit(
                category=category,
                description=f"Frequently mentions {category}-related activities",
                occurrence_count=len(evidences),
                evidence=evidences[:5],  # Cap evidence to 5
            ))

    return habits


def _extract_facts(messages: List[Message]) -> List[PersonalFact]:
    """Extract personal facts: relationships, location, occupation, preferences."""
    facts = []
    seen = set()

    for msg in messages:
        text = msg.text

        # Relationships
        for regex, rel_type in RELATIONSHIP_PATTERNS:
            if regex.search(text):
                key = f"rel:{rel_type}"
                if key not in seen:
                    seen.add(key)
                    facts.append(PersonalFact(
                        category="relationship",
                        value=rel_type.replace('_', ' '),
                        evidence=[PersonaEvidence(text=text[:150], message_idx=msg.global_idx)],
                    ))

        # Occupation — only match known job titles
        text_lower = text.lower()
        for title in KNOWN_JOB_TITLES:
            occ_patterns = [
                re.compile(rf"\bi(?:'m|am)\s+a\s+{re.escape(title)}\b", re.I),
                re.compile(rf"\bi\s+work\s+as\s+a\s+{re.escape(title)}\b", re.I),
                re.compile(rf"\bi(?:'m|am)\s+a\s+\w+\s+{re.escape(title)}\b", re.I),
            ]
            for pat in occ_patterns:
                if pat.search(text):
                    key = f"occ:{title}"
                    if key not in seen:
                        seen.add(key)
                        facts.append(PersonalFact(
                            category="occupation",
                            value=title,
                            evidence=[PersonaEvidence(text=text[:150], message_idx=msg.global_idx)],
                        ))

        # Location
        loc_match = LOCATION_RE.search(text)
        if loc_match:
            location = loc_match.group(1).strip()
            if len(location) > 2 and len(location) < 60:
                key = f"loc:{location.lower()[:30]}"
                if key not in seen:
                    seen.add(key)
                    facts.append(PersonalFact(
                        category="location",
                        value=location,
                        evidence=[PersonaEvidence(text=text[:150], message_idx=msg.global_idx)],
                    ))

        # Preferences
        pref_match = PREFERENCE_RE.search(text)
        if pref_match:
            pref = pref_match.group(1).strip()
            skip = {'it', 'that', 'this', 'you', 'them', 'her', 'him'}
            if len(pref) > 3 and pref.lower() not in skip:
                key = f"pref:{pref.lower()[:30]}"
                if key not in seen:
                    seen.add(key)
                    facts.append(PersonalFact(
                        category="preference",
                        value=pref,
                        evidence=[PersonaEvidence(text=text[:150], message_idx=msg.global_idx)],
                    ))

    return facts[:30]


def _extract_traits(messages: List[Message]) -> List[PersonalityTrait]:
    """Compute personality traits from message patterns."""
    if not messages:
        return []

    total = len(messages)
    question_count = sum(1 for m in messages if '?' in m.text)
    excl_count = sum(1 for m in messages if '!' in m.text)
    humor_count = sum(1 for m in messages if re.search(r'\b(?:lol|haha|hehe|lmao|rofl)\b|😂|🤣', m.text, re.I))
    empathy_count = sum(1 for m in messages if re.search(r'\b(?:sorry|hope\s+you|feel\s+for|thinking\s+of\s+you|take\s+care)\b', m.text, re.I))

    # Simple sentiment
    positive_count = 0
    negative_count = 0
    for m in messages:
        words = set(re.findall(r'\b[a-z]+\b', m.text.lower()))
        positive_count += len(words & POSITIVE_WORDS)
        negative_count += len(words & NEGATIVE_WORDS)

    question_ratio = question_count / total
    excl_ratio = excl_count / total
    humor_ratio = humor_count / total
    empathy_ratio = empathy_count / total
    sentiment = (positive_count - negative_count) / max(positive_count + negative_count, 1)

    traits = []

    if question_ratio > 0.4:
        traits.append(_make_trait("curious", question_ratio, messages, r'\?'))
    elif question_ratio > 0.2:
        traits.append(_make_trait("curious", question_ratio, messages, r'\?'))

    if excl_ratio > 0.3:
        traits.append(_make_trait("expressive", excl_ratio, messages, r'!'))
    elif excl_ratio > 0.15:
        traits.append(_make_trait("expressive", excl_ratio, messages, r'!'))

    if humor_ratio > 0.1:
        traits.append(_make_trait("humorous", humor_ratio, messages, r'\b(?:lol|haha|hehe|lmao)\b'))
    elif humor_ratio > 0.03:
        traits.append(_make_trait("humorous", humor_ratio, messages, r'\b(?:lol|haha|hehe|lmao)\b'))

    if empathy_ratio > 0.05:
        traits.append(_make_trait("empathetic", empathy_ratio, messages, r'\b(?:sorry|hope|care)\b'))

    if sentiment > 0.3:
        traits.append(PersonalityTrait(trait="positive", score=sentiment, intensity="strong",
                                       evidence=_get_evidence(messages, r'\b(?:love|great|awesome|amazing)\b', 3)))
    elif sentiment > 0.1:
        traits.append(PersonalityTrait(trait="positive", score=sentiment, intensity="moderate",
                                       evidence=_get_evidence(messages, r'\b(?:love|great|awesome|amazing)\b', 3)))
    elif sentiment < -0.1:
        traits.append(PersonalityTrait(trait="negative", score=abs(sentiment), intensity="moderate",
                                       evidence=_get_evidence(messages, r'\b(?:hate|terrible|awful)\b', 3)))

    traits.sort(key=lambda t: t.score, reverse=True)
    return traits


def _make_trait(name: str, score: float, messages: List[Message], pattern: str) -> PersonalityTrait:
    intensity = "strong" if score > 0.3 else "moderate" if score > 0.1 else "mild"
    evidence = _get_evidence(messages, pattern, 3)
    return PersonalityTrait(trait=name, score=score, intensity=intensity, evidence=evidence)


def _get_evidence(messages: List[Message], pattern: str, max_count: int) -> List[PersonaEvidence]:
    evidence = []
    for m in messages:
        if re.search(pattern, m.text, re.I):
            evidence.append(PersonaEvidence(text=m.text[:150], message_idx=m.global_idx))
            if len(evidence) >= max_count:
                break
    return evidence


def _analyze_comm_style(messages: List[Message]) -> CommunicationStyle:
    """Statistical analysis of communication patterns."""
    if not messages:
        return CommunicationStyle()

    total = len(messages)
    lengths_chars = [len(m.text) for m in messages]
    lengths_words = [len(m.text.split()) for m in messages]
    avg_chars = sum(lengths_chars) / total
    avg_words = sum(lengths_words) / total

    # Emoji usage
    emoji_count = sum(len(EMOJI_RE.findall(m.text)) for m in messages)
    emoji_rate = emoji_count / total

    # Question and exclamation ratios
    question_count = sum(1 for m in messages if '?' in m.text)
    excl_count = sum(1 for m in messages if '!' in m.text)

    # Top 10 words (excluding stopwords)
    all_words = []
    for m in messages:
        words = re.findall(r'\b[a-z]{3,}\b', m.text.lower())
        all_words.extend(w for w in words if w not in STOPWORDS_FOR_TOP_WORDS)
    top_words = [w for w, _ in Counter(all_words).most_common(10)]

    # Capitalization style
    all_upper = sum(1 for m in messages if m.text.isupper() and len(m.text) > 3)
    cap_style = "shouts" if all_upper > total * 0.1 else "normal"

    # Punctuation patterns
    ellipsis = sum(1 for m in messages if '...' in m.text)
    punct = {
        "question_marks_per_msg": round(question_count / total, 3),
        "exclamation_per_msg": round(excl_count / total, 3),
        "ellipsis_per_msg": round(ellipsis / total, 3),
    }

    # Message length distribution
    short = sum(1 for w in lengths_words if w < 8)
    medium = sum(1 for w in lengths_words if 8 <= w < 25)
    long = sum(1 for w in lengths_words if w >= 25)

    return CommunicationStyle(
        avg_words_per_message=avg_words,
        avg_chars_per_message=avg_chars,
        emoji_usage_rate=emoji_rate,
        question_ratio=question_count / total,
        exclamation_ratio=excl_count / total,
        top_words=top_words,
        capitalization_style=cap_style,
        punctuation_patterns=punct,
        message_length_distribution={"short": short, "medium": medium, "long": long},
    )
