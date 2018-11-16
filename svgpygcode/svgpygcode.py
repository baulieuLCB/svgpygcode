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
        # for i in range (0, len(self.contours)):
        #     self.order.append(i)

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
            for index in range(0, len(profile)):
                # true index to work with : we are going to
                i = (index + closest_index + 1)%len(profile)
                if profile[i][0] in ['M', 'L']:
                    temp = """G1 X{} Y{} Z{}\n""".format(profile[i][1][0], profile[i][1][1], depth)
                if profile[i][0] == 'A':
                    temp = """G1 X{} Y{} Z{}\n""".format(profile[i][1][5], profile[i][1][6], depth)
                self.gcode += temp
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
            for index in range(0, len(profile)):
                # true index to work with : we are going to
                i = (index + closest_index + 1)%len(profile)
                if profile[i][0] in ['M', 'L']:
                    temp = """G1 X{} Y{} Z{}\n""".format(profile[i][1][0], profile[i][1][1], depth)
                if profile[i][0] == 'A':
                    temp = """G1 X{} Y{} Z{}\n""".format(profile[i][1][5], profile[i][1][6], depth)
                self.gcode += temp
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
