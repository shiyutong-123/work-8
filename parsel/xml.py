"""XML-related utilities for Parsel."""
from __future__ import annotations

from lxml import etree


def _force_fix(root: etree._Element) -> etree._Element:
    """
    Force fix namespace-related bugs in XML elements.

    This function ensures that namespaces are properly handled in the element tree.
    It cleans up namespaces and ensures consistent namespace handling.
    """
    if not isinstance(root, etree._Element):
        return root

    # Clean up namespaces to ensure proper handling
    etree.cleanup_namespaces(root)
    
    return root
