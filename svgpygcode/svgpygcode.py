# svgpygcode

import math
from decimal import Decimal

class Machining:
    def __init__(self):
        # list of contours
        self.contours = []
        # gcode string, ready for writing into a nc file
        self.gcode = ""
        # order in which the operations will be achieved, to minimize the machine travelling time
        self.order = []
        # current position of the machining head. Used during the calculation to minimize machine travelling
        self.current_position = [0, 0]

    def add_operation(self, svg_path, operation_type, properties):
        '''
        Add machining operations to the machining process.
            arguments:
                - svg_path:str 'd' attribute of your path component
                - operation_type:str description of the operation : 'profile_inside', 'profile_outside', 'pocket_inside', 'pocket_outside', 'engraving'
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, clearance_pane, holding_tabs_height, holding_tabs_number, holding_tabs_width
        '''
        self.contours.append([operation_type, svg_path, properties])

    def calculate(self, priority = []):
        '''
        Calculates the gcode for the operations defined, following the chosen order or priority.
            arguments:
                - prioritys:[str] list of string, first element type will be machined first, etc. Default : engraving -> pockets -> profiles
        '''
        # setting gcode file header
        self.gcode = "G90\n"
        self.determine_order(priority)
        for i in self.order:
            if self.contours[i][0] == 'pocket_inside':
                self.pocket(self.contours[i][1], self.contours[i][0], self.contours[i][2])
            if self.contours[i][0] == 'pocket_outside':
                self.pocket(self.contours[i][1], self.contours[i][0], self.contours[i][2])
            if self.contours[i][0] == 'profile_inside':
                self.profile(self.contours[i][1], self.contours[i][0], self.contours[i][2])
            if self.contours[i][0] == 'profile_outside':
                self.profile(self.contours[i][1], self.contours[i][0], self.contours[i][2])
            if self.contours[i][0] == 'engraving':
                self.engrave(self.contours[i][1], self.contours[i][0], self.contours[i][2])

    def determine_order(self, priority = []):
        '''
        Determines the order to follow depending of the type of machining and writes it in self.order.
            arguments:
                - priority:[str] same as in self.calculate
        '''
        position = self.current_position
        for el in self.contours:
            el[1] = self.parse_path(el[1])
        # WARNING : does not take count of priority yet
        while len(self.order) < len(self.contours):
            # look for the closest contour not already queued, and append it index to the list
            min_d = -1
            index = 0
            for i in range(0, len(self.contours)):
                if i not in self.order:
                    if min_d == -1:
                        min_d = self.min_distance(self.contours[i][1], position)
                        index = i
                    elif min_d > self.min_distance(self.contours[i][1], position):
                        min_d = self.min_distance(self.contours[i][1], position)
                        index = i
            self.order.append(index)
            # change the current position
            closest_index = self.closest_index(self.contours[index][1], position)
            if self.contours[index][1][closest_index][0] in ['M', 'L']:
                position = [self.contours[index][1][closest_index][1][0], self.contours[index][1][closest_index][1][1]]
            elif self.contours[index][1][closest_index][0] in ['A']:
                position = [self.contours[index][1][closest_index][1][5], self.contours[index][1][closest_index][1][6]]

    def profile(self, profile, type, properties):
        '''
        Determines the gcode string for a profile cut.
            arguments:
                - profile:[] list of line / elliptic arc / bezier elements.
                - operation_type:str description of the operation : 'profile_inside', 'profile_outside', 'pocket_inside', 'pocket_outside', 'engraving'
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, clearance_pane, holding_tabs_height, holding_tabs_number, holding_tabs_width
        '''
        # profile = self.parse_path(svg_path)
        properties = self.define_properties(properties)

        # modifying the path to integrate holding tabs
        profile = self.add_holding_tabs(profile, properties['holding_tabs_number'], properties['holding_tabs_width'], properties['holding_tabs_height'])

        # searching for the closest point from current position
        closest_index = self.closest_index(profile, self.current_position)

        # bringing the machining head to the closest point
        temp = """G0 X{} Y{} Z{}\n""".format(self.current_position[0], self.current_position[1], properties['clearance_pane'])
        if profile[closest_index][0] in ['M', 'L']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], properties['clearance_pane'])
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], properties['depth_increment'] if properties['depth_increment'] > properties['target_depth'] else properties['target_depth'])
        elif profile[closest_index][0] in ['A']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], properties['clearance_pane'])
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], properties['depth_increment'] if properties['depth_increment'] > properties['target_depth'] else properties['target_depth'])
        else:
            raise ValueError('UNEXPECTED CURVE TYPE IN THE SVG - COULD NOT GENERATE GCODE. Sorry bro :-( . Happened while generating a profile')
        self.gcode += temp

        increment = 1
        for increment in range(1, int(properties['target_depth']/properties['depth_increment']) + 2):
            depth = increment * properties['depth_increment'] if increment * properties['depth_increment'] > properties['target_depth'] else properties['target_depth']
            # plunging to the right depth
            if profile[closest_index][0] in ['M', 'L']:
                temp = """G1 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], depth)
            elif profile[closest_index][0] in ['A']:
                temp = """G1 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], depth)
            self.gcode += temp
            # go through the profile
            temp = ""
            for index in range(0, len(profile)):
                # true index to work with : we are going to
                i = (index + closest_index + 1)%len(profile)
                if profile[i][0] in ['M', 'L', 'HTD']:
                    temp += """G1 X{} Y{} Z{}\n""".format(profile[i][1][0], profile[i][1][1], depth)
                if profile[i][0] == 'A':
                    if profile[i-1][0] == 'A':
                        arc = self.arc_to_circle(profile[i-1][1][5], profile[i-1][1][6], profile[i][1])
                        cx = arc['cx'] - float(profile[i-1][1][5])
                        cy = arc['cy'] - float(profile[i-1][1][6])
                    elif profile[i-1][0] in ['M', 'L', 'HTD']:
                        arc = self.arc_to_circle(profile[i-1][1][0], profile[i-1][1][1], profile[i][1])
                        cx = arc['cx'] - float(profile[i-1][1][0])
                        cy = arc['cy'] - float(profile[i-1][1][1])
                    temp += """G{} X{} Y{} I{} J{}\n""".format(3 if arc['clockwise'] else 2,profile[i][1][5], profile[i][1][6], cx, cy)
                elif profile[i][0] == 'HTU':
                    ht_depth = depth if depth > properties['target_depth'] + properties['holding_tabs_height'] else properties['target_depth'] + properties['holding_tabs_height']
                    temp += """G1 X{} Y{} Z{}\n""".format(profile[i][1][0], profile[i][1][1], ht_depth)
                    # temp = """G1 X{} Y{} Z{}\n""".format(profile[i][1][5], profile[i][1][6], depth)
            self.gcode += temp
            temp = ""
        if profile[closest_index][0] in ['M', 'L']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], properties['clearance_pane'])
            self.current_position = [profile[closest_index][1][0], profile[closest_index][1][1]]
        elif profile[closest_index][0] in ['A']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], properties['clearance_pane'])
            self.current_position = [float(profile[closest_index][1][5]), float(profile[closest_index][1][6])]
        self.gcode += temp

    def pocket(self, profile, type, properties):
        '''
        Determines the gcode string for a pocket cut.
            arguments:
                - svg_path:[] list of line / elliptic arc / bezier elements.
                - operation_type:str description of the operation : 'profile_inside', 'profile_outside', 'pocket_inside', 'pocket_outside', 'engraving'
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, clearance_pane, holding_tabs_height, holding_tabs_number, holding_tabs_width
        '''
        # profile = self.parse_path(svg_path)
        properties = self.define_properties(properties)

        # searching for the closest point from current position
        closest_index = self.closest_index(profile, self.current_position)

        # bringing the machining head to the closest point
        temp = """G0 X{} Y{} Z{}\n""".format(self.current_position[0], self.current_position[1], properties['clearance_pane'])
        if profile[closest_index][0] in ['M', 'L']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], properties['clearance_pane'])
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], properties['depth_increment'] if properties['depth_increment'] > properties['target_depth'] else properties['target_depth'])
        elif profile[closest_index][0] in ['A']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], properties['clearance_pane'])
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], properties['depth_increment'] if properties['depth_increment'] > properties['target_depth'] else properties['target_depth'])
        else:
            raise ValueError('UNEXPECTED CURVE TYPE IN THE SVG - COULD NOT GENERATE GCODE. Sorry bro :-( . Happened while generating a profile')
        self.gcode += temp

        increment = 1
        for increment in range(1, int(properties['target_depth']/properties['depth_increment']) + 2):
            depth = increment * properties['depth_increment'] if increment * properties['depth_increment'] > properties['target_depth'] else properties['target_depth']
            # plunging to the right depth
            if profile[closest_index][0] in ['M', 'L']:
                temp = """G1 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], depth)
            elif profile[closest_index][0] in ['A']:
                temp = """G1 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], depth)
            self.gcode += temp
            # go through the profile
            temp = ""
            for index in range(0, len(profile)):
                # true index to work with : we are going to
                i = (index + closest_index + 1)%len(profile)
                if profile[i][0] in ['M', 'L']:
                    temp += """G1 X{} Y{} Z{}\n""".format(profile[i][1][0], profile[i][1][1], depth)
                if profile[i][0] == 'A':
                    if profile[i-1][0] == 'A':
                        arc = self.arc_to_circle(profile[i-1][1][5], profile[i-1][1][6], profile[i][1])
                        cx = arc['cx'] - float(profile[i-1][1][5])
                        cy = arc['cy'] - float(profile[i-1][1][6])
                    elif profile[i-1][0] in ['M', 'L']:
                        arc = self.arc_to_circle(profile[i-1][1][0], profile[i-1][1][1], profile[i][1])
                        cx = arc['cx'] - float(profile[i-1][1][0])
                        cy = arc['cy'] - float(profile[i-1][1][1])
                    temp += """G{} X{} Y{} I{} J{}\n""".format(3 if arc['clockwise'] else 2, profile[i][1][5], profile[i][1][6], cx, cy)
            self.gcode += temp
            temp = ""
        if profile[closest_index][0] in ['M', 'L']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][0], profile[closest_index][1][1], properties['clearance_pane'])
            self.current_position = [profile[closest_index][1][0], profile[closest_index][1][1]]
        elif profile[closest_index][0] in ['A']:
            temp += """G0 X{} Y{} Z{}\n""".format(profile[closest_index][1][5], profile[closest_index][1][6], properties['clearance_pane'])
            self.current_position = [profile[closest_index][1][5], profile[closest_index][1][6]]
        self.gcode += temp

    def engraving(self, profile, type, properties):
        '''
        Determines the gcode string for an engraving cut.
            arguments:
                - profile:[] list of line / elliptic arc / bezier elements.
                - operation_type:str description of the operation : 'profile_inside', 'profile_outside', 'pocket_inside', 'pocket_outside', 'engraving'
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, clearance_pane, holding_tabs_height, holding_tabs_number, holding_tabs_width
        '''
        self.current_position = [1, 1]

    def parse_path(self, svg_path):
        '''
        Parses a string SVG to a list of line / elliptic arc / bezier elements.
            arguments:
                - svg_path:str 'd' attribute of your path component
        '''
        data = []
        temp1 = ""
        temp2 = ""
        for char in svg_path:
            if char in ['M', 'L', 'A']:
                if temp1 is not '':
                    data.append([temp1, temp2])
                temp1 = char
                temp2 = ""
            else:
                temp2 += char
        for el in data:
            el[1] = el[1][1:-2].split(' ')
            for e in el[1]:
                e = float(e)
        result = data
        return result

    def closest_index(self, profile, position):
        '''
        Returns the index of the curve finishing to the closest point to the indicated position.
            arguments:
                - profile:list parsed svg path (cf self.parse_path)
                - position:[float, float] coordinates in 2D or a point
        '''
        closest_index = 0
        min_d = -1
        for i in range(0, len(profile)):
            if profile[i][0] in ['M', 'L']:
                d = math.sqrt((float(position[0]) - float(profile[i][1][0]))**2 + (float(position[1]) - float(profile[i][1][1]))**2)
            elif profile[i][0] == 'A':
                d = math.sqrt((float(position[0]) - float(profile[i][1][5]))**2 + (float(position[1]) - float(profile[i][1][6]))**2)
            if min_d == -1:
                min_d = d
                closest_index = i
            elif d < min_d:
                min_d = d
                closest_index = i
        return closest_index

    def min_distance(self, profile, position):
        '''
        Returns the minimal distance between the given position and the given contour.
            arguments:
                - profile:list parsed svg path (cf self.parse_path)
                - position:[float, float] coordinates in 2D or a point
        '''
        min_d = -1
        for i in range(0, len(profile)):
            if profile[i][0] in ['M', 'L']:
                d = math.sqrt((float(position[0]) - float(profile[i][1][0]))**2 + (float(position[1]) - float(profile[i][1][1]))**2)
            elif profile[i][0] == 'A':
                d = math.sqrt((float(position[0]) - float(profile[i][1][5]))**2 + (float(position[1]) - float(profile[i][1][6]))**2)
            if min_d == -1:
                min_d = d
            elif d < min_d:
                min_d = d
        return min_d

    def define_properties(self, properties):
        '''
        Defines the set of properties for a machining operation, to avoid any empty information during calculation.
            arguments:
                - properties:dict properties for a machining operation.
        '''
        result = {
        'target_depth' : 0 if 'target_depth' not in properties.keys() else properties['target_depth'],
        'cut_feedrate' : 0 if 'cut_feedrate' not in properties.keys() else properties['cut_feedrate'],
        'plunge_feedrate' : 0 if 'plunge_feedrate' not in properties.keys() else properties['plunge_feedrate'],
        'drill_type' : 'straight' if 'drill_type' not in properties.keys() else properties['drill_type'],
        'drill_radius' : 8 if 'drill_radius' not in properties.keys() else properties['drill_radius'],
        'depth_increment' : 0.1 if 'depth_increment' not in properties.keys() else properties['depth_increment'],
        'stock_surface' : 0 if 'stock_surface' not in properties.keys() else properties['stock_surface'],
        'clearance_pane' : 20 if 'clearance_pane' not in properties.keys() else properties['clearance_pane'],
        'holding_tabs_width' : 10 if 'holding_tabs_width' not in properties.keys() else properties['holding_tabs_width'],
        'holding_tabs_height' : 10 if 'holding_tabs_height' not in properties.keys() else properties['holding_tabs_height'],
        'holding_tabs_number' : 3 if 'holding_tabs_number' not in properties.keys() else properties['holding_tabs_number']
        }

        # target depth should always be negative
        if result['target_depth'] > 0:
            result['target_depth'] = -1 * result['target_depth']
        # depth increment should always be negative
        if result['depth_increment'] > 0:
            result['depth_increment'] = -1 * result['depth_increment']
        return result

    def arc_to_circle(self, x1, y1, profile):
        '''
        Translates an elliptic arc to a gcode circle (main difficulty : the center)
            arguments:
                - x1:float x coordinate of the starting point
                - x2:float y coordinate of the starting point
                - profile:list list of arguments defining the arc [rx, ry, phi, fA, fS, x2, y2]
        '''
        fS = float(profile[4])
        rx = float(profile[0])
        ry = float(profile[1])
        x1 = float(x1)
        y1 = float(y1)

        PIx2 = math.pi * 2
        if rx < 0:
            rx = -rx
        if ry < 0:
            ry = -ry
        if rx == 0 or ry == 0:
            raise ValueError('0 given for an arc definition rx or ry')

        s_phi = math.sin(float(profile[2]))
        c_phi = math.cos(float(profile[2]))
        hd_x = (x1 - float(profile[5])) / 2
        hd_y = (y1 - float(profile[6])) / 2
        hs_x = (x1 + float(profile[5])) / 2
        hs_y = (y1 + float(profile[6])) / 2

        x1_ = c_phi * hd_x + s_phi * hd_y
        y1_ = c_phi * hd_y - s_phi * hd_x

        lambd = (x1_**2)/(rx**2) + (y1_**2)/(ry**2)
        if lambd > 1:
            rx = rx * math.sqrt(lambd)
            ry = ry * math.sqrt(lambd)

        rxry = rx * ry
        rxy1_ = rx * y1_
        ryx1_ = ry * x1_
        sum_of_sq = (rxy1_**2) + (ryx1_**2)
        coe = math.sqrt(abs((rxry**2 - sum_of_sq) / sum_of_sq))
        if float(profile[3]) == float(profile[4]):
            coe = -coe

        cx_ = coe * rxy1_ / ry
        cy_ = -coe * ryx1_ / rx

        cx = c_phi * cx_ - s_phi * cy_ + hs_x
        cy = s_phi * cx_ + c_phi * cy_ + hs_y

        xcr1 = (x1_ - cx_) / rx
        xcr2 = (x1_ + cx_) / rx
        ycr1 = (y1_ - cy_) / ry
        ycr2 = (y1_ + cy_) / ry

        startAngle = self.radian(1.0, 0.0, xcr1, ycr1)
        deltaAngle = self.radian(xcr1, ycr1, -xcr2, -ycr2)
        while deltaAngle > PIx2:
            deltaAngle -= PIx2
        while deltaAngle < 0:
            deltaAngle += PIx2
        if fS == False or fS == 0:
            deltaAngle -= PIx2
        endAngle = startAngle + deltaAngle
        while endAngle > PIx2:
            endAngle -= PIx2
        while endAngle < 0:
            endAngle += PIx2

        outputObj = {
        'cx' : cx,
        'cy' : cy,
        'startAngle' : startAngle,
        'deltaAngle' : deltaAngle,
        'endAngle' : endAngle,
        'clockwise' : (fS == True or fS == 1)
        }

        return outputObj

    def radian(self, ux, uy, vx, vy):
        '''
        Returns the radian angle between two vectors
            arguments:
            - ux:float x coordinates of the u vector
            - uy:float y coordinates of the u vector
            - vx:float x coordinates of the v vector
            - vy:float y coordinates of the v vector
        '''
        dot = ux * vx + uy * vy
        mod = math.sqrt(( ux**2 + uy**2) * (vx**2 + vy**2))
        rad = math.acos( dot / mod)
        if ux * vy - uy * vx < 0.0:
            rad = -rad
        return rad

    def add_holding_tabs(self, profile, holding_tabs_number, holding_tabs_width, holding_tabs_height ):
        profile_length = 0
        for i in range(1, len(profile)):
            profile_length += self.curve_length(profile[i], profile[i-1])
        spacing = profile_length / (holding_tabs_number + 1) *1/2

        # browsing the list to find where to place the holding holding tabs (curve must be longer than holding_tabs_width)
        # every time we find one -> cut the curve and add two lines in between : one HTU (holding tab up), one HTD (I don't know what that means)
        d = 0
        it = 1
        i = 1
        while i < len(profile): # the length of profile is going to change (holding tabs insertion, my darling)
            ratio = 1
            l = self.curve_length(profile[i], profile[i-1])
            if d + l > it * spacing and l > holding_tabs_width and l > 30:
                # this is a good place to insert a sweet holding tab.
                curve = profile[i]
                previousCurve = profile[i-1]
                if previousCurve[0] in ['A']:
                    startX = float(previousCurve[1][5])
                    startY = float(previousCurve[1][6])
                elif previousCurve[0] in ['M', 'L', 'HTD', 'HTU']:
                    startX = float(previousCurve[1][0])
                    startY = float(previousCurve[1][1])
                else:
                    startX = 0
                    startY = 0

                # first case : the current curve is a line
                if curve[0] in ['M', 'L', 'HTD']: # M should never happend, as we begin with the index 1. anyway, this is the simple case
                    ratio = ratio = (it * spacing - d)/l
                    if ratio > 0.8:
                        ratio = 0.8
                    elif ratio < 0.2:
                        ratio = 0.2
                    endX = float(curve[1][0])
                    endY = float(curve[1][1])
                    cX = startX + (endX - startX) * ratio # x position of the cut -> for now = center ->CHANGE for ratio (it * spacing - (d + l)) / l
                    cY = startY + (endY - startY) * ratio # y position of the cut -> for now = center
                    ht_startX = cX - (cX - startX) * float(holding_tabs_width) / (2 * math.sqrt((cX - startX)**2 + (cY - startY)**2))
                    ht_startY = cY - (cY - startY) * float(holding_tabs_width) / (2 * math.sqrt((cX - startX)**2 + (cY - startY)**2))
                    ht_endX = cX - (cX - endX) * float(holding_tabs_width) / (2 * math.sqrt((cX - endX)**2 + (cY - endY)**2))
                    ht_endY = cY - (cY - endY) * float(holding_tabs_width) / (2 * math.sqrt((cX - endX)**2 + (cY - endY)**2))
                    # we are going to change the current line to start -> ht_start and insert three new elements : HTU, HTD and ht_end -> end
                    # changing the current line
                    profile[i][1][0] = ht_startX
                    profile[i][1][1] = ht_startY
                    # inserting HTU
                    profile.insert(i + 1, ['HTU', [cX, cY]])
                    # inserting HTD
                    profile.insert(i + 2, ['HTD', [ht_endX, ht_endY]])
                    # inserting the end of the line
                    profile.insert(i + 3, ['L', [endX, endY]])
                    # shifting the index to the right position
                    i += 2
                    it += 1


                # second case : the current curve is an arc
                if curve[0] in ['A']: # this is the difficult case.
                    circle = self.arc_to_circle(startX, startY, curve[1])
                    ratio = (it * spacing - d)/l # (d + l - it*spacing) / l
                    if ratio > 0.9: # can happen because we use a nasty approximation for curve length, and is useful if the HT is too close to a joint
                        ratio = 0.8
                    if ratio < 0.1:
                        ratio = 0.2
                    endX = float(curve[1][5])
                    endY = float(curve[1][6])
                    s = -1
                    if circle['clockwise']:
                        s = -s
                    cX = circle['cx'] + float(curve[1][0]) * math.cos(circle['startAngle'] + circle['deltaAngle'] * ratio)
                    cY = circle['cy'] + float(curve[1][0]) * math.sin(circle['startAngle'] + circle['deltaAngle'] * ratio)
                    ht_startAngle = circle['deltaAngle'] * ratio - float(holding_tabs_width)/ (2 * float(curve[1][0]))
                    ht_endAngle = circle['deltaAngle'] * ratio + float(holding_tabs_width)/ (2 * float(curve[1][0]))
                    ht_startX = circle['cx'] + float(curve[1][0]) * math.cos(circle['startAngle'] + ht_startAngle)
                    ht_startY = circle['cy'] + float(curve[1][0]) * math.sin(circle['startAngle'] + ht_startAngle)
                    ht_endX = circle['cx'] + float(curve[1][0]) * math.cos(circle['startAngle'] + ht_endAngle)
                    ht_endY = circle['cy'] + float(curve[1][0]) * math.sin(circle['startAngle'] + ht_endAngle)
                    # we are going to change the current arc to a new arc start -> ht_Start and insert three new elements : HTU, HTD and a new arc ht_end -> end
                    # changing the current arc
                    profile[i][1][5] = ht_startX
                    profile[i][1][6] = ht_startY
                    # inserting HTU
                    profile.insert(i + 1, ['HTU', [cX, cY]])
                    # inserting HTD
                    profile.insert(i + 2, ['HTD', [ht_endX, ht_endY]]) # ht_endX, ht_endY]])
                    # inserting the second arc
                    profile.insert(i + 3, ['A', [curve[1][0], curve[1][1], curve[1][2], curve[1][3], curve[1][4], endX, endY]])
                    # shifting the index to the right position
                    i += 2
                    it += 1
            i+=1
            d += l*ratio


        return profile

    def curve_length(self, curve, previousCurve):
        length = 0

        # determining the starting point of the curve
        if previousCurve[0] in ['M', 'L', 'HTU', 'HTD']:
            startX = previousCurve[1][0]
            startY = previousCurve[1][1]
        elif previousCurve[0] in ['A']:
            startX = previousCurve[1][5]
            startY = previousCurve[1][6]

        if curve[0] in ['M', 'L']:
            # just calculate the distance between the two points #WOWengineering #Ishoulddothiswithmachinelearningandblockchain
            length = math.sqrt((float(curve[1][0]) - float(startX))**2 + (float(curve[1][1]) - float(startY))**2)
        elif curve[0] in ['A']:
            circle = self.arc_to_circle(startX, startY, curve[1])
            length = float(curve[1][0]) * circle['deltaAngle']
            # for now we'll do with the awful approximation length = PI*r (most arcs are half circles for me) #Imalazyf**k
            # length = math.pi * math.sqrt((float(curve[1][5]) - float(startX))**2 + (float(curve[1][6]) - float(startY))**2) / 2

        return length

    def offset_curve(self, input_profile, distance, direction):
        """
        Returns a list of svg paths with parallels  to the profile path, offseted by the value of distance and in the given direction.
        As the purpose of this function is to fill pockets, self_intersecting paths will be broken and selected.
            Arguments:
                - profile:list svg path (defined as [['type', [coordinates]]])
                - distance:float distance from the profile to the result
                - direction:str can be 'inside' or 'outside'
        """
        r = distance
        # the first element of the path should be 'M' (which means Move: used to set the beginning of the path.)
        # this point is also the end of the last path element, if the path is closed. As we always consider paths to be closed, we delete this element.
        profile = input_profile[1:] if input_profile[0][0] == 'M' else input_profile

        # determine the direction of the path (clockwise or counter-clockwise)
        cw = 0
        calc_cw = 0
        for i in range(1, len(profile)): # first element is M, not to be considered...
            j = (i - 1) % len(profile)
            sx = profile[j][1][0] if profile[j][0] in ['M', 'L'] else profile[j][1][5]
            sy = profile[j][1][1] if profile[j][0] in ['M', 'L'] else profile[j][1][6]
            ex = profile[i][1][0] if profile[i][0] in ['M', 'L'] else profile[i][1][5]
            ey = profile[i][1][1] if profile[i][0] in ['M', 'L'] else profile[i][1][6]
            calc_cw += (ex - sx) * (ey + sy)
        cw = True if calc_cw > 0 else False
        od = 1 # od means offset direction
        if cw:
            od = -od
        if direction == "inside":
            od = -od
        raw_offset = []
        for i in range(0, len(profile)):
            # for each node, determine the angle between both incoming and outing tangent
            pc = profile[(i - 1)%len(profile)] # previous curve
            c = profile[i] # curve
            nc = profile[(i + 1)%len(profile)] # next curve
            p = self.get_point_from_curve(c) # point
            # for the next points, it's a bit different : if the curve is a line, we just have to use its ending point.
            # However, if the curve is an arc, we have to use the tangent of the curve...
            # (for pc : the qestion is if the current curve is an arc or a line) (this paragraph is a pure mindf**k)
            if nc[0] in ['M', 'L']:
                np = self.get_point_from_curve(nc)
            else:
                np = self.get_point_tangent_arc(nc, p, 'start')
            if c[0] in ['M', 'L']:
                pp = self.get_point_from_curve(pc)
            else:
                pp = self.get_point_tangent_arc(c, self.get_point_from_curve(pc), 'end')
            # we define two vectors : u is the vector p-pp, v is the vector p-np
            u = [pp[0] - p[0], pp[1] - p[1]]
            v = [np[0] - p[0], np[1] - p[1]]
            u_len = math.sqrt(u[0]**2 + u[1]**2)
            v_len = math.sqrt(v[0]**2 + v[1]**2)
            angle = math.acos((u[0] * v[0] + u[1] * v[1]) / (u_len * v_len))
            # now we have the angle between the two vectors. To know if the oriented angle is this one or 2*PI - angle, we have to check for this sub_profile's direction.
            # easy my friend : we calculate its clockwise value and check if it's equal to cw.
            # sub_cw = (p[0] - cpp[0]) * (p[1] + cpp[1]) + (cnp[0] - p[0]) * (cnp[1] + p[1]) + (cpp[0] - cnp[0]) * (cpp[1] + cnp[1])
            sub_cw = (p[0] - pp[0]) * (p[1] + pp[1]) + (np[0] - p[0]) * (np[1] + p[1]) + (pp[0] - np[0]) * (pp[1] + np[1])
            if (sub_cw > 0) == cw and direction == 'outside':
                angle = 2 * math.pi - angle
            if (sub_cw > 0) != cw and direction == 'inside':
                angle = 2 * math.pi - angle
            # add a new point and the corresponding curve.
            # anyway, we need the angle between the previous line and the X axis. We'll call it beta
            p_len = math.sqrt((p[0] - pp[0])**2 + (p[1] - pp[1])**2)
            beta = self.guess_angle((p[1] - pp[1]) / p_len, (p[0] - pp[0]) / p_len)
            if angle > math.pi:
                # endpoint is the original offset of the point.
                ax = p[0] + math.cos(beta - od * math.pi / 2) * r
                ay = p[1] + math.sin(beta - od * math.pi / 2) * r
                if c[0] == 'A':
                    radius_dir = self.radius_dir(c[1][4], direction, cw)
                    raw_offset.append(['A', [abs(c[1][0] + radius_dir * r), abs(c[1][1] + radius_dir * r), c[1][2], c[1][3], c[1][4], ax, ay]])
                else:
                    raw_offset.append([c[0], [ax, ay]])
                # Then insert a new point orthogonally offset from the same point to the second tangent
                p_len2 = math.sqrt((np[0] - p[0])**2 + (np[1] - p[1])**2)
                beta2 = self.guess_angle((np[1] - p[1]) / p_len2, (np[0] - p[0]) / p_len2)
                bx = p[0] + math.cos(beta2 - od * math.pi / 2) * r
                by = p[1] + math.sin(beta2 - od * math.pi / 2) * r
                arc_dir = 1
                if cw and direction == 'outside':
                    arc_dir = 0
                if cw == False and direction == 'inside':
                    arc_dir = 0
                raw_offset.append(['A', [r, r, 0, 0, arc_dir, bx, by]])
            else:
                # endpoint is the offset of p on the bisectrix of the two vectors
                ax = p[0] - math.cos(beta + od * angle / 2) * r / math.sin(angle / 2)
                ay = p[1] - math.sin(beta + od * angle / 2) * r / math.sin(angle / 2)
                if c[0] == 'A':
                    radius_dir = self.radius_dir(c[1][4], direction, cw)
                    raw_offset.append(['A', [abs(c[1][0] + radius_dir * r), abs(c[1][1] + radius_dir * r), c[1][2], c[1][3], c[1][4], ax, ay]])
                else:
                    raw_offset.append([c[0], [ax, ay]])
        # we defined a closed loop. to use it as an SVG, we have to add a 'M' element at the beginning, that will point to the last point
        raw_offset.insert(0, ['M', self.get_point_from_curve(raw_offset[-1])])
        # now, we break the profile in several sub_profile, breaking points are each auto-intersection point
        raw_offset = self.break_profile(raw_offset, cw)
        # we go through the list of sub_profiles and we remove the ones that don't have the same clockwise direction
        raw_offset = self.remove_inverted_profiles(raw_offset, cw)
        # we clean the profiles (technically, we round every float to avoid scientific notation...)
        raw_offset = [self.clean(profile) for profile in raw_offset]
        return raw_offset

    def break_profile(self, input_profile, cw):
        """
        Returns a list of non_autosecant profiles produced from the given profile. Each sub_profile that doesn't have the same clockwise value as cw is deleted
        WARNING : ONLY WORKS FOR LINES INTERSECTION FOR NOW. if an arc intersects with anything else, I don't know yet how to catch it.
            Arguments:
                - profile:list profile svg path defined like this : [['type', [properties]]]
        """
        result = []
        collision = True
        # i = 0
        # j = 0
        # k = 0
        result.append(input_profile)
        while collision == True:
            collision = False
            k = 0
            while k < len(result):
                profile = result[k]
                i = 0
                j = 0
                while collision == False and i < len(profile):
                    if profile[i][0] in ['L']:
                        j = i + 1
                        while j < len(profile) and collision == False:
                            if profile[i][0] in ['L']:
                                previous_i = (i - 1) % len(profile)
                                previous_j = (j - 1) % len(profile)
                                s1 = self.get_point_from_curve(profile[previous_i])
                                e1 = self.get_point_from_curve(profile[i])
                                s2 = self.get_point_from_curve(profile[previous_j])
                                e2 = self.get_point_from_curve(profile[j])
                                intersect = self.do_they_intersect(s1, e1, s2, e2)
                                if intersect != []: # the two lines intersect, and we have the coordinates of the intersection point
                                    collision = True
                                    # first : add the current path, just remove the other range and change the line at the i index to make it end at the intersection point
                                    temp = profile[:i + 1] + profile[j:]
                                    temp[i][1] = [intersect[0], intersect[1]]
                                    result[k] = temp
                                    # second : add an 'M' movement to the beginning of the path, and end the last element (index j-i) at the intersection point
                                    temp2 = profile[i:j + 1]
                                    temp2[j-i] = temp2[j-i].copy() # Necessary, to avoid modifying the other profile (python works with references, not copies of the lists) (man, it took me so long to spot this s**t...)
                                    temp2[j-i][1] = [intersect[0], intersect[1]]
                                    temp2.insert(0, ['M', [intersect[0], intersect[1]]])
                                    result.append(temp2)
                            j += 1
                    i += 1
                k += 1
        return result

    def remove_inverted_profiles(self, raw_offset, cw):
        result = []
        for profile in raw_offset:
            calc_cw = 0
            for i in range(1, len(profile)): # first element is M, not to be considered...
                j = (i - 1) % len(profile)
                sx = profile[j][1][0] if profile[j][0] in ['M', 'L'] else profile[j][1][5]
                sy = profile[j][1][1] if profile[j][0] in ['M', 'L'] else profile[j][1][6]
                ex = profile[i][1][0] if profile[i][0] in ['M', 'L'] else profile[i][1][5]
                ey = profile[i][1][1] if profile[i][0] in ['M', 'L'] else profile[i][1][6]
                calc_cw += (ex - sx) * (ey + sy)
            if (calc_cw > 0) == cw:
                result.append(profile)
        return result

    def do_they_intersect(self, s1, e1, s2, e2):
        """
        Returns the coordinates of the intersection point if the segments [s1, e1] and [s2, e2] intersect, [either]
            Arguments:
            - s1:list coordinates of the first segment's starting point in the format [x, y]
            - e1:list coordinates of the first segment's ending point in the format [x, y]
            - s2:list coordinates of the second segment's starting point in the format [x, y]
            - e2:list coordinates of the second segment's ending point in the format [x, y]
        """
        result = []
        if (self.ccw(s1,s2,e2) != self.ccw(e1,s2,e2) and self.ccw(s1,e1,s2) != self.ccw(s1,e1,e2)) and e1 != s2 and s1 != e2: # in this case, the segments intersect (don't ask me why, ask this guy : https://stackoverflow.com/questions/3838329/how-can-i-check-if-two-segments-intersect)
            # we calculate the intersection's coordinates
            # for this, we first have to calculate the coefficients of both segments equation
            A1 = (e1[1] - s1[1]) / (e1[0] - s1[0] + 0.000001)
            B1 = s1[1] - A1 * s1[0]
            A2 = (e2[1] - s2[1]) / (e2[0] - s2[0] + 0.000001)
            B2 = s2[1] - A2 * s2[0]
            x = (B1 - B2) / (A2 - A1)
            y = A1 * x + B1
            result = [x, y]
        return result

    def ccw(self, A, B, C):
        """
        measure whereas the shape is counterlclockwise or not. only used for the line intersection detection
            Arguments:
                - A:list point in the format [x, y]
                - B:list point in the format [x, y]
                - C:list point in the format [x, y]
        """
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    def guess_angle(self, sin, cos):
        """
        I didn't know how precise the arcos and arcsin function are, so I decided not to take any risk.
        Please don't judge me.
            Arguments:
                - cos:float cosinus of the angle
                - sin:float Avogadro's number divided by the number of days until the next full moon
        """
        c = math.acos(cos)
        s = math.asin(sin)
        return abs(c) if s > 0 else -abs(c)

    def get_point_from_curve(self, curve):
        """
        Returns the 2D coordinates of the given curve's ending point.
        Necessary because the coordinates indexes depend on the curve's nature.
            Arguments:
                - curve:list curve defined in a standard way : ['type', ['properties']]
        """
        result = []
        if curve[0] in ['M', 'L', 'HTD', 'HTU']: # the curve is a line (or a movement, or a holding tab, which is exactly the same)
            result = [curve[1][0], curve[1][1]]
        else: # the curve is an arc (in which case the coordinates are stored in 5th and 6th position in the curve properties list)
            result = [curve[1][5], curve[1][6]]
        return result

    def get_point_tangent_arc(self, curve, sp, position):
        """
        Returns the 2D coordinates of a point which will define the tangent to the arc on the origin or end point, in the same direction as the arc itself.
            Arguments :
                - curve:list curve defined in a standard way : ['type', ['properties']]
                - sp:list 2D coordinates of the arc_s starting point
                - position:str can be 'start' or 'end'
        """
        # strategy :
        #   - find the center of the arc
        #   - calculate the angle alpha between the Ox axis and the center-startpoint segment -> the angle between the tangent and Ox is alpha - PI/2
        #   - calculate the tangent point (we'll call it a) position with radial coordinates
        circle = self.arc_to_circle(sp[0], sp[1], curve[1])
        c = [circle['cx'], circle['cy']]
        if position == 'start':
            # we have the circle center, now we calculate the vector coordinates, its length and its angle with Ox
            u = [sp[0] - c[0], sp[1] - c[1]]
            u_len = math.sqrt(u[0]**2 + u[1]**2)
            u_cos = u[0] / u_len
            u_sin = u[1] / u_len
            alpha = self.guess_angle(u_sin, u_cos)
            # calculate the position of a, given that the distance sp -> a is 10 (no reason for 10...)
            dir = -1
            if float(curve[1][4]) == 0:
                dir = 1
            a_x = sp[0] + 10 * math.cos(alpha - dir * math.pi / 2)
            a_y = sp[1] + 10 * math.sin(alpha - dir * math.pi / 2)
        else:
            # we have the circle center, now we calculate the vector coordinates, its length and its angle with Ox
            u = [curve[1][5] - c[0], curve[1][6] - c[1]]
            u_len = math.sqrt(u[0]**2 + u[1]**2)
            u_cos = u[0] / u_len
            u_sin = u[1] / u_len
            alpha = self.guess_angle(u_sin, u_cos)
            # calculate the position of a, given that the distance sp -> a is 10 (no reason for 10...)
            dir = -1
            if float(curve[1][4]) == 0:
                dir = 1
            a_x = curve[1][5] + 10 * math.cos(alpha + dir * math.pi / 2)
            a_y = curve[1][6] + 10 * math.sin(alpha + dir * math.pi / 2)
        return [a_x, a_y]

    def radius_dir(self, sweep_flag, direction, cw):
        """
        Calculates if the radius of the new arc has to be superior or inferior to its reference.
            Arguments:
                - sweep_flag:int sweep_flag value of the circle (can be 0 or 1)
                - direction:str can be 'inside' or 'outside'
                - cw:bool clockwise or counter-clockwise
        """
        result = 1
        temp = True
        if float(sweep_flag) == 0 and cw == False:
            temp = False
        if float(sweep_flag) == 1 and cw == True:
            temp = False
        if direction == 'inside' and temp:
            result = -1
        if direction == 'outside' and temp == False:
            result = -1
        return result

    def clean(self, profile):
        """
        Returns a clean version on profile, which means a version where every float is rounded to the 5th decimal, in order to avoid scientific writing
            Arguments:
                - profile:list profile defined as : [[type, [properties]]]
        """
        result = []
        for el in profile:
            result.append([el[0], [round(e, 6) for e in el[1]]])
        return result


















# dfsdjflksdjl
