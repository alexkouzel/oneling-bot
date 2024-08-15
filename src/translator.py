import json

from openai import OpenAI

from models import Translation, Destination, Example

client = OpenAI()

JSON_SCHEMA = {
    "corrected_term": "string",
    "translations": [
        {
            "value": "string",
            "examples": [{"src": "string", "dst": "string"}],
        }
    ],
    "definition": "string",
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
        "correct all errors, including typos, grammatical errors, incorrect collocations, improper word choices, and non-idiomatic expressions. "
        "For example, if the input is 'ik ben hunger', correct it to 'ik heb honger'. "
        f"Translate the corrected term or phrase using up to {translation_count} unique and non-redundant translations. "
        "Each translation must be distinct in wording, phrasing, or style, and must not simply be a rewording or synonym substitution of the same translation. "
        f"For each translation, provide {examples_per_translation_count} unique and non-redundant examples. "
        "Each example must be provided in both the source language (marked as 'src') and the destination language (marked as 'dst'). "
        "Ensure that each example offers a distinct context, scenario, or usage, avoiding repetition of similar sentences or ideas. "
        "Include the term's definition in the source language. "
        "If the term is not in the source language, is invalid, or unrecognized, return an empty JSON object. "
        f"Format the response as JSON: {{{json_schema_str}}}"
    )

    user_message = f"Term: {value}; Source language: {src_lang}; Destination language: {dst_lang}"

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=400,
        top_p=1,
    )

    content = response.choices[0].message.content

    json_object = json.loads(content)

    if not "corrected_term" in json_object:
        return None

    return Translation(
        src=json_object["corrected_term"],
        dst=[
            Destination(
                value=dst["value"],
                examples=[
                    Example(src=example["src"], dst=example["dst"])
                    for example in dst["examples"]
                ],
            )
            for dst in json_object["translations"]
        ],
        definition=json_object["definition"],
    )
