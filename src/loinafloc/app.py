"""
Cette application vous permet de créer vos courses d'orientations sur une carte du monde
"""

import toga, sys, asyncio, time
from toga import platform
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER
from toga.widgets.box import Box
from toga.widgets.label import Label
from toga.widgets.button import Button
from toga.window import MainWindow
from toga.window import Window
from toga.widgets.progressbar import ProgressBar
from toga.widgets.textinput import TextInput
from toga.app import App
from toga.widgets.mapview import *
from toga.dialogs import InfoDialog, ErrorDialog, QuestionDialog
from toga.platform import current_platform

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
        if current_platform != "android":
            await self.main_window.dialog(ErrorDialog("Environnement invalide!", "Cette application a été conçu pour Android! Veuillez installer cette application sur Android, puis réessayer"))
            sys.exit()
        if not self.location.has_permission:
            await self.main_window.dialog(InfoDialog("Permission requise", "Nous avons besoins d'accéder à votre position pour que l'application fonctionne sans problème!"))
            location_state = await self.location.request_permission()
            if location_state == False:
                sys.exit()
        start_text = Label("Démarrage...", style=Pack(font_size=24, flex=1, text_align="center", margin_top=30))
        progressbar = ProgressBar(style=Pack(margin=(5, 30), flex=1), max=100, running=True)
        self.position_pin = MapPin(location=[0, 0], title="Vous êtes ici")
        self.main_box.add(start_text, progressbar)
        self.loc_found = False
        self.location.on_change = self.init_loc
        self.location.start_tracking()
        self.start_time = time.time() + 1
        self.balises = []
        progressbar.value = 10
        await asyncio.sleep(3)
        progressbar.value = 45
        self.main_box.refresh()
        await asyncio.sleep(5)
        progressbar.value = 85
        self.main_box.refresh()
        await asyncio.sleep(2)
        progressbar.value = progressbar.max
        self.main_box.refresh()
        self.location.stop_tracking()
        if self.loc_found == False: #Le GPS n'a pas trouvé de positions ==> main n'est pas lancé
            self.map_view = MapView(location=[46.740948, 2.535976], style=Pack(flex=1), zoom=4)
            error_label = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", background_color="#ff0000", text_align="center"))
            loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
            self.init_act()
            self.clear()
            self.main_box.add(error_label, loading, self.map_view, self.act_box)
            self.last_update = time.time() - 120
            self.location_state = False
            await self.main()

    async def main(self, start=True):
        print("Initialisation check_pos")
        if start:
            asyncio.create_task(self.check_pos())
        print("main démarré")
        self.map_view.refresh()
        if self.location.has_permission:
            self.location.on_change = self.update_pos
            self.location.start_tracking()

    async def update_pos(self, *args, **kwargs):
            self.location.stop_tracking()
            print("position mis à jour")
            location = kwargs.get("location", None)
            altitude = kwargs.get("altitude", None)
            self.position_pin.location = location
            if not self.position_pin in self.map_view.pins:
                print("Pins mis à jour")
                self.map_view.pins.add(self.position_pin)
                if self.location_state == False:
                    await asyncio.sleep(2)
            for i in range(len(self.balises)):
                self.map_view.pins.add(MapPin(location=self.balises[i][0], title="Balises n°"+str(i+1), subtitle=self.balises[i][1]))
            self.last_update = time.time()
            self.map_view.refresh()
            self.location.start_tracking()

    async def check_pos(self):
        while True:
            if time.time() - self.last_update >= 30:
                if self.location_state: #devient obsolète
                    self.clear()
                    self.reset_map_view()
                    self.location.stop_tracking()
                    error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
                    loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
                    self.init_act()
                    self.main_box.add(error_text, loading, self.map_view, self.act_box)
                    self.location_state = False
                    self.location.start_tracking()
            else:
                if not(self.location_state):
                    self.clear()
                    self.reset_map_view()
                    self.init_act()
                    self.main_box.add(self.map_view, self.act_box)
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
        self.init_act()
        self.map_view.pins.add(self.position_pin)
        self.main_box.add(self.map_view, self.act_box)
        self.last_update = time.time()
        self.location_state = True
        await self.main()

    def add_balise(self, widgets):
        def update_pin(widgets):
            self.balise_location_pin.subtitle = self.tag_name.value

        self.clear()
        self.location.stop_tracking()
        self.localisation = self.map_view.location
        self.zoom = self.map_view.zoom + 1 if self.map_view != 20 else 20
        self.add_balise_subbox = Box(style=Pack(direction=COLUMN, flex=1))
        add_title = Label("Ajouter une\nbalise", style=Pack(font_size=24, flex=1, text_align=CENTER))
        location_box = Box(style=Pack(direction=ROW, align_items="center", alignment="center", flex=1, text_align=CENTER))
        location_label = Label("Coordonnées de la nouvelle balise:", style=Pack(font_size=12, flex=1))
        location_entry = TextInput(value=str(self.localisation), readonly=True, style=Pack(font_size=12, flex=1))
        location_box.add(location_label, location_entry)
        tag_box = Box(style=Pack(direction=COLUMN, align_items="center", alignment="center", flex=1))
        tag_label = Label("Nom de la balise", style=Pack(font_size=16, text_align=CENTER))
        self.tag_name = TextInput(placeholder="Entrer un nom de balise (optionel)", style=Pack(font_size=12, text_align=CENTER))
        tag_box.add(tag_label, self.tag_name)
        next_button = Button("Suivant", style=Pack(flex=1, margin=(5, 0)), on_press=self.save_balise)
        self.add_balise_subbox.add(add_title, location_box, tag_box, next_button)
        balise_location_map = MapView(location=self.localisation, zoom=self.zoom, on_select=update_pin, style=Pack(margin=(20),flex=1))
        self.balise_location_pin = MapPin(location=self.localisation, title="Position de la future balise")
        balise_location_map.pins.add(self.balise_location_pin)
        self.main_box.add(self.add_balise_subbox, balise_location_map)

    async def save_balise(self, widgets):
        requests = await self.main_window.dialog(QuestionDialog("Ajouter cette balise", "Voulez-vous ajouter cette balise à cette emplacement"))
        if requests:
            self.balises.append([self.balise_location_pin.location, self.tag_name.value])
        self.location_state = False
        self.last_update = self.last_update - 40
        self.clear()
        self.reset_map_view()
        error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
        loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
        self.init_act()
        self.main_box.add(error_text, loading, self.map_view, self.act_box)
        await self.main(False)

    def init_act(self):
        self.act_box = Box(style=Pack(direction=COLUMN, height=100))
        self.balise_box = Box(style=Pack(direction=ROW, flex=1))
        self.add_balise_button = Button(text="+", style=Pack(flex=1), on_press=self.add_balise)
        self.edit_balise_button = Button(text="crayon", style=Pack(flex=1))
        self.running_box = Box(style=Pack(direction=ROW, flex=1))
        self.load_button = Button(text="load", style=Pack(flex=1))
        self.run_button = Button(text="run", style=Pack(flex=2))
        self.save_button = Button(text="save", style=Pack(flex=1))
        self.balise_box.add(self.add_balise_button, self.edit_balise_button)
        self.running_box.add(self.load_button, self.run_button, self.save_button)
        self.act_box.add(self.balise_box, self.running_box)

def main():
    return Globalorientation()
