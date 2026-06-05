from parsel import Selector
import sys


# 测试 Selector.pipe
text = "<div>Hello, World!</div>"
sel = Selector(text=text)
print("测试 Selector.pipe:")
result = sel.pipe('get_text')
print(f"结果: {result}")
assert result == '<html><body><div>Hello, World!</div></body></html>', f"预期 '<html><body><div>Hello, World!</div></body></html>', 实际 {result}"


# 测试 SelectorList.pipe
text = """<div>
  <ul>
    <li>Item 1</li>
    <li>Item 2</li>
    <li>Item 3</li>
  </ul>
</div>"""
sel = Selector(text=text)
list_sel = sel.css('li')
print("\n测试 SelectorList.pipe:")
result = list_sel.pipe('get_text')
print(f"结果: {result}")
assert len(result) == 3, f"预期 3 个项目, 实际 {len(result)}"


print("\n✅ 所有测试通过!")
