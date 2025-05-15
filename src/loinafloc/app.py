"""
Cette application vous permet de créer vos courses d'orientations sur une carte du monde
"""

import toga, sys, asyncio, time
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from toga.widgets.box import Box
from toga.widgets.label import Label
from toga.window import MainWindow
from toga.widgets.progressbar import ProgressBar
from toga.app import App
from toga.widgets.mapview import *
from toga.dialogs import InfoDialog, ErrorDialog

class Globalorientation(App):
    def clear(self):
        self.main_box = Box(style=Pack(direction=COLUMN))
        self.main_window.content = self.main_box

    def reset_map_view(self):
        location = self.map_view.location
        zoom = self.map_view.zoom
        self.map_view = MapView(location=location, zoom=zoom, style=Pack(flex=1))
        self.map_view.pins.add(self.position_pin)

    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        self.main_box = Box(style=Pack(direction=COLUMN))

        self.main_window = MainWindow(title=self.formal_name)
        self.main_window.content = self.main_box
        self.main_window.show()

        print("Application démarrée")

        asyncio.create_task(self.starting())

    async def starting(self):
        if not self.location.has_permission:
            await self.main_window.dialog(InfoDialog("Permission requise", "Nous avons besoins d'accéder à votre position pour que l'application fonctionne sans problème!"))
            location_state = await self.location.request_permission()
            if location_state == False:
                sys.exit()
        start_text = Label("Démarrage...", style=Pack(font_size=24, flex=1, text_align="center", margin_top=30))
        progressbar = ProgressBar(style=Pack(margin=(5, 30), flex=1), max=None, running=True)
        self.position_pin = MapPin(location=[0, 0], title="Vous êtes ici")
        self.main_box.add(start_text, progressbar)
        self.loc_found = False
        self.location.on_change = self.init_loc
        self.location.start_tracking()
        self.start_time = time.time() + 1
        await asyncio.sleep(10)
        self.location.stop_tracking()
        if self.loc_found == False: #Le GPS n'a pas trouvé de positions ==> main n'est pas lancé
            print("Pas de signal")
            self.map_view = MapView(location=[46.740948, 2.535976], style=Pack(flex=1), zoom=4)
            error_label = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", background_color="#ff0000", text_align="center"))
            loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
            self.clear()
            self.main_box.add(error_label, loading, self.map_view)
            self.last_update = time.time() - 120
            self.location_state = False
            await self.main()

    async def main(self):
        print("Initialisation check_pos")
        asyncio.create_task(self.check_pos())
        print("main démarré")
        if self.location.has_permission:
            self.location.on_change = self.update_pos
            self.location.start_tracking()

    async def update_pos(self, *args, **kwargs):
            print("position mis à jour")
            location = kwargs.get("location", None)
            altitude = kwargs.get("altitude", None)
            self.position_pin.location = location
            if not self.position_pin in self.map_view.pins:
                print("Pins mis à jour")
                self.map_view.pins.add(self.position_pin)
                if self.location_state == False:
                    await asyncio.sleep(2)
            self.last_update = time.time()

    async def check_pos(self):
        while True:
            if time.time() - self.last_update >= 30:
                if self.location_state: #devient obsolète
                    self.clear()
                    self.reset_map_view()
                    error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
                    loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
                    self.main_box.add(error_text, loading, self.map_view)
                    self.location_state = False
            else:
                if not(self.location_state):
                    self.clear()
                    self.reset_map_view()
                    self.main_box.add(self.map_view)
                    self.location_state = True
            await asyncio.sleep(0.1)

    async def init_loc(self, *args, **kwargs):
        location = kwargs.get("location", None)
        altitude = kwargs.get("altitude", None)
        self.loc_found = True
        self.map_view = MapView(location=location, zoom=18, style=Pack(flex=1))
        self.position_pin = MapPin(location=location, title="Vous êtes ici")
        while (time.time() - self.start_time <= 10):
            pass
        self.clear()
        self.map_view.pins.add(self.position_pin)
        self.main_box.add(self.map_view)
        self.last_update = time.time()
        self.location_state = True
        await self.main()

def main():
    return Globalorientation()
