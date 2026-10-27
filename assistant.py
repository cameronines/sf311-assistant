import json
from datetime import date
from dotenv import load_dotenv
import anthropic

from tools import (
    VALID_CATEGORIES, VALID_NEIGHBORHOODS,
    count_requests, recent_similar_requests, typical_resolution_time,
)

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-sonnet-5-5"

TOOL_FUNCTIONS = {
    "count_requests": count_requests,
    "recent_similar_requests": recent_similar_requests,
    "typical_resolution_time": typical_resolution_time,
}

CATEGORY = {"type": "string", "enum": VALID_CATEGORIES,
            "description": "311 request category. Pick the closest match."}
NEIGHBORHOOD = {"type": "string", "enum": VALID_NEIGHBORHOODS,
                "description": "San Francisco analysis neighborhood."}

TOOLS = [
    {
        "name": "count_requests",
        "description": "Count 311 requests of one category in one "
                       "neighborhood over the past N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": CATEGORY,
                "neighborhood": NEIGHBORHOOD,
                "days": {"type": "integer", "description": "Days to look back (default 30)."},
            },
            "required": ["category", "neighborhood"],
        },
    },
    {
        "name": "recent_similar_requests",
        "description": "List still-open recent requests of one category in one "
                       "neighborhood. Use to check whether an issue has "
                       "probably already been reported.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": CATEGORY,
                "neighborhood": NEIGHBORHOOD,
                "days": {"type": "integer", "description": "Days to look back (default 14)."},
                "limit": {"type": "integer", "description": "Max rows (default 10)."},
            },
            "required": ["category", "neighborhood"],
        },
    },
    {
        "name": "typical_resolution_time",
        "description": "Median days until requests of one category in one "
                       "neighborhood were closed, using cases filed 30-180 "
                       "days ago.",
        "input_schema": {
            "type": "object",
            "properties": {"category": CATEGORY, "neighborhood": NEIGHBORHOOD},
            "required": ["category", "neighborhood"],
        },
    },
]

SYSTEM = f"""You are an assistant that helps community volunteers understand
San Francisco 311 data. Today's date is {date.today().isoformat()}.

Rules:
- Answer only using the tools. Never guess numbers.
- If the question does not fit the tools (other cities, weather, opinions),
  say what you can and cannot help with.
- If the neighborhood or issue type is unclear, ask a short clarifying question.
- "Closed" means the city closed the case, not necessarily that the problem
  was fixed. Say "closed", not "fixed".
- Resolution times only include cases that closed, so mention the share closed.
- Report counts and patterns neutrally. Do not speculate about people or
  draw conclusions about why a neighborhood has more reports.
"""


def ask(question):
    messages = [{"role": "user", "content": question}]

    for _ in range(6):  # safety limit on back-and-forth
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  [tool] {block.name}({block.input})")
            try:
                output = TOOL_FUNCTIONS[block.name](**block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(output)})
            except Exception as err:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Error: {err}", "is_error": True})
        messages.append({"role": "user", "content": results})

    return "Sorry, I could not finish that request."


if __name__ == "__main__":
    print("Ask about SF 311 data (blank line to quit).")
    while True:
        q = input("\nQuestion: ").strip()
        if not q:
            break
        print("\n" + ask(q))