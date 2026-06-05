from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from threading import RLock
from typing import TYPE_CHECKING, Any, Literal, Protocol

from cssselect import GenericTranslator as OriginalGenericTranslator
from cssselect import HTMLTranslator as OriginalHTMLTranslator
from cssselect.parser import Element, FunctionalPseudoElement, PseudoElement
from cssselect.xpath import ExpressionError
from cssselect.xpath import XPathExpr as OriginalXPathExpr

if TYPE_CHECKING:
    from typing_extensions import Self


class XPathExpr(OriginalXPathExpr):
    textnode: bool = False
    attribute: str | None = None

    @classmethod
    def from_xpath(
        cls,
        xpath: OriginalXPathExpr,
        textnode: bool = False,
        attribute: str | None = None,
    ) -> Self:
        x = cls(path=xpath.path, element=xpath.element, condition=xpath.condition)
        x.textnode = textnode
        x.attribute = attribute
        return x

    def __str__(self) -> str:
        path = super().__str__()
        if self.textnode:
            if path == "*":
                path = "text()"
            elif path.endswith("::*/*"):
                path = path[:-3] + "text()"
            else:
                path += "/text()"

        if self.attribute is not None:
            if path.endswith("::*/*"):
                path = path[:-2]
            path += f"/@{self.attribute}"

        return path

    def join(
        self: Self,
        combiner: str,
        other: OriginalXPathExpr,
        *args: Any,
        **kwargs: Any,
    ) -> Self:
        if not isinstance(other, XPathExpr):
            raise ValueError(
                f"Expressions of type {__name__}.XPathExpr can ony join expressions"
                f" of the same type (or its descendants), got {type(other)}"
            )
        super().join(combiner, other, *args, **kwargs)
        self.textnode = other.textnode
        self.attribute = other.attribute
        return self


class TranslatorProtocol(Protocol):
    def xpath_element(self, selector: Element) -> OriginalXPathExpr:
        pass

    def css_to_xpath(self, css: str, prefix: str = ...) -> str:
        pass


class TranslatorMixin:
    """This mixin adds support to CSS pseudo elements via dynamic dispatch.

    Currently supported pseudo-elements are ``::text`` and ``::attr(ATTR_NAME)``.
    """

    def xpath_element(self: TranslatorProtocol, selector: Element) -> XPathExpr:
        xpath = super().xpath_element(selector)  # type: ignore[safe-super]
        return XPathExpr.from_xpath(xpath)

    def xpath_pseudo_element(
        self, xpath: OriginalXPathExpr, pseudo_element: PseudoElement
    ) -> OriginalXPathExpr:
        """
        Dispatch method that transforms XPath to support pseudo-element
        """
        if isinstance(pseudo_element, FunctionalPseudoElement):
            method_name = f"xpath_{pseudo_element.name.replace('-', '_')}_functional_pseudo_element"
            method = getattr(self, method_name, None)
            if not method:
                raise ExpressionError(
                    f"The functional pseudo-element ::{pseudo_element.name}() is unknown"
                )
            xpath = method(xpath, pseudo_element)
        else:
            method_name = (
                f"xpath_{pseudo_element.replace('-', '_')}_simple_pseudo_element"
            )
            method = getattr(self, method_name, None)
            if not method:
                raise ExpressionError(
                    f"The pseudo-element ::{pseudo_element} is unknown"
                )
            xpath = method(xpath)
        return xpath

    def xpath_attr_functional_pseudo_element(
        self, xpath: OriginalXPathExpr, function: FunctionalPseudoElement
    ) -> XPathExpr:
        """Support selecting attribute values using ::attr() pseudo-element"""
        if function.argument_types() not in (["STRING"], ["IDENT"]):
            raise ExpressionError(
                f"Expected a single string or ident for ::attr(), got {function.arguments!r}"
            )
        return XPathExpr.from_xpath(xpath, attribute=function.arguments[0].value)

    def xpath_text_simple_pseudo_element(self, xpath: OriginalXPathExpr) -> XPathExpr:
        """Support selecting text nodes using ::text pseudo-element"""
        return XPathExpr.from_xpath(xpath, textnode=True)


class GenericTranslator(TranslatorMixin, OriginalGenericTranslator):
    @lru_cache(maxsize=256)
    def css_to_xpath(self, css: str, prefix: str = "descendant-or-self::") -> str:
        return super().css_to_xpath(css, prefix)


class HTMLTranslator(TranslatorMixin, OriginalHTMLTranslator):
    @lru_cache(maxsize=256)
    def css_to_xpath(self, css: str, prefix: str = "descendant-or-self::") -> str:
        return super().css_to_xpath(css, prefix)


CSSTranslatorType = Literal["html", "xml"]


@dataclass(frozen=True)
class CSSTranslatorSnapshot:
    generation: int
    html: HTMLTranslator
    xml: GenericTranslator

    def translator_for(
        self, type_: CSSTranslatorType
    ) -> GenericTranslator | HTMLTranslator:
        return self.html if type_ == "html" else self.xml


class CSSTranslatorState:
    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot = self._make_snapshot(0)

    def _make_snapshot(self, generation: int) -> CSSTranslatorSnapshot:
        return CSSTranslatorSnapshot(
            generation=generation,
            html=HTMLTranslator(),
            xml=GenericTranslator(),
        )

    def snapshot(self) -> CSSTranslatorSnapshot:
        return self._snapshot

    def invalidate(self) -> CSSTranslatorSnapshot:
        with self._lock:
            self._snapshot = self._make_snapshot(self._snapshot.generation + 1)
            return self._snapshot


_translator_state = CSSTranslatorState()


def get_css_translator_snapshot() -> CSSTranslatorSnapshot:
    return _translator_state.snapshot()


def invalidate_css_translator_cache() -> CSSTranslatorSnapshot:
    return _translator_state.invalidate()


def css2xpath(query: str) -> str:
    """Return translated XPath version of a given CSS query"""
    return get_css_translator_snapshot().html.css_to_xpath(query)
