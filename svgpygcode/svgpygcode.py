# svgpygcode

import math

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






















# dfsdjflksdjl
