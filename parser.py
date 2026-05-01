import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict

# this file converts nl into a structured Github API query
# checks sentences category by category from ParsedGitHubQuery
# the rest of the words go to search_terms

@dataclass
class ParsedGitHubQuery:
    original_query: str
    search_terms: str
    language: Optional[str] = None
    min_stars: Optional[int] = None
    max_stars: Optional[int] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    pushed_after: Optional[str] = None
    license_name: Optional[str] = None
    exclude_terms: List[str] = field(default_factory=list)
    sort: str = "stars"
    order: str = "desc"
    per_page: int = 10
    warnings: List[str] = field(default_factory=list)

    def to_github_q(self) -> str:
        """
        Convert structured fields into GitHub's repository search q string.
        This converts the extracted info into GitHub's search syntax and builds
        the final q string for GitHub

        Ex: machine learning language:Python stars:>1000 created:>2021-01-01
        """
        parts = []

        if self.search_terms:
            parts.append(self.search_terms)

        if self.language:
            parts.append(f"language:{self.language}")

        if self.min_stars is not None:
            parts.append(f"stars:>{self.min_stars}")

        if self.max_stars is not None:
            parts.append(f"stars:<{self.max_stars}")

        if self.created_after:
            parts.append(f"created:>{self.created_after}")

        if self.created_before:
            parts.append(f"created:<{self.created_before}")

        if self.pushed_after:
            parts.append(f"pushed:>{self.pushed_after}")

        if self.license_name:
            parts.append(f"license:{self.license_name}")

        for term in self.exclude_terms:
            parts.append(f"-{term}")

        return " ".join(parts).strip()

    def to_api_params(self) -> Dict[str, str]:
        # turns parsed query into API params
        return {
            "q": self.to_github_q(),
            "sort": self.sort,
            "order": self.order,
            "per_page": str(self.per_page),
        }

# supports shortcut, typos, and simple chinese translations
LANGUAGES = {
    "python": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "dart": "Dart",
    "r": "R",
    "julia": "Julia",
    "shell": "Shell",
    "bash": "Shell",
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

TYPO_FIXES = {
    "pyton": "python",
    "pyhton": "python",
    "javasript": "javascript",
    "javscript": "javascript",
    "machien": "machine",
    "lerning": "learning",
    "lernig": "learning",
    "artifical": "artificial",
    "inteligence": "intelligence",
    "repos": "repositories",
    "repo": "repository",
}

CHINESE_TRANSLATIONS = {
    "機器學習": "machine learning",
    "人工智慧": "artificial intelligence",
    "深度學習": "deep learning",
    "電腦視覺": "computer vision",
    "資料科學": "data science",
    "專案": "repository",
    "程式庫": "repository",
    "找出": "find",
    "搜尋": "search",
    "關於": "about",
    "星星": "stars",
    "最多": "top",
    "最近更新": "recently updated",
}


def normalize_text(text: str) -> str:
    normalized = text.strip()

    for zh, en in CHINESE_TRANSLATIONS.items():
        normalized = normalized.replace(zh, en)

    words = normalized.split()
    fixed_words = []

    for word in words:
        clean = word.lower().strip(".,!?;:")
        fixed_words.append(TYPO_FIXES.get(clean, word))

    return " ".join(fixed_words)


def extract_limit(text: str) -> int:
    """
    Extract top N / first N / limit N.
    Default = 10
    """
    lowered = text.lower()

    number_match = re.search(r"\b(?:top|first|show|give me|find)\s+(\d{1,3})\b", lowered)
    if number_match:
        return min(max(int(number_match.group(1)), 1), 100)

    for word, number in NUMBER_WORDS.items():
        if re.search(rf"\b(?:top|first|show|give me|find)\s+{word}\b", lowered):
            return number

    return 10


def extract_language(text: str) -> Optional[str]:
    lowered = text.lower()

    # Special handling so "go" does not match normal English "go"
    if re.search(r"\bgolang\b", lowered):
        return "Go"

    for key, value in LANGUAGES.items():
        if key == "go":
            if re.search(r"\bgo repositories\b|\bgo projects\b|\blanguage go\b|\bin go\b", lowered):
                return value
        elif re.search(rf"\b{re.escape(key)}\b", lowered):
            return value

    return None


def extract_stars(text: str) -> tuple[Optional[int], Optional[int]]:
    lowered = text.lower()
    min_stars = None
    max_stars = None

    patterns_min = [
        r"more than (\d+) stars",
        r"over (\d+) stars",
        r"at least (\d+) stars",
        r"minimum (\d+) stars",
        r"stars\s*>\s*(\d+)",
    ]

    patterns_max = [
        r"less than (\d+) stars",
        r"under (\d+) stars",
        r"fewer than (\d+) stars",
        r"stars\s*<\s*(\d+)",
    ]

    for pattern in patterns_min:
        match = re.search(pattern, lowered)
        if match:
            min_stars = int(match.group(1))

    for pattern in patterns_max:
        match = re.search(pattern, lowered)
        if match:
            max_stars = int(match.group(1))

    return min_stars, max_stars


def extract_dates(text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    lowered = text.lower()
    current_year = date.today().year

    created_after = None
    created_before = None
    pushed_after = None

    # created after 2020 / after 2020
    match = re.search(r"(?:created after|after)\s+(\d{4})", lowered)
    if match:
        created_after = f"{match.group(1)}-12-31"

    # created before 2020 / before 2020
    match = re.search(r"(?:created before|before)\s+(\d{4})", lowered)
    if match:
        created_before = f"{match.group(1)}-01-01"

    # updated this year
    if "updated this year" in lowered or "recently updated" in lowered:
        pushed_after = f"{current_year}-01-01"

    # last year
    if "last year" in lowered:
        last_year = current_year - 1
        created_after = f"{last_year}-01-01"
        created_before = f"{last_year}-12-31"

    return created_after, created_before, pushed_after


def extract_license(text: str) -> Optional[str]:
    lowered = text.lower()

    license_map = {
        "mit": "mit",
        "apache": "apache-2.0",
        "apache 2": "apache-2.0",
        "gpl": "gpl",
        "bsd": "bsd",
    }

    for key, value in license_map.items():
        if re.search(rf"\b{re.escape(key)}\b", lowered):
            return value

    return None


def extract_exclusions(text: str) -> List[str]:
    lowered = text.lower()
    exclusions = []

    # Example: "not machine learning"
    not_matches = re.findall(r"\bnot\s+([a-zA-Z0-9+#.\- ]+?)(?:\s+with|\s+in|\s+created|\s+updated|$)", lowered)
    for match in not_matches:
        cleaned = match.strip()
        if cleaned:
            exclusions.append(cleaned.replace(" ", "-"))

    # Example: "without tensorflow"
    without_matches = re.findall(r"\bwithout\s+([a-zA-Z0-9+#.\-]+)", lowered)
    for match in without_matches:
        exclusions.append(match.strip())

    return exclusions


def infer_sort(text: str) -> tuple[str, str]:
    lowered = text.lower()

    if "newest" in lowered or "recently created" in lowered:
        return "created", "desc"

    if "recently updated" in lowered or "updated this year" in lowered:
        return "updated", "desc"

    if "most forks" in lowered or "forked" in lowered:
        return "forks", "desc"

    # Default: popularity by stars
    return "stars", "desc"


def clean_search_terms(text: str, language: Optional[str]) -> str:
    """
    Remove command words and constraints so the remaining phrase becomes search terms.
    """
    lowered = text.lower()

    remove_patterns = [
        r"\bfind\b",
        r"\bshow me\b",
        r"\bshow\b",
        r"\bgive me\b",
        r"\bsearch\b",
        r"\brepositories\b",
        r"\brepository\b",
        r"\brepos\b",
        r"\brepo\b",
        r"\bprojects\b",
        r"\bproject\b",
        r"\btop\s+\d+\b",
        r"\bfirst\s+\d+\b",
        r"\bwith more than \d+ stars\b",
        r"\bmore than \d+ stars\b",
        r"\bover \d+ stars\b",
        r"\bat least \d+ stars\b",
        r"\bminimum \d+ stars\b",
        r"\bless than \d+ stars\b",
        r"\bunder \d+ stars\b",
        r"\bfewer than \d+ stars\b",
        r"\bcreated after \d{4}\b",
        r"\bcreated before \d{4}\b",
        r"\bafter \d{4}\b",
        r"\bbefore \d{4}\b",
        r"\bupdated this year\b",
        r"\brecently updated\b",
        r"\blast year\b",
        r"\bmost starred\b",
        r"\bpopular\b",
        r"\bbest\b",
        r"\bnewest\b",
        r"\babout\b",
        r"\brelated to\b",
        r"\bfor\b",
        r"\bin\b",
        r"\blanguage\b",
        r"\bmit\b",
        r"\bapache 2\b",
        r"\bapache\b",
        r"\bgpl\b",
        r"\bbsd\b",
    ]

    if language:
        remove_patterns.append(rf"\b{re.escape(language.lower())}\b")

    cleaned = lowered

    for pattern in remove_patterns:
        cleaned = re.sub(pattern, " ", cleaned)

    # Remove exclusions from search terms
    cleaned = re.sub(r"\bnot\s+[a-zA-Z0-9+#.\- ]+", " ", cleaned)
    cleaned = re.sub(r"\bwithout\s+[a-zA-Z0-9+#.\-]+", " ", cleaned)

    cleaned = re.sub(r"[^a-zA-Z0-9+#.\- ]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def validate_query(parsed: ParsedGitHubQuery) -> ParsedGitHubQuery:
    """
    Hardened validation layer.
    It catches conflicting constraints and vague queries.
    """
    if not parsed.search_terms and not parsed.language:
        parsed.warnings.append(
            "The query is too vague. Please include a topic, language, or constraint."
        )

    if parsed.min_stars is not None and parsed.max_stars is not None:
        if parsed.min_stars >= parsed.max_stars:
            parsed.warnings.append(
                "Conflicting star constraints: minimum stars is greater than or equal to maximum stars."
            )

    if parsed.created_after and parsed.created_before:
        if parsed.created_after >= parsed.created_before:
            parsed.warnings.append(
                "Conflicting date constraints: created_after is later than or equal to created_before."
            )

    if parsed.per_page < 1:
        parsed.per_page = 10

    if parsed.per_page > 100:
        parsed.per_page = 100
        parsed.warnings.append("GitHub API per_page maximum is 100, so the limit was capped at 100.")

    return parsed


def parse_natural_language_query(query: str) -> ParsedGitHubQuery:
    normalized = normalize_text(query)

    language = extract_language(normalized)
    min_stars, max_stars = extract_stars(normalized)
    created_after, created_before, pushed_after = extract_dates(normalized)
    license_name = extract_license(normalized)
    exclude_terms = extract_exclusions(normalized)
    sort, order = infer_sort(normalized)
    per_page = extract_limit(normalized)
    search_terms = clean_search_terms(normalized, language)

    parsed = ParsedGitHubQuery(
        original_query=query,
        search_terms=search_terms,
        language=language,
        min_stars=min_stars,
        max_stars=max_stars,
        created_after=created_after,
        created_before=created_before,
        pushed_after=pushed_after,
        license_name=license_name,
        exclude_terms=exclude_terms,
        sort=sort,
        order=order,
        per_page=per_page,
    )

    return validate_query(parsed)