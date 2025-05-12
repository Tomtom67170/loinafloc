"""
Cette application vous permet de créer vos courses d'orientations sur une carte du monde
"""

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from toga.widgets.box import Box
from toga.window import MainWindow
from toga.app import App
from toga.widgets.mapview import *

class Globalorientation(App):
    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        main_box = Box()

        self.main_window = MainWindow(title=self.formal_name)
        self.main_window.content = main_box

        de_gaulle = MapPin(location=[48.762281, 7.689851], title="Wahlenheim de Gaulle", subtitle="Un super arrêt de bus")
        map_view = MapView(location=[48.762659, 7.688413], style=Pack(flex=1), zoom=18)
        map_view.pins.add(de_gaulle)
        main_box.add(map_view)
        self.main_window.show()


def main():
    return Globalorientation()
