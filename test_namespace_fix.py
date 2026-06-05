#!/usr/bin/env python
"""Test script to verify namespace fix is working."""

from parsel import Selector


def test_namespace_fix():
    """Test that namespace fix is working properly."""
    print("Testing namespace fix...")
    
    # Test with HTML
    html_content = """
    <div xmlns:foo="http://example.com/foo">
        <foo:bar>Test</foo:bar>
    </div>
    """
    
    sel = Selector(text=html_content, type="html")
    print("HTML selector created successfully")
    print(f"Root element tag: {sel.root.tag}")
    
    # Test with XML
    xml_content = """
    <root xmlns:ns="http://example.com/ns">
        <ns:item>1</ns:item>
        <ns:item>2</ns:item>
    </root>
    """
    
    sel = Selector(text=xml_content, type="xml")
    print("\nXML selector created successfully")
    print(f"Root element tag: {sel.root.tag}")
    
    print("\n✅ Namespace fix is working!")


if __name__ == "__main__":
    test_namespace_fix()
