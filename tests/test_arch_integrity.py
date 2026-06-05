from __future__ import annotations

from lxml import etree, html

from parsel import Selector
from parsel.selector import _ctgroup


class NamespaceOverflowSelector(Selector):
    failing_root_id: int | None = None

    def xpath(self, query: str, namespaces=None, **kwargs):
        if id(self.root) == self.failing_root_id:
            type(self).failing_root_id = None
            raise ValueError(f"XPath error: namespace overflow in {query}")
        return super().xpath(query, namespaces=namespaces, **kwargs)


def build_malformed_html_tree() -> etree._Element:
    root = html.Element("html")
    body = html.Element("body")
    root.append(body)

    target = html.Element("div")
    target.set("class", "target")
    target.text = "ok"
    body.append(target)

    namespaced = etree.Element(
        "{urn:overflow}ghost",
        nsmap={"ghost": "urn:overflow"},
    )
    namespaced.text = "ignored"
    body.append(namespaced)
    return root


def test_selector_namespace_overflow_fallback_preserves_css_caches() -> None:
    html_query = "div.target::text"
    html_translator = _ctgroup["html"]["_csstranslator"]
    html_translator.css_to_xpath.cache_clear()
    html_translator.css_to_xpath(html_query)
    html_cache_before = html_translator.css_to_xpath.cache_info()

    selector = NamespaceOverflowSelector(root=build_malformed_html_tree(), type="html")
    NamespaceOverflowSelector.failing_root_id = id(selector.root)
    assert selector.css(html_query).getall() == ["ok"]

    html_cache_after = html_translator.css_to_xpath.cache_info()
    assert html_cache_after.hits == html_cache_before.hits + 1
    assert html_cache_after.misses == html_cache_before.misses
    assert html_cache_after.currsize == html_cache_before.currsize

    xml_query = "item::text"
    xml_translator = _ctgroup["xml"]["_csstranslator"]
    xml_translator.css_to_xpath.cache_clear()
    xml_translator.css_to_xpath(xml_query)
    xml_cache_before = xml_translator.css_to_xpath.cache_info()

    xml_selector = Selector(text="<root><item>ok</root>", type="xml")
    assert xml_selector.css(xml_query).getall() == ["ok"]

    xml_cache_after = xml_translator.css_to_xpath.cache_info()
    assert xml_cache_after.hits == xml_cache_before.hits + 1
    assert xml_cache_after.misses == xml_cache_before.misses
    assert xml_cache_after.currsize == xml_cache_before.currsize
