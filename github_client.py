import os
import requests
from typing import Dict, Any, List

# this file calls the Github API query

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def search_repositories(params: Dict[str, str]) -> Dict[str, Any]:
    """
    Execute GitHub repository search API request.
    A GitHub token is optional for public repository search,
    but using one can reduce rate-limit problems.
    """
    headers = {
        "Accept": "application/vnd.github+json", # receive JSON response
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # type export GITHUB_TOKEN="your_token_here" in bash if have token
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        GITHUB_SEARCH_URL,
        headers=headers,
        params=params,
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub API error {response.status_code}: {response.text}"
        )

    return response.json()


def simplify_results(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Keep only the fields useful for displaying CLI results.
    """
    simplified = []

    for item in api_response.get("items", []):
        simplified.append(
            {
                "full_name": item.get("full_name"),
                "description": item.get("description"),
                "stars": item.get("stargazers_count"),
                "forks": item.get("forks_count"),
                "language": item.get("language"),
                "url": item.get("html_url"),
                "updated_at": item.get("updated_at"),
            }
        )

    return simplified