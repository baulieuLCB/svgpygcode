#coding: utf-8

import svgpygcode
from xml.dom import minidom

# opening svg file
doc = minidom.parse('/Users/baulieu/scripts/libraries/svgpygcode/svgpygcode/TeamDesk_1.6_Pied35.svg')  # parseString also exists
path_strings = [[path.getAttribute('d'), path.getAttribute('stroke') ] for path in doc.getElementsByTagName('path')]
doc.unlink()

for path in path_strings:
    print(path)
