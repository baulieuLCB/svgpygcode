#coding: utf-8

import svgpygcode as spg
from xml.dom import minidom
import os

# opening svg file
doc = minidom.parse('/Users/baulieu/scripts/libraries/svgpygcode/svgpygcode/TeamDesk_pied_35.svg')  # parseString also exists
path_strings = [[path.getAttribute('d'), path.getAttribute('stroke') ] for path in doc.getElementsByTagName('path')]
doc.unlink()

machining = spg.Machining()

for path in path_strings:
    if path[1][7:10] == '200':
        machining.add_operation(path[0], 'pocket_outside', {'clearance_pane':30, 'target_depth':-25, 'depth_increment':-3.1})
    elif path[1][7:10] == '100':
        machining.add_operation(path[0], 'pocket_inside', {'clearance_pane':30, 'target_depth':-25, 'depth_increment':-3.1})
    if path[1][4:7] == '200':
        machining.add_operation(path[0], 'profile_inside', {'clearance_pane':30, 'target_depth':-35.3, 'depth_increment':-3.1})
    elif path[1][4:7] == '100':
        machining.add_operation(path[0], 'profile_outside', {'clearance_pane':30, 'target_depth':-35.3, 'depth_increment':-3.1})
    elif path[1][4:7] == '255':
        machining.add_operation(path[0], 'engraving', {'clearance_pane':30, 'target_depth':-25, 'depth_increment':-3.1})

machining.calculate()

# print(machining.gcode)

file = open(os.path.join('/Users/baulieu/scripts/libraries/svgpygcode/svgpygcode/', 'result.nc'), 'w+')
file.write(machining.gcode)
file.close()
