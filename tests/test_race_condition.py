"""Tests for CSS translator cache race condition in concurrent scenarios."""

from __future__ import annotations

import asyncio
import pickle
from concurrent.futures import ThreadPoolExecutor

import pytest

from parsel import Selector
from parsel.csstranslator import _translation_cache


HTML_DOC = "<html><body><div class='foo'>hello</div><p>world</p></body></html>"
XML_DOC = "<root><item class='foo'>hello</item><data>world</data></root>"


def _concurrent_css_query(
    doc: str,
    selector_type: str,
    css_query: str,
    expected_xpath_snippet: str,
    num_tasks: int = 50,
) -> list[str]:
    """Run CSS queries concurrently to trigger race conditions."""
    errors: list[str] = []

    def task() -> None:
        try:
            sel = Selector(text=doc, type=selector_type)
            xpath = sel._css2xpath(css_query)
            if expected_xpath_snippet not in xpath:
                errors.append(
                    f"Type pollution: {selector_type} selector got wrong xpath: {xpath}"
                )
        except Exception as exc:
            errors.append(f"Task failed: {exc}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(task) for _ in range(num_tasks)]
        for future in futures:
            future.result()

    return errors


def _concurrent_pickle_roundtrip(
    doc: str,
    selector_type: str,
    css_query: str,
    expected_text: str,
    num_tasks: int = 50,
) -> list[str]:
    """Serialize and deserialize Selectors concurrently to trigger race conditions."""
    errors: list[str] = []
    sel = Selector(text=doc, type=selector_type)
    pickled = pickle.dumps(sel)

    def task() -> None:
        try:
            loaded = pickle.loads(pickled)
            result = loaded.css(css_query).get()
            if result != expected_text:
                errors.append(
                    f"Type pollution after unpickle: expected {expected_text!r}, "
                    f"got {result!r} for type {selector_type}"
                )
        except Exception as exc:
            errors.append(f"Pickle task failed: {exc}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(task) for _ in range(num_tasks)]
        for future in futures:
            future.result()

    return errors


def _concurrent_mixed_types(
    num_tasks: int = 100,
) -> list[str]:
    """Concurrently query CSS with mixed HTML and XML types to trigger type pollution."""
    errors: list[str] = []

    html_sel = Selector(text=HTML_DOC, type="html")
    html_pickled = pickle.dumps(html_sel)
    xml_sel = Selector(text=XML_DOC, type="xml")
    xml_pickled = pickle.dumps(xml_sel)

    def html_task() -> None:
        try:
            sel = pickle.loads(html_pickled)
            xpath = sel._css2xpath("div.foo")
            if "html" not in xpath.lower() and "div" not in xpath:
                pass
            result = sel.css("div.foo::text").get()
            if result != "hello":
                errors.append(f"HTML type pollution: expected 'hello', got {result!r}")
        except Exception as exc:
            errors.append(f"HTML task failed: {exc}")

    def xml_task() -> None:
        try:
            sel = pickle.loads(xml_pickled)
            xpath = sel._css2xpath("item.foo")
            result = sel.css("item.foo::text").get()
            if result != "hello":
                errors.append(f"XML type pollution: expected 'hello', got {result!r}")
        except Exception as exc:
            errors.append(f"XML task failed: {exc}")

    tasks = []
    for _ in range(num_tasks // 2):
        tasks.append(html_task)
        tasks.append(xml_task)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(t) for t in tasks]
        for future in futures:
            future.result()

    return errors


class TestCSSTranslationCacheRaceCondition:
    def test_concurrent_css_same_type(self) -> None:
        """Concurrent CSS queries of the same type should not cause errors."""
        errors = _concurrent_css_query(
            HTML_DOC,
            "html",
            "div.foo::text",
            "div",
            num_tasks=100,
        )
        assert not errors, f"Errors: {errors}"

    def test_concurrent_css_xml_type(self) -> None:
        """Concurrent CSS queries on XML should not cause errors."""
        errors = _concurrent_css_query(
            XML_DOC,
            "xml",
            "item.foo::text",
            "item",
            num_tasks=100,
        )
        assert not errors, f"Errors: {errors}"

    def test_concurrent_pickle_html(self) -> None:
        """Concurrent pickle/unpickle of HTML Selectors should not cause type pollution."""
        errors = _concurrent_pickle_roundtrip(
            HTML_DOC,
            "html",
            "div.foo::text",
            "hello",
            num_tasks=50,
        )
        assert not errors, f"Errors: {errors}"

    def test_concurrent_pickle_xml(self) -> None:
        """Concurrent pickle/unpickle of XML Selectors should not cause type pollution."""
        errors = _concurrent_pickle_roundtrip(
            XML_DOC,
            "xml",
            "item.foo::text",
            "hello",
            num_tasks=50,
        )
        assert not errors, f"Errors: {errors}"

    def test_concurrent_mixed_types(self) -> None:
        """Concurrent mixed HTML/XML operations should not cause type pollution."""
        errors = _concurrent_mixed_types(num_tasks=100)
        assert not errors, f"Errors: {errors}"

    def test_cache_clear_does_not_cause_pollution(self) -> None:
        """Clearing the cache concurrently should not cause type pollution."""
        errors: list[str] = []

        html_sel = Selector(text=HTML_DOC, type="html")
        xml_sel = Selector(text=XML_DOC, type="xml")

        html_xpath = html_sel._css2xpath("div.foo")
        xml_xpath = xml_sel._css2xpath("item.foo")

        def clear_and_query() -> None:
            try:
                _translation_cache.clear()
                sel = Selector(text=HTML_DOC, type="html")
                xpath = sel._css2xpath("div.foo")
                if "div" not in xpath:
                    errors.append(f"Cache clear caused pollution: {xpath}")
            except Exception as exc:
                errors.append(f"Clear task failed: {exc}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(clear_and_query) for _ in range(50)]
            for future in futures:
                future.result()

        assert not errors, f"Errors: {errors}"

    def test_cache_type_isolation(self) -> None:
        """Verify that HTML and XML translator caches are properly isolated."""
        html_sel = Selector(text=HTML_DOC, type="html")
        xml_sel = Selector(text=XML_DOC, type="xml")

        html_xpath = html_sel._css2xpath("div.foo")
        xml_xpath = xml_sel._css2xpath("item.foo")

        assert "div" in html_xpath, f"HTML xpath should contain 'div': {html_xpath}"
        assert "item" in xml_xpath, f"XML xpath should contain 'item': {xml_xpath}"

        html_xpath_cached = html_sel._css2xpath("div.foo")
        xml_xpath_cached = xml_sel._css2xpath("item.foo")

        assert html_xpath == html_xpath_cached, "HTML cache should return same value"
        assert xml_xpath == xml_xpath_cached, "XML cache should return same value"


class TestAsyncRaceCondition:
    """Tests that use asyncio to demonstrate the race condition."""

    def test_async_concurrent_css(self) -> None:
        """Async concurrent CSS queries should not cause type pollution."""

        async def html_query() -> str:
            sel = Selector(text=HTML_DOC, type="html")
            return sel.css("div.foo::text").get()

        async def xml_query() -> str:
            sel = Selector(text=XML_DOC, type="xml")
            return sel.css("item.foo::text").get()

        async def run_concurrent() -> list[str]:
            results: list[str] = []
            tasks = []
            for _ in range(50):
                tasks.append(asyncio.create_task(html_query()))
                tasks.append(asyncio.create_task(xml_query()))
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_concurrent())
        assert all(r == "hello" for r in results), f"Type pollution detected: {results}"

    def test_async_pickle_roundtrip(self) -> None:
        """Async concurrent pickle/unpickle should not cause type pollution."""
        html_sel = Selector(text=HTML_DOC, type="html")
        xml_sel = Selector(text=XML_DOC, type="xml")
        html_data = pickle.dumps(html_sel)
        xml_data = pickle.dumps(xml_sel)

        async def html_roundtrip() -> str:
            sel = pickle.loads(html_data)
            return sel.css("div.foo::text").get()

        async def xml_roundtrip() -> str:
            sel = pickle.loads(xml_data)
            return sel.css("item.foo::text").get()

        async def run_concurrent() -> list[str]:
            tasks = []
            for _ in range(50):
                tasks.append(asyncio.create_task(html_roundtrip()))
                tasks.append(asyncio.create_task(xml_roundtrip()))
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_concurrent())
        assert all(r == "hello" for r in results), f"Type pollution: {results}"

    def test_async_cache_race(self) -> None:
        """Async cache access race condition test."""

        async def query_and_clear() -> None:
            for _ in range(10):
                sel = Selector(text=HTML_DOC, type="html")
                xpath = sel._css2xpath("div.foo")
                assert "div" in xpath, f"Bad xpath: {xpath}"
                _translation_cache.clear()
                await asyncio.sleep(0)

        async def run_concurrent() -> None:
            tasks = [asyncio.create_task(query_and_clear()) for _ in range(20)]
            await asyncio.gather(*tasks)

        asyncio.run(run_concurrent())