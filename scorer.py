import re
from typing import Dict, Any, Tuple, List

# compares model output against ground truth


def normalize_q(q: str) -> str:
    q = str(q).strip()
    q = re.sub(r"\s+", " ", q)
    return q


def normalize_q_token(token: str) -> List[str]:
    """
    Normalize one token in the GitHub q string.

    This function always returns a LIST of strings.

    It ignores capitalization for normal search terms:
    React == react
    Android == android

    It also treats hyphenated normal topic phrases as equivalent:
    machine-learning == machine learning

    But it preserves negative terms:
    -machine-learning should stay as -machine-learning
    """
    token = token.strip()

    if not token:
        return []

    # Remove accidental API parameters that some models put inside q.
    # Example: "web-scraping language:Python sort:forks order:desc"
    if token.lower().startswith("sort:") or token.lower().startswith("order:"):
        return []

    # Fix common syntax mistake
    token = token.replace("language=", "language:")

    lower_token = token.lower()

    # Normalize language qualifiers
    language_map = {
        "language:python": "language:Python",
        "language:javascript": "language:JavaScript",
        "language:typescript": "language:TypeScript",
        "language:rust": "language:Rust",
        "language:go": "language:Go",
        "language:c++": "language:C++",
        "language:java": "language:Java",
        "language:ruby": "language:Ruby",
        "language:kotlin": "language:Kotlin",
        "language:swift": "language:Swift",
        "language:php": "language:PHP",
        "language:dart": "language:Dart",
        "language:shell": "language:Shell",
        "language:julia": "language:Julia",
        "language:r": "language:R",
    }

    if lower_token in language_map:
        return [language_map[lower_token]]

    # Normalize license qualifiers
    license_map = {
        "license:mit": "license:mit",
        "license:apache": "license:apache-2.0",
        "license:apache-2.0": "license:apache-2.0",
        "license:gpl": "license:gpl",
        "license:bsd": "license:bsd",
    }

    if lower_token in license_map:
        return [license_map[lower_token]]

    # Keep negative terms as negative terms.
    # -machine-learning should NOT become machine + learning.
    if token.startswith("-"):
        return [token.lower()]

    # Keep GitHub operators/qualifiers mostly unchanged.
    # This includes stars:>500, created:>2022-12-31, pushed:>2026-01-01.
    if ":" in token:
        key, value = token.split(":", 1)
        return [f"{key.lower()}:{value}"]

    # For normal topic terms, treat hyphen as a space.
    # machine-learning -> machine learning
    # web-scraping -> web scraping
    return token.lower().replace("-", " ").split()


def q_tokens(q: str) -> list[str]:
    """
    Compare q fields by token set, ignoring token order,
    harmless capitalization, and normal topic hyphenation.
    """
    q = normalize_q(q)

    tokens = []
    for token in q.split():
        tokens.extend(normalize_q_token(token))

    return sorted(tokens)


def normalize_api_params(params: Dict[str, Any]) -> Dict[str, str]:
    return {
        "q": normalize_q(params.get("q", "")),
        "sort": str(params.get("sort", "")).strip().lower(),
        "order": str(params.get("order", "")).strip().lower(),
        "per_page": str(params.get("per_page", "")).strip(),
    }


def score_prediction(
    prediction: Dict[str, Any],
    ground_truth: Dict[str, Any]
) -> Tuple[bool, Dict[str, bool]]:
    pred = normalize_api_params(prediction)
    truth = normalize_api_params(ground_truth)

    field_scores = {
        "q": q_tokens(pred["q"]) == q_tokens(truth["q"]),
        "sort": pred["sort"] == truth["sort"],
        "order": pred["order"] == truth["order"],
        "per_page": pred["per_page"] == truth["per_page"],
    }

    is_correct = all(field_scores.values())
    return is_correct, field_scores