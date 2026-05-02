import argparse
import json
from pathlib import Path

from model_clients import MODEL_CLIENTS
from scorer import score_prediction

# main eval

def load_cases(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_model(model_name: str, cases_path: str):
    cases = load_cases(cases_path)
    model_fn = MODEL_CLIENTS[model_name]

    results = []
    correct_count = 0

    for case in cases:
        case_id = case["id"]
        user_input = case["input"]
        ground_truth = case["ground_truth"]

        print(f"\nEvaluating {model_name} on {case_id}: {user_input}")

        try:
            prediction = model_fn(user_input)
            is_correct, field_scores = score_prediction(prediction, ground_truth)

            if is_correct:
                correct_count += 1

            results.append(
                {
                    "id": case_id,
                    "input": user_input,
                    "ground_truth": ground_truth,
                    "prediction": prediction,
                    "correct": is_correct,
                    "field_scores": field_scores,
                }
            )

            print(f"Prediction: {prediction}")
            print(f"Ground truth: {ground_truth}")
            print(f"Field scores: {field_scores}")
            print(f"Correct: {is_correct}")

        except Exception as error:
            results.append(
                {
                    "id": case_id,
                    "input": user_input,
                    "ground_truth": ground_truth,
                    "prediction": None,
                    "correct": False,
                    "error": str(error),
                }
            )

            print(f"Error: {error}")

    total = len(cases)
    accuracy = correct_count / total if total else 0

    summary = {
        "model": model_name,
        "correct": correct_count,
        "total": total,
        "accuracy": accuracy,
        "results": results,
    }

    Path("eval_results").mkdir(exist_ok=True)

    output_path = f"eval_results/{model_name}_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"Model: {model_name}")
    print(f"Correct: {correct_count}/{total}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Saved results to {output_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate models on GitHub structured query generation."
    )

    parser.add_argument(
        "--model",
        choices=list(MODEL_CLIENTS.keys()) + ["all"],
        required=True,
        help="Model to evaluate: gemini, qwen, mistral, or all",
    )

    parser.add_argument(
        "--cases",
        default="eval_cases.json",
        help="Path to evaluation cases JSON file",
    )

    args = parser.parse_args()

    if args.model == "all":
        summaries = []

        for model_name in MODEL_CLIENTS:
            summaries.append(evaluate_model(model_name, args.cases))

        print("\nFinal comparison:")
        for summary in summaries:
            print(
                f"{summary['model']}: "
                f"{summary['correct']}/{summary['total']} "
                f"({summary['accuracy']:.2%})"
            )

    else:
        evaluate_model(args.model, args.cases)


if __name__ == "__main__":
    main()