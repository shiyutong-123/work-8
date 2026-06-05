from lxml import etree
e = etree.Element('a')
print(dir(e))
try:
    e()
except Exception as ex:
    print("Error:", type(ex), ex)
