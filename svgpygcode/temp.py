#coding: utf-8

import svgpygcode as spg
from xml.dom import minidom

# opening svg file
doc = minidom.parse('/Users/baulieu/scripts/libraries/svgpygcode/svgpygcode/TeamDesk_1.6_Pied35.svg')  # parseString also exists
path_strings = [[path.getAttribute('d'), path.getAttribute('stroke') ] for path in doc.getElementsByTagName('path')]
doc.unlink()

machining = spg.Machining()

for path in path_strings:
    if path[1][7:10] == '200':
        machining.add_operation(path[0], 'pocket_outside', dict())
    elif path[1][7:10] == '100':
        machining.add_operation(path[0], 'pocket_inside', dict())
    if path[1][4:7] == '200':
        machining.add_operation(path[0], 'profile_inside', dict())
    elif path[1][4:7] == '100':
        machining.add_operation(path[0], 'profile_outside', dict())
    elif path[1][4:7] == '255':
        machining.add_operation(path[0], 'engraving')

machining.calculate()

print(machining.gcode)
