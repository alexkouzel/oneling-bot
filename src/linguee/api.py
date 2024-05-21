from linguee.config import settings
from linguee.const import LANGUAGE_CODE
from linguee.downloaders.httpx_downloader import HTTPXDownloader
from linguee.downloaders.memory_cache import MemoryCache
from linguee.downloaders.sqlite_cache import SQLiteCache
from linguee.client import LingueeClient
from linguee.models import FollowCorrections, ParseError
from linguee.parsers import XExtractParser

page_downloader = MemoryCache(
    upstream=SQLiteCache(
        cache_database=settings.cache_database,
        upstream=HTTPXDownloader(),
    )
)
client = LingueeClient(
    page_downloader=page_downloader,
    page_parser=XExtractParser(),
)


async def translations(
    query: str,
    src: LANGUAGE_CODE,
    dst: LANGUAGE_CODE,
    guess_direction: bool = False,
    follow_corrections: FollowCorrections = FollowCorrections.ALWAYS,
):
    result = await client.process_search_result(
        query=query,
        src=src,
        dst=dst,
        guess_direction=guess_direction,
        follow_corrections=follow_corrections,
    )
    if isinstance(result, ParseError):
        return None

    return result.lemmas


async def examples(
    query: str,
    src: LANGUAGE_CODE,
    dst: LANGUAGE_CODE,
    guess_direction: bool = False,
    follow_corrections: FollowCorrections = FollowCorrections.ALWAYS,
):
    result = await client.process_search_result(
        query=query,
        src=src,
        dst=dst,
        guess_direction=guess_direction,
        follow_corrections=follow_corrections,
    )
    if isinstance(result, ParseError):
        return None

    return result.examples


async def external_sources(
    query: str,
    src: LANGUAGE_CODE,
    dst: LANGUAGE_CODE,
    guess_direction: bool = False,
    follow_corrections: FollowCorrections = FollowCorrections.ALWAYS,
):
    result = await client.process_search_result(
        query=query,
        src=src,
        dst=dst,
        guess_direction=guess_direction,
        follow_corrections=follow_corrections,
    )
    if isinstance(result, ParseError):
        return None

    return result.external_sources


async def autocompletions(
    query: str,
    src: LANGUAGE_CODE,
    dst: LANGUAGE_CODE,
):
    result = await client.process_autocompletions(
        query=query,
        src_lang_code=src,
        dst_lang_code=dst,
    )
    if isinstance(result, ParseError):
        return None

    return result.autocompletions
