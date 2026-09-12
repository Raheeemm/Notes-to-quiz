import json
import os
import re
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

load_dotenv()


# ---------------------------------------------------------
# LLM CLIENT
# ---------------------------------------------------------

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")


# ---------------------------------------------------------
# PROMPT
# ---------------------------------------------------------

SYSTEM_PROMPT = """You are a study assistant that turns study notes into
a useful revision quiz.

Read the study notes provided by the user and produce:

1. A concise summary of the key ideas in 3 to 5 sentences.
2. Exactly 10 multiple-choice questions.

DIFFICULTY DISTRIBUTION:

- Questions 1-3: easy
- Questions 4-7: medium
- Questions 8-10: hard

DIFFICULTY GUIDELINES:

Easy:
Test direct understanding and recall of important concepts explicitly
stated in the notes.

Medium:
Test relationships, processes, causes and effects, comparisons,
and distinctions between concepts in the notes.

Hard:
Require applying, comparing, sequencing, or reasoning from information
contained in the notes.

IMPORTANT:
Hard questions must still be answerable using ONLY the supplied notes.
Do not introduce outside facts.

QUESTION RULES:

- Exactly 10 questions.
- Every question must be based only on the supplied notes.
- Every question must have exactly 4 options.
- Exactly 1 option must be correct.
- Wrong options must be plausible.
- Do not use obvious filler such as "None of the above".
- Include a short explanation for every question.
- correct_index must be the 0-based position of the correct option.
- difficulty must be exactly "easy", "medium", or "hard".
- Do not include any information that cannot reasonably be derived from
  the notes.

RETURN FORMAT:

Return ONLY one valid JSON object.

Do not use markdown.
Do not use code fences.
Do not include commentary before or after the JSON.

The JSON must have exactly this structure:

{
  "summary": "A 3 to 5 sentence summary.",
  "questions": [
    {
      "question": "Question text",
      "options": [
        "Option 1",
        "Option 2",
        "Option 3",
        "Option 4"
      ],
      "correct_index": 0,
      "explanation": "Why this answer is correct.",
      "difficulty": "easy"
    }
  ]
}

The questions array must contain exactly 10 objects.
"""


# ---------------------------------------------------------
# PYDANTIC MODELS
# ---------------------------------------------------------

class Question(BaseModel):
    question: str

    options: list[str] = Field(
        min_length=4,
        max_length=4,
    )

    correct_index: int = Field(
        ge=0,
        le=3,
    )

    explanation: str

    difficulty: Literal["easy", "medium", "hard"]


class StudySet(BaseModel):
    summary: str

    questions: list[Question] = Field(
        min_length=10,
        max_length=10,
    )


# ---------------------------------------------------------
# CALL MODEL
# ---------------------------------------------------------

def _call_model(messages: list[dict]) -> str:
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.4,
    }

    # Ask the model for JSON when the provider supports it.
    try:
        response = client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )

    except Exception as exc:
        print(
            f"[llm] JSON response format unavailable, "
            f"retrying normally: {exc}"
        )

        response = client.chat.completions.create(**kwargs)

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "The model returned an empty response."
        )

    return content


# ---------------------------------------------------------
# EXTRACT JSON
# ---------------------------------------------------------

def _extract_json(raw: str) -> str:
    """
    Extract the outermost JSON object from the model response.

    Handles:
    - plain JSON
    - ```json ... ```
    - accidental text before/after JSON
    - nested JSON objects
    - braces inside JSON strings
    """

    text = raw.strip()

    # Remove markdown code fences if the model adds them.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    start = text.find("{")

    if start == -1:
        raise ValueError(
            "The model did not return anything resembling "
            "a JSON object."
        )

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        char = text[i]

        if in_string:

            if escape:
                escape = False

            elif char == "\\":
                escape = True

            elif char == '"':
                in_string = False

            continue

        if char == '"':
            in_string = True

        elif char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return text[start:i + 1]

    raise ValueError(
        "The model returned incomplete JSON."
    )


# ---------------------------------------------------------
# GENERATE STUDY SET
# ---------------------------------------------------------

def generate_study_set(notes: str) -> StudySet:

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Here are the study notes. "
                "Use ONLY these notes to create the quiz:\n\n"
                f"{notes}"
            ),
        },
    ]

    last_error = ""

    for attempt in range(2):

        raw = ""

        try:
            raw = _call_model(messages)

            print(
                f"[llm] attempt {attempt + 1} received response"
            )

            # Extract JSON from the response.
            json_text = _extract_json(raw)

            # Parse JSON.
            data = json.loads(json_text)

            # Validate against our schema.
            study_set = StudySet.model_validate(data)

            print(
                f"[llm] attempt {attempt + 1} accepted"
            )

            return study_set

        except (
            json.JSONDecodeError,
            ValidationError,
            ValueError,
        ) as exc:

            last_error = str(exc)

            print(
                f"[llm] attempt {attempt + 1} rejected: "
                f"{last_error}"
            )

            # Give the model one opportunity to fix its response.
            if attempt == 0:

                messages = messages + [
                    {
                        "role": "assistant",
                        "content": raw,
                    },
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was rejected by "
                            "the validator.\n\n"

                            "Generate the study set again and return "
                            "ONLY a valid JSON object.\n\n"

                            "The corrected response MUST contain:\n"
                            "- exactly 10 questions\n"
                            "- questions 1-3 difficulty = easy\n"
                            "- questions 4-7 difficulty = medium\n"
                            "- questions 8-10 difficulty = hard\n"
                            "- exactly 4 options per question\n"
                            "- exactly 1 correct answer per question\n"
                            "- correct_index as an integer from 0 to 3\n"
                            "- an explanation for every question\n"
                            "- a summary field\n\n"

                            "Do not return markdown or any prose.\n\n"

                            f"Validation error:\n{last_error}"
                        ),
                    },
                ]

    raise ValueError(
        "Failed to generate a valid study set after 2 attempts. "
        f"Last error: {last_error}"
    )