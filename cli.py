import argparse
import json

from parser import parse_natural_language_query
from github_client import search_repositories, simplify_results

# this is the command-line interface

def main():
    arg_parser = argparse.ArgumentParser(
        description="Natural language GitHub repository search CLI"
    )

    arg_parser.add_argument(
        "query",
        type=str,
        help="Natural language query, e.g. 'Find top 5 Python repos about machine learning'",
    )

    arg_parser.add_argument(
        "--show-query",
        action="store_true",
        help="Show the structured GitHub API query before executing",
    )

    arg_parser.add_argument(
        "--json",
        action="store_true",
        help="Output full simplified results as JSON",
    )

    args = arg_parser.parse_args()

    # take sent from user, send to parser.py then get structured API param
    parsed = parse_natural_language_query(args.query)
    api_params = parsed.to_api_params()

    print("\nNatural language input:")
    print(f"  {parsed.original_query}")

    print("\nStructured GitHub API request:")
    print(json.dumps(api_params, indent=2))

    if parsed.warnings:
        print("\nWarnings:")
        for warning in parsed.warnings:
            print(f"  - {warning}")

        if any("too vague" in warning.lower() or "conflicting" in warning.lower() for warning in parsed.warnings):
            print("\nStopping because the query needs clarification or has conflicting constraints.")
            return

    try:
        # send req to github and return json
        api_response = search_repositories(api_params)
        results = simplify_results(api_response)

        print(f"\nTotal matching repositories reported by GitHub: {api_response.get('total_count')}")

        if args.json:
            print(json.dumps(results, indent=2))
            return

        print("\nTop results:")
        for index, repo in enumerate(results, start=1):
            print(f"\n{index}. {repo['full_name']}")
            print(f"   Stars: {repo['stars']} | Forks: {repo['forks']} | Language: {repo['language']}")
            print(f"   Updated: {repo['updated_at']}")
            print(f"   URL: {repo['url']}")
            if repo["description"]:
                print(f"   Description: {repo['description']}")

    except Exception as error:
        print("\nError:")
        print(f"  {error}")


if __name__ == "__main__":
    main()