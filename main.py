import os
import subprocess
import sys
import threading
import time

import gi
import minecraft_launcher_lib as mc
from dotenv import load_dotenv
from gi.repository import Adw, Gio, GLib, Gtk
from minecraft_launcher_lib.types import CallbackDict

### PRECOMPILE BLUEPRINT

print("Starting compilation")

os.system("rm main.ui")
os.system("blueprint-compiler compile main.blp >> main.ui")

print("Finished compilation")

### SETUP DOTENV

assert load_dotenv()
client_id = os.environ["CLIENT_ID"]
redirect_uri = os.environ["REDIRECT_URI"]

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

### APPLICATION


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="github.klazkin.muncher",
            **kwargs,
        )

    def do_activate(self):
        self.window: Adw.ApplicationWindow = MuncherWindow(application=self)
        self.window.present()


@Gtk.Template(filename="main.ui")
class MuncherWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MuncherWindow"

    button_play: Adw.SplitButton = Gtk.Template.Child()
    button_play_content: Adw.SplitButton = Gtk.Template.Child()
    button_play_spinner: Adw.Spinner = Gtk.Template.Child()
    button_popover: Gtk.Popover = Gtk.Template.Child()
    spinner_label: Gtk.Label = Gtk.Template.Child()
    install_progress_bar: Gtk.ProgressBar = Gtk.Template.Child()
    version_list: Gtk.ListView = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app: Application = kwargs["application"]

        self.minecraft_directory = mc.utils.get_minecraft_directory()
        self.selected_version = mc.utils.get_latest_version()["release"]
        available_versions = mc.utils.get_available_versions(self.minecraft_directory)
        available_versions_flat = list(map(lambda v: v["id"], available_versions))

        self.version_list_model = Gtk.StringList.new(available_versions_flat)
        self.version_select_model = Gtk.SingleSelection(model=self.version_list_model)
        self.version_select_model.set_selected(
            available_versions_flat.index(self.selected_version)
        )

        self.version_list.set_model(self.version_select_model)
        self.version_select_model.connect(
            "selection-changed", self.on_selection_changed
        )

        self.button_play.connect("clicked", self.on_play_pressed)
        self.button_play_content.set_label(f"Play {self.selected_version}")
        self.progress_bar_max = 0

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

    def on_selection_changed(self, *_):
        selected_version = self.version_list_model.get_string(
            self.version_select_model.get_selected()
        )

        if selected_version is None:
            print(f"invalid version id {self.version_select_model.get_selected()}")
            return

        self.selected_version = selected_version
        self.button_play_content.set_label(
            f"Play {self.selected_version}"
        )  # todo use connections to keep updated?

    def on_play_pressed(self, _):
        self.button_play.set_sensitive(False)
        self.button_play_spinner.set_visible(True)
        self.button_play_content.set_visible(False)

        thread = threading.Thread(
            target=self.start_game,
            daemon=True,
        )
        thread.start()

    def on_about(self, *args):
        dialog = Adw.AboutDialog(
            application_name="Munhcer",
            developer_name="Klazkin",
            version="0.0.1",  # TODO extract from config
            comments="Minimalistic Minecraft launcher built for the GNOME ecosystem",
            license_type=Gtk.License.GPL_3_0_ONLY,
        )

        dialog.present(self)

    def start_game(self):

        self.progress_bar_max = 0  # reset

        def set_status(status: str):
            self.install_progress_bar.set_text(f"{status}...")

        def set_progress(progress: int):
            if self.progress_bar_max != 0:
                self.install_progress_bar.set_visible(True)
                self.install_progress_bar.set_fraction(progress / self.progress_bar_max)

        def set_max(new_max: int):
            self.progress_bar_max = new_max

        install_callbacks: CallbackDict = {
            "setStatus": set_status,
            "setProgress": set_progress,
            "setMax": set_max,
        }

        self.spinner_label.set_label("Downloading...")
        mc.install.install_minecraft_version(
            self.selected_version, self.minecraft_directory, install_callbacks
        )
        self.spinner_label.set_label("Launching...")
        self.install_progress_bar.set_visible(False)

        options = mc.utils.generate_test_options()

        minecraft_command = mc.command.get_minecraft_command(
            self.selected_version, self.minecraft_directory, options
        )

        subprocess.Popen(minecraft_command, start_new_session=True)
        time.sleep(3)
        self.app.quit()


def login():
    login_url = mc.microsoft_account.get_login_url(client_id, redirect_uri)
    print("go to:", login_url)
    redirect_url = input("redirect_url:")

    if not mc.microsoft_account.url_contains_auth_code(redirect_url):
        print("no code")
        exit(-1)

    auth_code = mc.microsoft_account.get_auth_code_from_url(redirect_url)

    print("code:", auth_code)

    login_result = mc.microsoft_account.complete_login(
        client_id, None, redirect_uri, str(auth_code), None
    )

    return login_result


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
