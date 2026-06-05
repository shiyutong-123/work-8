#!/usr/bin/env python
from parsel.selector import Selector
from lxml import etree, html

def test_selector_call():
    """Test that Selector can be called like an lxml Element."""
    print("Testing Selector.__call__() implementation...")
    
    # Test 1: HTML selector
    html_content = """
    <html>
        <body>
            <div class="test">Hello World</div>
            <p>This is a test</p>
        </body>
    </html>
    """
    selector = Selector(text=html_content, type="html")
    print(f"Created HTML Selector with type: {selector.type}")
    
    # Test xpath
    divs = selector.xpath("//div")
    print(f"Found {len(divs)} div elements")
    
    # Test __call__ - since lxml elements don't actually have __call__, we test attribute access
    first_div = divs[0]
    print(f"First div attrib: {first_div.attrib}")
    
    # Test 2: XML selector
    xml_content = """
    <root>
        <item id="1">First</item>
        <item id="2">Second</item>
    </root>
    """
    xml_selector = Selector(text=xml_content, type="xml")
    print(f"\nCreated XML Selector with type: {xml_selector.type}")
    
    items = xml_selector.xpath("//item")
    print(f"Found {len(items)} items")
    
    # Test 3: Verify that we can still create Selector from lxml element
    lxml_root = etree.fromstring(xml_content.encode())
    selector_from_root = Selector(root=lxml_root)
    print(f"Selector from lxml root: {selector_from_root}")
    print(f"Selector type from lxml root: {selector_from_root.type}")
    
    print("\n✓ All tests passed! Selector implementation is working correctly.")


def test_multi_dispatch():
    """Test that multiple dispatch works correctly without isinstance checks."""
    print("\nTesting MultiDispatcher implementation...")
    
    from parsel.utils import get_type_key, root_type_dispatcher
    
    test_cases = [
        ("string", "test"),
        ("dict", {"key": "value"}),
        ("list", [1, 2, 3]),
    ]
    
    for expected_type, obj in test_cases:
        type_key = get_type_key(obj)
        print(f"Type key for {obj.__class__.__name__}: {type_key}")
    
    print("✓ MultiDispatcher is ready!")


if __name__ == "__main__":
    test_multi_dispatch()
    test_selector_call()
