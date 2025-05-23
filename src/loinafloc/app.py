"""
Cette application vous permet de créer vos courses d'orientations sur une carte du monde
"""

import toga, sys, asyncio, time, json
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
from toga.widgets.table import Table
from toga.app import App
from toga.widgets.mapview import *
from toga.dialogs import InfoDialog, ErrorDialog, QuestionDialog
from toga.platform import current_platform
from toga.widgets.optioncontainer import OptionContainer
from android.content import Intent
from java import jarray, jbyte
from android.net import Uri
from java.io import OutputStream
from java.nio.charset import StandardCharsets

class Globalorientation(App):

    async def android_write(self, data_to_save: bytes, suggested_filename="Balises.json"):
        file_create = Intent(Intent.ACTION_CREATE_DOCUMENT)
        file_create.addCategory(Intent.CATEGORY_OPENABLE)
        file_create.setType("*/*")
        file_create.putExtra(Intent.EXTRA_TITLE, suggested_filename)

        # Affiche la boîte de dialogue de sélection
        result = await self._impl.intent_result(Intent.createChooser(file_create, "Exporter mes balises"))

        uri = result['resultData'].getData()
        context = self._impl.native
        stream = context.getContentResolver().openOutputStream(uri)

        # Écrit les données dans le flux
        stream.write(data_to_save)
        stream.flush()
        stream.close()

    async def android_read(self, widget=None) -> bytes:
        fileChose = Intent(Intent.ACTION_GET_CONTENT)
        fileChose.addCategory(Intent.CATEGORY_OPENABLE)
        fileChose.setType("*/*")

        # Assuming `app` is your toga.App object
        results = await self._impl.intent_result(Intent.createChooser(fileChose, "Sélectionner un questionnaire"))  
        data = results['resultData'].getData()
        context = self._impl.native
        stream = context.getContentResolver().openInputStream(data)

        def read_stream(stream):
            block = jarray(jbyte)(1024 * 1024)
            blocks = []
            while True:
                bytes_read = stream.read(block)
                if bytes_read == -1:
                    return b"".join(blocks)
                else:
                    blocks.append(bytes(block)[:bytes_read])
        return read_stream(stream)

    def clear(self):
        self.main_box = Box(style=Pack(direction=COLUMN))
        self.main_window.content = self.main_box

    def reset_map_view(self, show_pins=True):
        location = self.map_view.location
        zoom = self.map_view.zoom
        self.map_view = MapView(location=location, zoom=zoom, style=Pack(flex=1))
        self.map_view.pins.add(self.position_pin)
        if show_pins:
            for i in range(len(self.balises)):
                self.map_view.pins.add(MapPin(location=self.balises[i][0], title="Balise n°"+str(i+1), subtitle=self.balises[i][1]))

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
        self.on_focus = False
        self.main_box.add(start_text, progressbar)
        self.loc_found = False
        self.location.on_change = self.init_loc
        self.location.start_tracking()
        self.start_time = time.time() + 1
        self.balises = []
        self.move_state = False
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

    async def save_balises(self, widgets):
        try:
            to_write = json.dumps(self.balises, indent=4).encode("utf-8")
            await self.android_write(to_write)
        except Exception as E:
            await self.main_window.dialog(ErrorDialog("Erreur lors de l'export", "Impossible d'exporter le fichier pour la raison:\n"+str(E)))
        else:
            await self.main_window.dialog(InfoDialog("Balises exportés", "Vos balises ont été exportés"))

    async def load_balises(self, widgets):
        try:
            file = await self.android_read()
            self.balises = json.loads(file.decode("utf-8"))
        except Exception as E:
            await self.main_window.dialog(ErrorDialog("Impossible d'ouvrir ce fichier", "Vos balises n'ont pu être importés pour la raison:\n"+str(E)))
        else:
            try:
                self.location_state = False
                self.move_state = False
                self.last_update = self.last_update - 40
                self.clear()
                self.reset_map_view()
                error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
                loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
                self.init_act()
                self.main_box.add(error_text, loading, self.map_view, self.act_box)

                #on détermine une localisation d'apparition
                x = 0
                y = 0
                for x_bal in self.balises:
                    x += x_bal[0][0]
                for y_bal in self.balises:
                    y += y_bal[0][1]

                y /= len(self.balises)
                x /= len(self.balises)

                self.map_view.location = [x, y]
                self.map_view.zoom = 14

                await self.main()
            except Exception as E:
                await self.main_window.dialog(ErrorDialog("Impossible d'importer les balises", "Vos balises n'ont pu être importés pour la raison:\n"+str(E)))
                self.balises = []
                self.location_state = False
                self.move_state = False
                self.last_update = self.last_update - 40
                self.clear()
                self.reset_map_view()
                error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
                loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
                self.init_act()
                self.main_box.add(error_text, loading, self.map_view, self.act_box)
                await self.main()

    async def main(self, start=True):
        print("Initialisation check_pos")
        self.check_pos_task = asyncio.create_task(self.check_pos())
        print("main démarré")
        self.map_view.refresh()
        if self.location.has_permission:
            self.location.on_change = self.update_pos
            self.location.start_tracking()

    async def run(self, widgets):
        self.location.stop_tracking()
        if len(self.balises) == 0:
            await self.main_window.dialog(InfoDialog("Course incomplète", "Vous devez ajouter au moins une balise à votre course d'orientation"))
            return
        response = await self.main_window.dialog(QuestionDialog("Prêt?", "Voulez-vous commencer la course d'orientation dés maintenant?"))
        if not(response):
            return
        self.allow_position = await self.main_window.dialog(QuestionDialog("Afficher localisation", "Souhaitez-vous autoriser l'affichage de votre position durant la course? Si oui, vous pourrez l'afficher/masquer à n'importe quel moment de la course"))
        self.main_box.clear()
        self.reset_map_view(show_pins=False)

        self.main_container = OptionContainer()
        self.location_box = Box(style=Pack(direction=COLUMN))
        progressbar_header = Box(style=Pack(direction=COLUMN, align_items=CENTER, text_align=CENTER))
        progress_label = Label(style=Pack(font_size=10), text="Balise 0 sur "+str(len(self.balises)))
        self.progressbar_status = ProgressBar(max=len(self.balises), value=0, style=Pack(margin=(0)))
        progressbar_header.add(progress_label, self.progressbar_status)
        self.main_box.add(progressbar_header, self.main_container)
        

    async def update_pos(self, *args, **kwargs):
            self.location.stop_tracking()
            print("position mis à jour")
            location = kwargs.get("location", None)
            altitude = kwargs.get("altitude", None)
            self.position_pin.location = location
            if self.on_focus: self.map_view.location = location
            if not self.position_pin in self.map_view.pins:
                print("Pins mis à jour")
                self.map_view.pins.add(self.position_pin)
                if self.location_state == False:
                    await asyncio.sleep(2)
            for i in range(len(self.balises)):
                self.map_view.pins.add(MapPin(location=self.balises[i][0], title="Balise n°"+str(i+1), subtitle=self.balises[i][1]))
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

    async def add_balise(self, widgets): 
        def update_pin(widgets):
            self.balise_location_pin.subtitle = self.tag_name.value

        if len(self.balises) >= 1000:
            await self.main_window.dialog(ErrorDialog("Limite du nombre de balises atteintes", "Votre course contient trop de balises! Veuillez en supprimer puis réessayer!"))
            return

        self.clear()
        self.location.stop_tracking()
        self.check_pos_task.cancel()
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

    def edit_balises(self, widgtets):
        self.clear()
        self.location.stop_tracking()
        self.check_pos_task.cancel()
        table_list = []
        self.selected_balise = None
        for x in self.balises:
            table_list.append([x[1], str(x[0])])
        print(table_list)
        self.balise_table = Table(["Nom de la balise", "Coordonnées"], data=table_list, style=Pack(flex=1), on_select=self.move_on_select)
        self.edit_box = Box(style=Pack(direction=COLUMN, height=100))
        self.manage_box = Box(style=Pack(direction=ROW, flex=1))
        self.rename_button = Button("edit", style=Pack(flex=2), on_press=self.rename_balise)
        self.del_button = Button("del", style=Pack(flex=1, background_color="#ff0000", color="#000000"), on_press=self.del_balise)
        self.move_button = Button("move", style=Pack(flex=2), on_press=self.move_balise)
        self.quit_button = Button("Confirmer", style=Pack(flex=1), on_press=self.quit_editing)
        self.manage_box.add(self.rename_button, self.del_button, self.move_button)
        self.edit_box.add(self.manage_box, self.quit_button)
        self.main_box.add(self.balise_table, self.edit_box)

    def move_balise(self, widgets:Button):
        if self.move_state:
            # self.move_state = False
            # selected_balise = self.balise_table.selection
            # del widgets.style.background_color
            # for i in range(len(self.balises)):
            #     if (str(self.balises[i][0]) == selected_balise.coordonnées and self.balises[i][1] == selected_balise.nom_de_la_balise):
            #         self.balises[i], self.balises[self.selected_balise] = self.balises[self.selected_balise], self.balises[i]
            # self.edit_balises(widgtets=None)
            pass

        else: #Aucune balise n'est seléctionné pour le moment
            self.selected_balise = self.balise_table.selection
            if self.selected_balise == None:
                return
            self.move_state = True
            for i in range(len(self.balises)):
                if (str(self.balises[i][0]) == self.selected_balise.coordonnées and self.balises[i][1] == self.selected_balise.nom_de_la_balise):
                    self.selected_balise = i
            print(self.selected_balise)
            widgets.style.update(background_color="#00ff00")

    def move_on_select(self, widgets):
        if self.move_state:
            self.move_state = False
            selected_balise = self.balise_table.selection
            del widgets.style.background_color
            for i in range(len(self.balises)):
                if (str(self.balises[i][0]) == selected_balise.coordonnées and self.balises[i][1] == selected_balise.nom_de_la_balise):
                    self.balises[i], self.balises[self.selected_balise] = self.balises[self.selected_balise], self.balises[i]
            self.edit_balises(widgtets=None)

    async def del_balise(self, widgets):
        question = await self.main_window.dialog(QuestionDialog("Supprimer la balise", "Voulez vous supprimer la balise seléctionnée?"))
        if question:
            self.move_state = False
            self.selected_balise = self.balise_table.selection
            for i in range(len(self.balises)):
                if (str(self.balises[i][0]) == self.selected_balise.coordonnées and self.balises[i][1] == self.selected_balise.nom_de_la_balise):
                    del self.balises[i]
            self.location_state = False
            self.last_update = self.last_update - 40
            self.clear()
            self.reset_map_view()
            error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
            loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
            self.init_act()
            self.main_box.add(error_text, loading, self.map_view, self.act_box)
            await self.main()

    def rename_balise(self, widgets):
        self.selected_balise = self.balise_table.selection
        self.move_state = False
        if self.selected_balise == None:
            return
        self.clear()
        title_rename = Label("Renommer la\nbalise", style=Pack(text_align=CENTER, alignment=CENTER, font_size=26, margin=(20, 0)))
        self.name_entry = TextInput(style=Pack(margin=(10, 30)), placeholder="Nouveau nom de balise", value=self.selected_balise.nom_de_la_balise)
        rename_button = Button("Renommer", style=Pack(margin=(0)), on_press=self.save_new_name)
        self.main_box.add(title_rename, self.name_entry, rename_button)
        self.name_entry.focus()

    async def save_new_name(self, widgets):
        #Il faut retrouver l'élément...
        for balise in self.balises:
            if (str(balise[0]) == self.selected_balise.coordonnées and balise[1] == self.selected_balise.nom_de_la_balise):
                balise[1] = self.name_entry.value
        self.location_state = False
        self.last_update = self.last_update - 40
        self.clear()
        self.reset_map_view()
        error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
        loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
        self.init_act()
        self.main_box.add(error_text, loading, self.map_view, self.act_box)
        await self.main()

    async def quit_editing(self, widgets):
        self.location_state = False
        self.move_state = False
        self.last_update = self.last_update - 40
        self.clear()
        self.reset_map_view()
        error_text = Label(text="Aucun signal GPS", style=Pack(font_size=10, color="#ffffff", text_align="center", background_color="#ff0000"))
        loading = ProgressBar(style=Pack(flex=1), max=None, running=True)
        self.init_act()
        self.main_box.add(error_text, loading, self.map_view, self.act_box)
        await self.main()

    def update_selected_balise(self, widgets):
        self.selected_balise

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
        await self.main()

    def update_focus(self, widgets:Button):
        if self.on_focus:
            self.on_focus = False
            del widgets.style.background_color
        else:
            self.on_focus = True
            widgets.style.update(background_color="#00ff00")
            self.map_view.zoom = 18
            self.map_view.location = self.position_pin.location

    def init_act(self):
        self.act_box = Box(style=Pack(direction=COLUMN, height=100))
        self.balise_box = Box(style=Pack(direction=ROW, flex=1))
        self.add_balise_button = Button(text="+", style=Pack(flex=2), on_press=self.add_balise)
        self.center_button = Button(text="c", style=Pack(flex=1), on_press=self.update_focus)
        if self.on_focus: self.center_button.style.update(background_color="#00ff00")
        else: del self.center_button.style.background_color
        self.edit_balise_button = Button(text="crayon", style=Pack(flex=2), on_press=self.edit_balises)
        self.running_box = Box(style=Pack(direction=ROW, flex=1))
        self.load_button = Button(text="load", style=Pack(flex=1), on_press=self.load_balises)
        self.run_button = Button(text="run", style=Pack(flex=2))
        self.save_button = Button(text="save", style=Pack(flex=1), on_press=self.save_balises)
        self.balise_box.add(self.add_balise_button, self.center_button, self.edit_balise_button)
        self.running_box.add(self.load_button, self.run_button, self.save_button)
        self.act_box.add(self.balise_box, self.running_box)

def main():
    return Globalorientation()
