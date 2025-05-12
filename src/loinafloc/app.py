"""
Cette application vous permet de créer vos courses d'orientations sur une carte du monde
"""

import toga, sys, asyncio
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from toga.widgets.box import Box
from toga.window import MainWindow
from toga.app import App
from toga.widgets.mapview import *
from toga.dialogs import InfoDialog

class Globalorientation(App):
    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        self.main_box = Box()

        self.main_window = MainWindow(title=self.formal_name)
        self.main_window.content = self.main_box
        self.main_window.show()

        asyncio.create_task(self.main())

    async def main(self):
        if self.location.has_permission:
            #location_state = await self.location.request_permission()
            localisation = await self.location.current_location()
            print(localisation[0], localisation[1])
            map_view = MapView(location=localisation, style=Pack(flex=1), zoom=4)
            location_pins = MapPin(location=localisation, title="Vous êtes ici")
            map_view.pins.add(location_pins)
        else:
            map_view = MapView(location=[46.740948, 2.535976], style=Pack(flex=1), zoom=4)
        self.main_box.add(map_view)

        if not self.location.has_permission:
            InfoDialog("Permission requise", "Nous avons besoins d'accéder à votre position pour que l'application fonctionne sans problème!")
            location_state = await self.location.request_permission()
            if location_state == False:
                sys.exit()


def main():
    return Globalorientation()
