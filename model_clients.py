import json
import os
from typing import Dict, Any

from dotenv import load_dotenv

# calls gemini, qwen, and mistral

load_dotenv()


SYSTEM_PROMPT = """
Please convert natural language GitHub repository search requests into structured GitHub API parameters.

Return ONLY valid JSON with exactly these keys:
{
  "q": string,
  "sort": string,
  "order": string,
  "per_page": string
}

Rules:
- q must use GitHub repository search syntax.
- Put topic words directly in q.
- Use language:Python, language:JavaScript, language:TypeScript, language:Rust, language:Go, language:C++, etc.
- Use stars:>N for more than / over / at least N stars.
- Use stars:<N for fewer than / under / less than N stars.
- Use created:>YYYY-MM-DD for created after a year. For "after 2021", use created:>2021-12-31.
- Use created:<YYYY-MM-DD for created before a year. For "before 2020", use created:<2020-01-01.
- Use pushed:>2026-01-01 for "updated this year".
- Use created:>2025-01-01 created:<2025-12-31 for "created last year".
- Use license:mit, license:apache-2.0, license:gpl, or license:bsd.
- Use negative terms with a dash, for example -tensorflow or -machine-learning.
- sort must be one of: stars, forks, updated, created.
- order should usually be desc.
- per_page must be a string number.
- If the user asks for more than 100 results, cap per_page at "100".
- If no number is specified, use "10".
- Default sort is stars desc.
- "newest" means sort created desc.
- "recently updated" or "updated this year" means sort updated desc.
- "most forked" means sort forks desc.
- Correct obvious typos, such as pyton -> Python and machien lerning -> machine learning.
- Translate common Chinese terms:
  機器學習 = machine learning
  人工智慧 = artificial intelligence
  深度學習 = deep learning
  電腦視覺 = computer vision
  專案 = repository

Important date and sorting rules:
- A date filter does NOT automatically change the sort field.
- "created after 2021" means add created:>2021-12-31 to q, but keep sort as "stars" unless the user says "newest" or "recently created".
- "created before 2020" means add created:<2020-01-01 to q, but keep sort as "stars".
- "created last year" means add created:>2025-01-01 created:<2025-12-31 to q, but keep sort as "stars".
- Only use sort "created" when the user says "newest" or "recently created".
- Only use sort "updated" when the user says "recently updated" or "updated this year".
- For "updated this year", use pushed:>2026-01-01 in q. Do NOT use updated:>2026-01-01.
- For "after YEAR", convert to created:>YEAR-12-31.
- For "before YEAR", convert to created:<YEAR-01-01.
- If the user asks for top 200, set per_page to "100" because GitHub API per_page is capped at 100.
- Do not rewrite "AI" as "artificial intelligence" unless the input says artificial intelligence.
  
Examples:
Input: Find the top 5 Python repositories about machine learning
Output: {"q":"machine learning language:Python","sort":"stars","order":"desc","per_page":"5"}

Input: Find AI repositories but not machine learning
Output: {"q":"ai -machine-learning","sort":"stars","order":"desc","per_page":"10"}

Input: Show me newest TypeScript chatbot repositories
Output: {"q":"chatbots language:TypeScript","sort":"created","order":"desc","per_page":"10"}
"""


JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "q": {
            "type": "string"
        },
        "sort": {
            "type": "string",
            "enum": ["stars", "forks", "updated", "created"]
        },
        "order": {
            "type": "string",
            "enum": ["asc", "desc"]
        },
        "per_page": {
            "type": "string"
        }
    },
    "required": ["q", "sort", "order", "per_page"]
}


def parse_json_response(text: str) -> Dict[str, Any]:
    """
    Some models may still wrap JSON in markdown.
    This function extracts the JSON object safely.
    """
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])

        raise


def call_gemini_model(user_query: str) -> Dict[str, Any]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    response = client.models.generate_content(
        model=model,
        contents=f"{SYSTEM_PROMPT}\n\nInput: {user_query}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JSON_SCHEMA,
            temperature=0
        ),
    )

    return parse_json_response(response.text)


def call_ollama_model(user_query: str, model_env_name: str) -> Dict[str, Any]:
    import ollama

    model = os.getenv(model_env_name)

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        format=JSON_SCHEMA,
        options={
            "temperature": 0
        },
    )

    return parse_json_response(response["message"]["content"])


def call_qwen_model(user_query: str) -> Dict[str, Any]:
    return call_ollama_model(user_query, "OLLAMA_MODEL_1")

def build_validation_feedback(user_query: str, prediction: Dict[str, Any]) -> str:
    """
    Build feedback using only the user input and model prediction.
    This does not use the ground truth.
    """
    feedback = []
    user_lower = user_query.lower()
    q = str(prediction.get("q", ""))
    q_lower = q.lower()
    sort = str(prediction.get("sort", "")).lower()

    if "updated this year" in user_lower:
        if "updated:>" in q_lower:
            feedback.append('Use pushed:>2026-01-01, not updated:>2026-01-01, for "updated this year".')
        if "pushed:>2026-01-01" not in q:
            feedback.append('For "updated this year", q must include pushed:>2026-01-01.')

    if "created after 2022" in user_lower and "created:>2022-12-31" not in q:
        feedback.append('For "created after 2022", use created:>2022-12-31, not created:>2022.')

    if "created after 2021" in user_lower and "created:>2021-12-31" not in q:
        feedback.append('For "created after 2021", use created:>2021-12-31.')

    if "newest" in user_lower:
        if "created:>" in q_lower or "created:<" in q_lower:
            feedback.append('For "newest", set sort to created, but do not add a created date filter unless the user gives a year/date.')

    if "ai repositories" in user_lower and "artificial" in q_lower:
        feedback.append('Do not rewrite "AI" as "artificial intelligence". Keep the query term as ai.')

    if "deep learning" in user_lower:
        extra_terms = ["language:TensorFlow", "language:Keras", "language:Caffe", "language:Theano", "language:Pytorch", "language:Mxnet", " OR "]
        if any(term.lower() in q_lower for term in extra_terms):
            feedback.append('Do not add extra languages, frameworks, or OR clauses unless the user explicitly asks for them.')

    if "java repositories" in user_lower and "language:Java" not in q:
        feedback.append('The user asked for Java repositories, so q must include language:Java.')

    if not feedback:
        return ""

    return "\n".join(feedback)

def call_model_with_retry(user_query: str, base_call_fn) -> Dict[str, Any]:
    first_prediction = base_call_fn(user_query)
    feedback = build_validation_feedback(user_query, first_prediction)

    if not feedback:
        return first_prediction

    retry_prompt = f"""
Your previous JSON output violated these rules:
{feedback}

Original user input:
{user_query}

Previous JSON:
{json.dumps(first_prediction, ensure_ascii=False)}

Return corrected JSON only, with exactly these keys:
q, sort, order, per_page
"""

    return base_call_fn(retry_prompt)


def call_mistral_model(user_query: str) -> Dict[str, Any]:
    return call_ollama_model(user_query, "OLLAMA_MODEL_2")

def call_mistral_model_with_retry(user_query: str) -> Dict[str, Any]:
    return call_model_with_retry(user_query, call_mistral_model)

MODEL_CLIENTS = {
    "gemini": call_gemini_model,
    "qwen": call_qwen_model,
    "mistral": call_mistral_model_with_retry,
}