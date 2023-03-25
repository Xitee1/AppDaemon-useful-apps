import hassapi as hass
import csv
from PIL import Image, ImageDraw, ImageFont

################
### Settings ###

# Home Assistant
vacuum_entity = "vacuum.roomba"

thickness = 2
color_rgb = (255, 0, 0)

rotation = 1

offset_x = 200
offset_y = 130

# Dot colors
point_color_running = (0, 255, 0)
point_color_return = (255, 255, 0)
point_color_stuck = (0, 0, 255)
point_color_docked = (255, 255, 255)

font = ImageFont.truetype("fonts/Arimo-Bold.ttf", size=32)

### END settings ###
####################

# TODO use args instead hard coded values

class GenerateImage(hass.Hass):
    """
    Generate a map where roomba has cleaned your home.

    This also requires a little extra setup in HA:
    - Add the following to your configuration.yaml:
        camera:
          - platform: local_file
            name: Roomba Karte
            file_path: /config/www/tmp/vacuum_yourRobotName/map.png

    Requirements:
    - A vacuum that exposes its cords as attribute the following format: Position (x, x, x)
    - A floor plan of your home (TODO optional but recommended)

    Required arguments:
    - vacuum_entity:
        Your vacuum entity. E.g. 'vacuum.roomba'
    - floor_plan_location:
        The file path of your floor plan. E.g. '/config/floorplans/home.png'

    FIXME This requires some extra steps in HA.
    TODO log roomba's cords with AD and do not require additional setup in HA.

    """

    def initialize(self):
        self.last_x = 0
        self.last_y = 0
        self.firstLine = True

        self.line_space = 0
        self.draw = None

        self.vacuum = self.get_entity(vacuum_entity)
        self.generate_image()

    def writeHead(self, text):
        self.draw.text((0, self.line_space + 23), text, (100, 200, 255), font=font)
        self.line_space += 30

    def writePoint(self, color, location):
        # cv2.circle(image, location, radius=14, color=color, thickness=-1)
        self.log("TODO draw point")

    def writePointInfo(self, color, text):
        self.writePoint(color, (15, self.line_space + 15))
        self.draw.text((30, self.line_space + 23), text, color, font=font)
        self.line_space += 30

    def generate_image(self, kwargs=None):
        # Get data from HA
        vacuum_status = self.vacuum.get_state(vacuum_entity)

        self.log("Vacuum state: {}".format(vacuum_status))

        # Load base image
        image = Image.open("/config/configuration/vacuum_roomba/floor.png")
        self.draw = ImageDraw.Draw(image)

        self.writeHead("Punkt =")
        self.writeHead("aktuelle")
        self.writeHead("Position")

        self.line_space += 20

        self.writePointInfo(point_color_docked, "Angedockt")
        self.writePointInfo(point_color_running, "Saugen")
        self.writePointInfo(point_color_return, "Rueckkehr")
        self.writePointInfo(point_color_stuck, "Steckt fest")

        image = image.rotate(90)
        self.draw = ImageDraw.Draw(image)

        with open("/config/configuration/vacuum_roomba/vacuum.log", 'r') as f:
            reader = csv.reader(f, delimiter=" ")
            next(reader, None)
            next(reader, None)
            for row in reader:

                x = int(row[0].replace(",", "").replace("(", "")) + offset_x
                y = int(row[1].replace(",", "")) + offset_y
                # self.log("X:{} Y:{}".format(x, y))
                # self.log("Last X:{} Last Y:{}".format(self.last_x, self.last_y))

                if self.firstLine:
                    self.last_x = x
                    self.last_y = y
                    self.firstLine = False

                else:
                    self.draw.line([(y, x), (self.last_y, self.last_x)], width=thickness, fill=color_rgb)

                    self.last_x = x
                    self.last_y = y

        if vacuum_status == "docked":  # or vacuum_status == "charging"
            self.writePoint(point_color_docked, (self.last_y, self.last_x))
        elif vacuum_status == "running":
            self.writePoint(point_color_running, (self.last_y, self.last_x))
        elif vacuum_status == "return":
            self.writePoint(point_color_return, (self.last_y, self.last_x))
        elif vacuum_status == "stuck":
            self.writePoint(point_color_stuck, (self.last_y, self.last_x))

        # Rotate image to match the floor plan and save
        image = image.rotate(-90)
        image.save("/config/www/tmp/vacuum_roomba/map.png", "PNG")
