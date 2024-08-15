import json

from openai import OpenAI

from models import Translation, Destination, Example

client = OpenAI()

JSON_SCHEMA = {
    "src": "string",
    "dst": [
        {
            "value": "string",
            "examples": [{"src": "string", "dst": "string"}],
        }
    ],
}


def translate(
    value: str,
    src_lang: str,
    dst_lang: str,
    translation_count: int,
    examples_per_translation_count: int,
) -> Translation:

    json_schema_str = json.dumps(JSON_SCHEMA)

    system_message = (
        "Given a term, source and destination languages, "
        "correct the term from typos and provide it as 'src'. "
        f"Translate it using up to {translation_count} translations, "
        f"with {examples_per_translation_count} examples for each. "
        "If the term is not valid or recognized, return an empty JSON object. "
        f"Return in JSON format: {{{json_schema_str}}}"
    )

    user_message = f"Translate '{value}' from {src_lang} to {dst_lang}."

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=300,
        top_p=1,
    )

    content = response.choices[0].message.content

    json_object = json.loads(content)

    if not "src" in json_object:
        return None

    return Translation(
        src=json_object["src"],
        dst=[
            Destination(
                value=dst["value"],
                examples=[
                    Example(src=example["src"], dst=example["dst"])
                    for example in dst["examples"]
                ],
            )
            for dst in json_object["dst"]
        ],
    )
