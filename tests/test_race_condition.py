"""
测试 selector 中 CSS 翻译器缓存的竞态条件问题
"""
from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from parsel import Selector
from parsel.csstranslator import HTMLTranslator, GenericTranslator


HTML_TEST_CONTENT = """
<html>
<body>
    <div id="test-div">
        <p class="test-paragraph">Hello, World!</p>
        <span class="test-span">Test span</span>
    </div>
    <div id="another-div">
        <p>Another paragraph</p>
    </div>
</body>
</html>
"""


def test_thread_safety_basic() -> None:
    """测试基本的线程安全"""
    results: list[bool] = []
    errors: list[Exception] = []
    
    def worker() -> None:
        try:
            selector = Selector(text=HTML_TEST_CONTENT)
            # 多次使用 css 选择器来触发缓存机制
            for _ in range(100):
                result = selector.css("#test-div .test-paragraph::text").get()
                assert result == "Hello, World!"
            results.append(True)
        except Exception as e:
            errors.append(e)
            results.append(False)
    
    # 创建多个线程同时执行
    threads = []
    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Thread safety test failed with errors: {errors}"
    assert all(results), "Some threads failed"


def test_mixed_translator_usage() -> None:
    """测试混合使用 HTML 和 XML 翻译器"""
    results: list[bool] = []
    errors: list[Exception] = []
    
    def html_worker() -> None:
        try:
            selector = Selector(text=HTML_TEST_CONTENT, type="html")
            for _ in range(100):
                result = selector.css("#test-div .test-paragraph::text").get()
                assert result == "Hello, World!"
            results.append(True)
        except Exception as e:
            errors.append(e)
            results.append(False)
    
    def xml_worker() -> None:
        try:
            xml_content = "<root><item id='1'>Test</item><item id='2'>Another</item></root>"
            selector = Selector(text=xml_content, type="xml")
            for _ in range(100):
                result = selector.css("item[id='1']::text").get()
                assert result == "Test"
            results.append(True)
        except Exception as e:
            errors.append(e)
            results.append(False)
    
    # 混合使用两种类型的选择器
    threads = []
    for i in range(10):
        if i % 2 == 0:
            t = threading.Thread(target=html_worker)
        else:
            t = threading.Thread(target=xml_worker)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Mixed translator test failed with errors: {errors}"
    assert all(results), "Some threads failed"


def test_instance_cache_isolation() -> None:
    """测试翻译器实例缓存的隔离性"""
    # 创建两个翻译器实例
    t1 = HTMLTranslator()
    t2 = HTMLTranslator()
    
    # 分别使用两个翻译器
    result1 = t1.css_to_xpath(".test")
    result2 = t2.css_to_xpath(".test")
    
    # 结果应该相同
    assert result1 == result2
    
    # 但它们的缓存应该是独立的
    # 我们检查实例内部的缓存字典（虽然这是实现细节）
    assert hasattr(t1, "_css_to_xpath_cache")
    assert hasattr(t2, "_css_to_xpath_cache")
    assert t1._css_to_xpath_cache is not t2._css_to_xpath_cache


@pytest.mark.asyncio
async def test_async_race_condition() -> None:
    """测试异步场景下的竞态条件"""
    errors: list[Exception] = []
    
    async def worker() -> None:
        try:
            # 在异步函数中使用选择器
            selector = Selector(text=HTML_TEST_CONTENT)
            for _ in range(50):
                result = selector.css("#test-div .test-paragraph::text").get()
                assert result == "Hello, World!"
                # 模拟异步操作
                await asyncio.sleep(0)
        except Exception as e:
            errors.append(e)
    
    # 创建多个协程同时执行
    tasks = [worker() for _ in range(20)]
    await asyncio.gather(*tasks)
    
    assert len(errors) == 0, f"Async race condition test failed with errors: {errors}"


def test_thread_pool_executor() -> None:
    """测试使用 ThreadPoolExecutor 的并发场景"""
    errors: list[Exception] = []
    
    def worker() -> bool:
        try:
            selector = Selector(text=HTML_TEST_CONTENT)
            for _ in range(100):
                result = selector.css("#another-div p::text").get()
                assert result == "Another paragraph"
            return True
        except Exception as e:
            errors.append(e)
            return False
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(worker) for _ in range(30)]
        results = [f.result() for f in futures]
    
    assert len(errors) == 0, f"ThreadPoolExecutor test failed with errors: {errors}"
    assert all(results), "Some worker threads failed"


def test_translator_subclassing_safety() -> None:
    """测试翻译器子类化的安全性"""
    class CustomHTMLTranslator(HTMLTranslator):
        pass
    
    class CustomGenericTranslator(GenericTranslator):
        pass
    
    # 创建多个实例并使用
    translators = [
        HTMLTranslator(),
        GenericTranslator(),
        CustomHTMLTranslator(),
        CustomGenericTranslator(),
    ]
    
    # 测试所有翻译器的缓存功能
    for translator in translators:
        result1 = translator.css_to_xpath("div")
        result2 = translator.css_to_xpath("div")
        assert result1 == result2, "Cache should return the same result"
