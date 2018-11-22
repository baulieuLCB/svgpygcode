#coding: utf-8

import svgwrite
import svgpygcode as spg
from svgpathtools import parse_path, Line, Path, wsvg

dwg = svgwrite.Drawing(filename = '/Users/baulieu/scripts/libraries/svgpygcode/svgpygcode/tryspt.svg', size = (1300, 1300), viewBox = ("-50 -50 1300 1300"))

machining = spg.Machining()

# print("""--------------------------------
# test tangent""")
#
# p = [100, 100]
# c = ['A',[50, 50, 0, 0, 1, 150, 150]]
# print(machining.get_point_tangent_arc(c, p, 'start'))
#
# p = [100, 100]
# c = ['A',[200, 200, 0, 0, 1, 100, 200]]
# print(machining.get_point_tangent_arc(c, p, 'start'))
#
# p = [100, 100]
# c = ['A',[200, 200, 0, 0, 0, 300, 100]]
# print(machining.get_point_tangent_arc(c, p, 'start'))
#
# p = [100, 100]
# c = ['A',[200, 200, 0, 0, 0, 300, 100]]
# print(machining.get_point_tangent_arc(c, p, 'end'))

# p = [100, 100]
# c = ['A',[50, 50, 0, 0, 1, 150, 150]]
# print(machining.get_point_tangent_arc(c, p, 'start'))


svg_path1 = [
['M', [100, 100]],
['L', [500, 100]],
['A', [50, 50, 0, 0, 1, 550, 150]],
['L', [550, 350]],
['A', [50, 50, 0, 0, 1, 500, 400]],
['L', [100, 400]],
['L', [100, 100]],
]

svg_path1 = [
['M', [100, 100]],
['L', [100, 400]],
['L', [500, 400]],
['A', [50, 50, 0, 0, 0, 550, 350]],
['L', [550, 150]],
['A', [50, 50, 0, 0, 0, 500, 100]],
['L', [100, 100]],
]

temp = "M 980.0 0.0  L 898.702 0.0  L 536.667 457.421  A 59.515 59.515 0 0 1 490.0 480.0  A 59.515 59.515 0 0 1 443.33299999999997 457.421  L 81.298 0.0  L 0.0 0.0  L 0.0 22.0  L 294.124 468.731  A 80.0 80.0 0 0 1 253.191 588.42  L 0.0 675.0  L 0.0 731.0  L 50.0 731.0  L 50.0 720.0  A 4.1 4.1 0 0 1 58.19999999999999 720.0  L 422.016 720.0  L 437.017 705.0  L 490.0 705.0  L 542.983 705.0  L 557.984 720.0  L 921.8 720.0  A 4.1 4.1 0 0 1 930.0 720.0  L 930.0 731.0  L 980.0 731.0  L 980.0 675.0  L 726.809 588.42  A 80.0 80.0 0 0 1 685.876 468.731  L 980.0 22.0  L 980.0 0.0z"

temp1 = []
t1 = ""
t2 = ""
for char in temp:
    if char in ['M', 'L', 'A']:
        if t1 != "":
            temp1.append([t1, t2])
        t1 = char
        t2 = ""
    else:
        t2 += char
temp2 = []
for el in temp1:
    temp2.append([el[0], el[1][1:-2].split(" ")])

svg_path1 = temp2

for i in range(0, len(svg_path1)):
    if svg_path1[i][0] in ['M', 'L']:
        for j in range(0, len(svg_path1[i][1])):
            svg_path1[i][1][j] = float(svg_path1[i][1][j])
    else:
        svg_path1[i][1][0] = float(svg_path1[i][1][0])
        svg_path1[i][1][1] = float(svg_path1[i][1][1])
        svg_path1[i][1][2] = int(svg_path1[i][1][2])
        svg_path1[i][1][3] = int(svg_path1[i][1][3])
        svg_path1[i][1][4] = int(svg_path1[i][1][4])
        svg_path1[i][1][5] = float(svg_path1[i][1][5])
        svg_path1[i][1][6] = float(svg_path1[i][1][6])

svg_path2 = ""

svg1 = ""
for el in svg_path1:
    svg1 += "{} ".format(el[0])
    for e in el[1]:
        svg1 += "{} ".format(e)

svg2 = ""
svg_path2 = machining.offset_curve(svg_path1, 3, 'outside')
print("""
------------------
""")
for el in svg_path2:
    print(el)
    svg2 += "{} ".format(el[0])
    for e in el[1]:
        svg2 += "{} ".format(e)

dwg.add(dwg.path(svg1).stroke(color = 'black', width = 0.2).fill("none"))
dwg.add(dwg.path(svg2).stroke(color = 'black', width = 0.2).fill("none"))

dwg.save()
