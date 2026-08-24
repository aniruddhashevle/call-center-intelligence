import re


INJECTION_PATTERNS = [
    (re.compile(r"\bignore\s+(all\s+)?previous\s+instructions?\b", re.I), "ignore_previous"),
    (re.compile(r"\bignore\s+(all\s+)?prior\s+instructions?\b", re.I), "ignore_prior"),
    (re.compile(r"\bdisregard\s+(all\s+)?prior\s+instructions?\b", re.I), "disregard_prior"),
    (re.compile(r"\bforget\s+(all\s+)?previous\s+instructions?\b", re.I), "forget_previous"),
    (re.compile(r"\b(?:show|reveal|give|tell)\s+(?:me\s+)?(?:the\s+)?(?:system|original)\s+prompt\b", re.I), "prompt_leak"),
    (re.compile(r"\bwhat\s+(?:is|was)\s+(?:your\s+)?system\s+prompt\b", re.I), "prompt_leak_question"),
    (re.compile(r"\b(?:inject|insert)\s+(?:a\s+)?system\s+prompt\b", re.I), "system_prompt_inject"),
    (re.compile(r"<<SYS>>", re.I), "llama_system_tag"),
    (re.compile(r"\[INST\]", re.I), "llama_inst_tag"),
    (re.compile(r"\[/INST\]", re.I), "llama_inst_close_tag"),
    (re.compile(r"\b(?:you are now|act as|pretend to be)\s+(?:an?\s+)?(?:admin|developer|system)\b", re.I), "role_switch"),
    (re.compile(r"\b(?:new|updated|replacement)\s+instructions?\s*:", re.I), "new_instructions"),
    (re.compile(r"\b(?:enable|activate|enter)\s+DAN\s+mode\b", re.I), "dan_mode"),
    (re.compile(r"\b(?:jailbreak|jailbroken)\b", re.I), "jailbreak"),
    (re.compile(r"\boverride\s+(?:all\s+)?safety\b", re.I), "override_safety"),
    (re.compile(r"\bignore\s+(?:the\s+)?transcript\b", re.I), "ignore_transcript"),
    (re.compile(r"\b(?:inject|insert)\s+(?:into|within)\s+(?:the\s+)?conversation\b", re.I), "conversation_inject"),
    (re.compile(r"\b(?:verify|confirm)\s+(?:your\s+)?identity\s+by\s+(?:giving|providing|revealing)\b", re.I), "social_engineering"),
    (re.compile(r"\btranslate\s+(?:the\s+following\s+)?(?:instructions?|prompt)\b", re.I), "translate_attack"),
    (re.compile(r"\bignore\s+(?:all\s+)?safety\s+(?:rules?|guidelines?|instructions?)\b", re.I), "ignore_safety"),
    (re.compile(r"\b(?:override|bypass)\s+(?:the\s+)?system\b", re.I), "system_override"),
    (re.compile(r"\b(?:reveal|expose|disclose)\s+(?:your\s+)?(?:hidden|secret)\s+(?:instructions?|prompt)\b", re.I), "reveal_attack"),
]


def detect_prompt_injection(text: str) -> list[str]:
    """
    Return the names of injection patterns detected in text.
    """
    detected = []

    for pattern, name in INJECTION_PATTERNS:
        if pattern.search(text):
            detected.append(name)

    return detected


def is_prompt_injection(text: str) -> bool:
    """Return True if any prompt-injection pattern is detected."""
    return bool(detect_prompt_injection(text))