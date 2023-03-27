import hassapi as hass
import csv
import datetime
from PIL import Image, ImageDraw, ImageFont

# You can adjust colors and style here

LINE_THICKNESS = 2
LINE_COLOR_RGB = (255, 0, 0)

POINT_COLOR_RUNNING = (0, 255, 0)
POINT_COLOR_RETURN = (255, 255, 0)
POINT_COLOR_STUCK = (0, 0, 255)
POINT_COLOR_DOCKED = (255, 255, 255)

# TODO need to use absolute path? Relative paths in this format do not work. fonts folder is in the apps folder, where the script is
font = ImageFont.truetype("/config/appdaemon/apps/fonts/Arimo-Bold.ttf", size=32)

VACUUM_LOG_PATH = "/config/www/tmp/vacuum_{name}/vacuum.log"
MAP_OUTPUT_PATH = "/config/www/tmp/vacuum_{name}/map.png"


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
    - pillow python package (Read INSTALL_PY_PACKAGES.md)

    Required arguments:
    - debug:
        Enable debug log
    - vacuum_entity:
        Your vacuum entity. E.g. 'vacuum.roomba'
    - vacuum_name:
        Used for naming the vacuum folders.
    - floor_plan_location:
        The file path of your floor plan. E.g. '/config/floorplans/home.png'
    - offset_cords_x:
        Adjust the offset so the generated lines match the floor plan
    - offset_cord_y:
        Adjust the offset so the generated lines match the floor plan
    - image_rotation:
        If the cords aren't drawn correctly to the map, you can try it with rotating the image (0, 90, 180, 270)

    FIXME This requires some extra steps in HA.
    TODO log roomba's cords with AD and do not require additional setup in HA.

    """

    def initialize(self):
        self.line_space = 0
        self.draw = None
        self.draw_last_x = 0
        self.draw_last_y = 0

        self.offset_cords_x = int(self.args['offset_cords_x'])
        self.offset_cords_y = int(self.args['offset_cords_y'])

        self.debug = self.args['debug']

        self.vacuum = self.get_entity(self.args['vacuum_entity'])

        self.map_path = self.args['floor_plan_location']
        self.vacuum_log_path = VACUUM_LOG_PATH.replace("{name}", self.args['vacuum_name'])
        self.map_output_path = MAP_OUTPUT_PATH.replace("{name}", self.args['vacuum_name'])

        self.image_rotation = self.args['image_rotation']

        self.generate_image()

        # Listen for position changes
        # TODO reduce disk writes
        self.run_every(self.generate_image, start=self.datetime(), interval=5)
        #self.vacuum.listen_state(self.generate_image, attribute="all")
        self.vacuum.listen_state(self.write_log, attribute="position")
        self.vacuum.listen_state(self.clear_log, old="docked", new="cleaning", duration=10)

    def mylog(self, msg):
        if self.debug:
            self.log(msg)

    def write_point(self, color, location):
        # cv2.circle(image, location, radius=14, color=color, thickness=-1)
        self.mylog("TODO draw point")

    def write_point_info(self, color, text):
        self.write_point(color, (15, self.line_space + 15))
        self.draw.text((30, self.line_space + 23), text, color, font=font)
        self.line_space += 30

    def write_log(self, entity, attribute, old, new, kwargs):
        f = open(self.vacuum_log_path, "a")

        #vacuum_position = self.vacuum.get_state(attribute="position").strip("()").split(', ')

        vacuum_position = new.strip("()").split(', ')
        x = vacuum_position[0]
        y = vacuum_position[1]

        f.write(f"{x},{y}\n")
        f.close()

        #self.update_image(int(x), int(y))

    def clear_log(self):
        with open(self.vacuum_log_path, 'r+') as file:
            file.truncate(0)

    def update_image(self, x, y):
        # TODO not really working because the old roomba location point is still on the map.
        # Pillow does not have an undo function for that, which means we have to render the whole image again.

        image = Image.open(self.map_path)
        image = image.rotate(self.image_rotation)
        self.draw = ImageDraw.Draw(image)

        x += self.offset_cords_x
        y += self.offset_cords_y

        self.draw.line([(y, x), (self.draw_last_y, self.draw_last_x)], width=LINE_THICKNESS, fill=LINE_COLOR_RGB)
        self.draw_last_x = x
        self.draw_last_y = y

        image = image.rotate(-self.image_rotation)
        image.save(self.map_output_path, "PNG")

    def generate_image(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        # Get data from HA
        vacuum_state = self.vacuum.get_state()

        if vacuum_state == "docked":
            return;

        self.mylog("Vacuum state: {}".format(vacuum_state))

        # Load base image
        image = Image.open(self.map_path)
        self.draw = ImageDraw.Draw(image)

        self.write_point_info(POINT_COLOR_DOCKED, "Angedockt")
        self.write_point_info(POINT_COLOR_RUNNING, "Saugen")
        self.write_point_info(POINT_COLOR_RETURN, "Rueckkehr")
        self.write_point_info(POINT_COLOR_STUCK, "Steckt fest")
        self.line_space = 0

        image = image.rotate(self.image_rotation)
        self.draw = ImageDraw.Draw(image)

        with open(self.vacuum_log_path, 'r') as f:
            reader = csv.reader(f, delimiter=",")

            #next(reader, None)

            first_line = True

            for row in reader:
                x = int(row[0]) + self.offset_cords_x
                y = int(row[1]) + self.offset_cords_y
                # self.mylog("X:{} Y:{}".format(x, y))
                # self.mylog("Last X:{} Last Y:{}".format(self.draw_last_x, self.draw_last_y))

                if first_line:
                    self.draw_last_x = x
                    self.draw_last_y = y
                    first_line = False

                else:
                    self.draw.line([(y, x), (self.draw_last_y, self.draw_last_x)], width=LINE_THICKNESS, fill=LINE_COLOR_RGB)
                    self.draw_last_x = x
                    self.draw_last_y = y

        # Write current vacuum state to the map image
        if vacuum_state == "docked":  # or vacuum_status == "charging"
            self.write_point(POINT_COLOR_DOCKED, (self.draw_last_y, self.draw_last_x))
        elif vacuum_state == "running":
            self.write_point(POINT_COLOR_RUNNING, (self.draw_last_y, self.draw_last_x))
        elif vacuum_state == "return":
            self.write_point(POINT_COLOR_RETURN, (self.draw_last_y, self.draw_last_x))
        elif vacuum_state == "stuck":
            self.write_point(POINT_COLOR_STUCK, (self.draw_last_y, self.draw_last_x))

        # Rotate image to match the floor plan and save
        image = image.rotate(-self.image_rotation)
        image.save(self.map_output_path, "PNG")
