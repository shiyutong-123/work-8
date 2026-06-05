import asyncio
from parsel import Selector

async def _test_selector(text: str, css_query: str, expected: str) -> None:
    sel = Selector(text=text)
    # Give back control to the event loop to allow concurrency
    await asyncio.sleep(0.001)
    result = sel.css(css_query).get()
    assert result == expected

async def run_race_condition_test() -> None:
    html_text = "<html><body><h1 class='title'>Hello World</h1><p>Test</p></body></html>"
    
    tasks = []
    # Create multiple tasks to trigger the race condition
    for _ in range(1000):
        tasks.append(_test_selector(html_text, "h1.title::text", "Hello World"))
        tasks.append(_test_selector(html_text, "p::text", "Test"))

    # Run them concurrently
    await asyncio.gather(*tasks)

def test_async_race_condition() -> None:
    asyncio.run(run_race_condition_test())

if __name__ == "__main__":
    test_async_race_condition()
    print("Test passed successfully!")
