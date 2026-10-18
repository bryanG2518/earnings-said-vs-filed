"""Hard refusal for recommendation requests, including follow-ups."""
import re

PATTERNS = [
    # direct asks
    r"\bshould i (be worried|worry|dump|trim|add|keep|exit|double down|buy|sell|hold|invest|short|get out|get in|own)\b",
    r"\bwould you (invest|buy|sell|add|trim|hold|own|short|keep)\b",
    r"\b(is|are) (it|this|they|\w+) a (good |bad |smart |strong )?(buy|sell|hold)\b",
    r"\b(is|are) (it|this|they|\w+) a (good|bad|smart) (investment|stock)\b",
    r"\b(buy|sell) or (hold|sell|buy)\b", r"\bprice target\b",
    r"\bworth (buying|investing|owning)\b", r"\bgood time to (buy|sell|invest)\b",
    # position management
    r"\b(add to|trim|exit|close|reduce|increase) my (position|shares|stake|holding)",
    # valuation verdicts
    r"\b(undervalued|overvalued)\b", r"\b(fair|intrinsic) value\b",
    r"\bwhat('s| is) (\w+ )?(stock )?worth\b", r"\brate (this|the|that) stock\b",
    # price direction
    r"\b(is|will) (\w+ )?(stock |shares |it )?(going to |gonna )?(go|rise|fall|drop|climb|tank|rally)( up| down)?\b.*\?",
    r"\b(stock|shares|price) (going to|gonna|will) (go|rise|fall|drop|climb)\b",
    r"\bwhat would you do with\b",
]
RESPONSE = ("Earnings Said vs. Filed describes what companies filed with the "
            "SEC. It doesn't make recommendations, price targets, or "
            "buy/sell/hold calls. I can walk through any finding in the "
            "brief and the filing it came from. For advice about your own "
            "situation, a licensed financial professional is the right "
            "person to ask.")


def is_advice_request(text):
    low = text.lower()
    return any(re.search(p, low) for p in PATTERNS)
