from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from parsel import Selector
from parsel.csstranslator import GenericTranslator, HTMLTranslator


HTML_TEXT = "<div><p class='intro'>Hello</p><span>World</span></div>"
XML_TEXT = (
    "<?xml version='1.0' encoding='utf-8'?>"
    "<root><item type='a'>alpha</item><item type='b'>beta</item></root>"
)


def _clear_all_caches() -> None:
    GenericTranslator.css_to_xpath.cache_clear()
    HTMLTranslator.css_to_xpath.cache_clear()
    Selector._css2xpath.cache_clear()


async def _run_concurrent_css_translations(
    num_workers: int,
    iterations: int,
) -> list[str]:
    errors: list[str] = []
    barrier = threading.Barrier(num_workers)

    def translate_html() -> None:
        barrier.wait()
        for _ in range(iterations):
            try:
                sel = Selector(text=HTML_TEXT, type="html")
                result = sel.css("p.intro::text").get()
                if result != "Hello":
                    errors.append(
                        f"HTML type pollution: expected 'Hello', got {result!r}"
                    )
                result2 = sel.css("span::text").get()
                if result2 != "World":
                    errors.append(
                        f"HTML type pollution: expected 'World', got {result2!r}"
                    )
            except Exception as exc:
                errors.append(f"HTML exception: {exc}")

    def translate_xml() -> None:
        barrier.wait()
        for _ in range(iterations):
            try:
                sel = Selector(text=XML_TEXT, type="xml")
                result = sel.css("item[type='a']::text").get()
                if result != "alpha":
                    errors.append(
                        f"XML type pollution: expected 'alpha', got {result!r}"
                    )
                result2 = sel.css("item[type='b']::text").get()
                if result2 != "beta":
                    errors.append(
                        f"XML type pollution: expected 'beta', got {result2!r}"
                    )
            except Exception as exc:
                errors.append(f"XML exception: {exc}")

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        tasks = []
        for i in range(num_workers):
            if i % 2 == 0:
                tasks.append(loop.run_in_executor(executor, translate_html))
            else:
                tasks.append(loop.run_in_executor(executor, translate_xml))
        await asyncio.gather(*tasks)

    return errors


def test_concurrent_css_no_type_pollution() -> None:
    _clear_all_caches()

    errors = asyncio.run(
        _run_concurrent_css_translations(
            num_workers=20,
            iterations=50,
        )
    )

    assert not errors, f"Type pollution detected in concurrent CSS translation: {errors}"


def test_concurrent_cache_clear_no_crash() -> None:
    _clear_all_caches()

    errors: list[str] = []
    barrier = threading.Barrier(10)
    stop_event = threading.Event()

    def reader_html() -> None:
        barrier.wait()
        while not stop_event.is_set():
            try:
                sel = Selector(text=HTML_TEXT, type="html")
                sel.css("p::text").get()
            except Exception as exc:
                errors.append(f"Reader HTML exception: {exc}")
                break

    def reader_xml() -> None:
        barrier.wait()
        while not stop_event.is_set():
            try:
                sel = Selector(text=XML_TEXT, type="xml")
                sel.css("item::text").get()
            except Exception as exc:
                errors.append(f"Reader XML exception: {exc}")
                break

    def cache_invalidator() -> None:
        barrier.wait()
        for _ in range(100):
            try:
                _clear_all_caches()
            except Exception as exc:
                errors.append(f"Cache clear exception: {exc}")
                break
        stop_event.set()

    async def _run() -> None:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=10) as executor:
            tasks = []
            for i in range(10):
                if i < 3:
                    tasks.append(loop.run_in_executor(executor, reader_html))
                elif i < 6:
                    tasks.append(loop.run_in_executor(executor, reader_xml))
                else:
                    tasks.append(loop.run_in_executor(executor, cache_invalidator))
            await asyncio.gather(*tasks)

    asyncio.run(_run())

    assert not errors, f"Crash during concurrent cache invalidation: {errors}"


def test_concurrent_mixed_css_selectors() -> None:
    _clear_all_caches()

    errors: list[str] = []
    barrier = threading.Barrier(16)

    css_queries_html = [
        ("p.intro::text", "Hello"),
        ("span::text", "World"),
        ("div > p::attr(class)", "intro"),
        ("p::text", "Hello"),
    ]

    css_queries_xml = [
        ("item[type='a']::text", "alpha"),
        ("item[type='b']::text", "beta"),
        ("root > item::attr(type)", "a"),
        ("item::text", "alpha"),
    ]

    def translate_html_queries() -> None:
        barrier.wait()
        for _ in range(50):
            try:
                sel = Selector(text=HTML_TEXT, type="html")
                for query, expected in css_queries_html:
                    result = sel.css(query).get()
                    if result != expected:
                        errors.append(
                            f"HTML query={query!r}: expected {expected!r}, got {result!r}"
                        )
            except Exception as exc:
                errors.append(f"HTML exception: {exc}")

    def translate_xml_queries() -> None:
        barrier.wait()
        for _ in range(50):
            try:
                sel = Selector(text=XML_TEXT, type="xml")
                for query, expected in css_queries_xml:
                    result = sel.css(query).get()
                    if result != expected:
                        errors.append(
                            f"XML query={query!r}: expected {expected!r}, got {result!r}"
                        )
            except Exception as exc:
                errors.append(f"XML exception: {exc}")

    async def _run() -> None:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=16) as executor:
            tasks = []
            for i in range(16):
                if i % 2 == 0:
                    tasks.append(loop.run_in_executor(executor, translate_html_queries))
                else:
                    tasks.append(loop.run_in_executor(executor, translate_xml_queries))
            await asyncio.gather(*tasks)

    asyncio.run(_run())

    assert not errors, f"Type pollution in mixed CSS selectors: {errors}"
