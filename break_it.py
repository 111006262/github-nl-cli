from parser import parse_natural_language_query


BREAK_TESTS = [
    "Find the top 5 Python repositories about machine learning",
    "Find pyton repos about machien lerning",
    "找出關於機器學習的 Python 專案",
    "Show me popular repos",
    "Find JavaScript repositories about React with more than 1000 stars",
    "Find repositories with more than 5000 stars and less than 100 stars about AI",
    "Find Rust blockchain projects created after 2021",
    "Show me newest TypeScript chatbot repositories",
    "Find AI repositories but not machine learning",
    "Find repositories about computer vision updated this year",
    "Find top 200 Python repositories about data science",
    "Find Go repositories about web servers",
    "Find repositories about deep learning with MIT license",
]


def main():
    for query in BREAK_TESTS:
        parsed = parse_natural_language_query(query)

        print("=" * 80)
        print(f"Input: {query}")
        print(f"GitHub q: {parsed.to_github_q()}")
        print(f"API params: {parsed.to_api_params()}")

        if parsed.warnings:
            print("Warnings:")
            for warning in parsed.warnings:
                print(f"  - {warning}")

    print("=" * 80)


if __name__ == "__main__":
    main()