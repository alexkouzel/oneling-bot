import linguee.api

type Example = tuple[str, str]

type QueryOverview = tuple[str, list[str], list[Example]]


async def get_examples(query: str, src: str, dst: str) -> list[Example]:
    lemmas = await linguee.api.translations(query, src, dst)
    return _extract_examples(lemmas) if lemmas else None


async def get_translations(query: str, src: str, dst: str) -> list[str]:
    lemmas = await linguee.api.translations(query, src, dst)
    return _extract_translations(lemmas) if lemmas else None


async def get_query_overview(query: str, src: str, dst: str) -> QueryOverview:
    lemmas = await linguee.api.translations(query, src, dst)

    if not lemmas:
        return None

    translations = _extract_translations(lemmas)
    examples = _extract_examples(lemmas)

    return lemmas[0].text, translations, examples


def _extract_translations(lemmas) -> list[str]:
    return list({translation.text for lemma in lemmas for translation in lemma.translations})


def _extract_examples(lemmas) -> list[Example]:
    return list({
        (example.src, example.dst)
        for lemma in lemmas
        for translation in lemma.translations
        for example in translation.examples
    })
