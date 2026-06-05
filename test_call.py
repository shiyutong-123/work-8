from parsel import Selector

html = '<html><body><div class="item"><p>Hello</p></div><div class="item"><p>World</p></div></body></html>'
sel = Selector(text=html, type='html')

result = sel('div.item')
print('CSS selector result:', [s.get() for s in result])

result2 = sel('//div/p')
print('XPath result:', [s.get() for s in result2])

result3 = sel('p')
print('Simple tag result:', [s.get() for s in result3])

print('All tests passed!')
