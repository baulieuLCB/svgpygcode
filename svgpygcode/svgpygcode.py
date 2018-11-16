# svgpygcode

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
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, holding_tabs_height, holding_tabs_number, holding_tabs_width
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
            print(self.contours[i])
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
        for i in range (0, len(self.contours)):
            self.order.append(i)

    def profile(self, svg_path, type, properties):
        '''
        Determines the gcode string for a profile cut.
            arguments:
                - svg_path:str 'd' attribute of your path component
                - operation_type:str description of the operation : 'profile_inside', 'profile_outside', 'pocket_inside', 'pocket_outside', 'engraving'
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, holding_tabs_height, holding_tabs_number, holding_tabs_width
        '''
        self.gcode += ("ajout d'un profil de type :\n" + type + "\n")
        self.current_position = [1, 1]

    def pocket(self, svg_path, type, properties):
        '''
        Determines the gcode string for a pocket cut.
            arguments:
                - svg_path:str 'd' attribute of your path component
                - operation_type:str description of the operation : 'profile_inside', 'profile_outside', 'pocket_inside', 'pocket_outside', 'engraving'
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, holding_tabs_height, holding_tabs_number, holding_tabs_width
        '''
        self.gcode += ("ajout d'une poche de type :\n" + type + "\n")
        self.current_position = [1, 1]

    def engraving(self, svg_path, type, properties):
        '''
        Determines the gcode string for an engraving cut.
            arguments:
                - svg_path:str 'd' attribute of your path component
                - operation_type:str description of the operation : 'profile_inside', 'profile_outside', 'pocket_inside', 'pocket_outside', 'engraving'
                - properties:dict contains the machining characteristics : target_depth, cut_feedrate, plunge_feedrate, drill_type, drill_radius, depth_increment, stock_surface, holding_tabs_height, holding_tabs_number, holding_tabs_width
        '''
        self.gcode += ("ajout d'une gravure de type :\n" + type + "\n")
        self.current_position = [1, 1]

    def parse_path(self, svg_path):
        '''
        Parses a string SVG to a list of line / elliptic arc / bezier elements.
            arguments:
                - svg_path:str 'd' attribute of your path component
        '''
        result = []
        return result
