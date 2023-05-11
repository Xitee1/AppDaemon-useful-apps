import hassapi as hass
import csv
import os
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

VACUUM_LOG_RAW_PATH = "{tmp_path}/vacuum_{name}/vacuum.log"
MAP_OUTPUT_RAW_PATH = "{tmp_path}/vacuum_{name}/map.png"


class GenerateImage(hass.Hass):
    """
    Generates a map of the area cleaned by Roomba.

    To have the image in a camera entity:
    - Add the following to your configuration.yaml:
        camera:
          - platform: local_file
            name: Roomba Karte
            file_path: /config/www/tmp/vacuum_yourRobotName/map.png

    Requirements:
    - A vacuum that exposes its cords as attribute the following format: Position (x, x, x)
    - A floor plan of your home (// TODO make optional (but recommended) //)
    - pillow python package (Read INSTALL_PY_PACKAGES.md)
    - This app needs the "fonts" folder to work. // TODO For now, make sure the fonts are in the absolute path "/config/appdaemon/apps/fonts/Arimo-Bold.ttf"!! //

    Required arguments:
    - debug:
        Enable debug log
    - vacuum_entity:
        Your vacuum entity. E.g. 'vacuum.roomba'
    - vacuum_name:
        Used for naming the vacuum folders.
    - tmp_path:
        Path to a tmp folder where the log and image should be stored. E.g. /config/www/tmp
    - floor_plan_location:
        The file path of your floor plan. E.g. '/config/floorplans/home.png'
    - offset_cords_x:
        Adjust the offset so the generated lines match the floor plan
    - offset_cord_y:
        Adjust the offset so the generated lines match the floor plan
    - image_rotation:
        If the cords aren't drawn correctly to the map, you can try rotating the image (0, 90, 180, 270)

    """

    def initialize(self):
        # Init internal vars
        self.line_space = 0
        self.draw = None

        self.vacuum_cords = []
        self.draw_last_x = 0
        self.draw_last_y = 0
        self.write_log_to_file = True

        # Init args
        self.offset_cords_x = int(self.args['offset_cords_x'])
        self.offset_cords_y = int(self.args['offset_cords_y'])

        self.debug = self.args['debug']

        self.vacuum = self.get_entity(self.args['vacuum_entity'])

        self.map_path = self.args['floor_plan_location']
        self.vacuum_log_path = VACUUM_LOG_RAW_PATH.replace("{tmp_path}", self.args['tmp_path']).replace("{name}", self.args['vacuum_name'])
        self.map_output_path = MAP_OUTPUT_RAW_PATH.replace("{tmp_path}", self.args['tmp_path']).replace("{name}", self.args['vacuum_name'])

        self.image_rotation = self.args['image_rotation']

        # Prepare paths
        os.makedirs(name=os.path.dirname(self.vacuum_log_path), exist_ok=True)
        os.makedirs(name=os.path.dirname(self.map_output_path), exist_ok=True)
        if not os.path.exists(self.vacuum_log_path): # Log file needs to be created if it does not exist.
            open(self.vacuum_log_path, "x")

        # Prepare app
        self.load_log()
        self.generate_image()

        # Listeners
        self.run_every(self.generate_image, start="now+10", interval=10)
        self.vacuum.listen_state(self.write_log, attribute="position")
        self.vacuum.listen_state(self.clear_log, old="docked", new="cleaning", duration=10)
        self.vacuum.listen_state(self.save_log, new="docked")

    def mylog(self, msg):
        if self.debug:
            self.log(msg)
    """
    Log UTILS
    """
    def load_log(self):
        """
        Load the log from the log file
        """
        self.mylog("Loading log file..")

        with open(self.vacuum_log_path, 'r') as f:
            reader = csv.reader(f, delimiter=",")

            for row in reader:
                x = int(row[0])
                y = int(row[1])
                self.vacuum_cords.append([x, y])

    def save_log(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        """
        Save the log to the log file
        """
        self.mylog("Saving log..")

        with open(self.vacuum_log_path, "r+") as f:
            f.truncate(0)

        with open(self.vacuum_log_path, "a") as f:
            for c in self.vacuum_cords:
                f.write(f"{c[0]},{c[1]}\n")

    def write_log(self, entity, attribute, old, new, kwargs):
        """
        Add current cords to log. This however does not save the log to the file.
        """
        vacuum_position = new.strip("()").split(', ')
        x = int(vacuum_position[0])
        y = int(vacuum_position[1])

        self.vacuum_cords.append([x, y])

        # Save log after every write for debug
        if self.debug:
            with open(self.vacuum_log_path, "a") as f:
                f.write(f"{x},{y}\n")

    def clear_log(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        """
        Clears the cords array and the file
        """
        self.mylog("Clearing log..")

        self.vacuum_cords = []
        with open(self.vacuum_log_path, 'r+') as f:
            f.truncate(0)

    """
    Image tools
    """
    def draw_point(self, x, y, color, size=35):
        x2 = x + size
        y2 = y + size

        self.draw.ellipse([(x, y), (x2, y2)], color)

    """
    Generate Map Image
    """
    def generate_image(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        """
        Generates the image and saves it to disk.
        """
        # Get data from HA
        vacuum_state = self.vacuum.get_state()

        if vacuum_state == "docked":
            return

        #self.mylog("Vacuum state: {}".format(vacuum_state))

        # Load base image
        image = Image.open(self.map_path)
        self.draw = ImageDraw.Draw(image)

        #self.write_point_info(POINT_COLOR_DOCKED, "Angedockt")
        #self.write_point_info(POINT_COLOR_RUNNING, "Saugen")
        #self.write_point_info(POINT_COLOR_RETURN, "Rueckkehr")
        #self.write_point_info(POINT_COLOR_STUCK, "Steckt fest")
        #self.line_space = 0

        image = image.rotate(self.image_rotation)
        self.draw = ImageDraw.Draw(image)

        first_run = True
        for c in self.vacuum_cords:
            x = c[0] + self.offset_cords_x
            y = c[1] + self.offset_cords_y

            if first_run:
                first_run = False
            else:
                self.draw.line([(y, x), (self.draw_last_y, self.draw_last_x)], width=LINE_THICKNESS, fill=LINE_COLOR_RGB)

            self.draw_last_x = x
            self.draw_last_y = y

        # Write current vacuum state to the map image
        if vacuum_state == "docked":  # or vacuum_status == "charging"
            self.draw_point(self.draw_last_y, self.draw_last_x, POINT_COLOR_DOCKED)
        elif vacuum_state == "return":
            self.draw_point(self.draw_last_y, self.draw_last_x, POINT_COLOR_RETURN)
        elif vacuum_state == "stuck":
            self.draw_point(self.draw_last_y, self.draw_last_x, POINT_COLOR_STUCK)
        else:
            self.draw_point(self.draw_last_y, self.draw_last_x, POINT_COLOR_RUNNING)

        # Rotate image to match the floor plan and save
        image = image.rotate(-self.image_rotation)
        image.save(self.map_output_path, "PNG")