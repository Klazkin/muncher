import json
import os
import subprocess
import sys
import threading
import time

import gi
import minecraft_launcher_lib as mc
from dotenv import load_dotenv
from gi.repository import Adw, Gio, Gtk, WebKit
from minecraft_launcher_lib.types import CallbackDict, MinecraftOptions

from user_data import UserData, save, user_data

APP_ID = "github.klazkin.muncher"

### PRECOMPILE BLUEPRINT

blueprints = ["main", "login", "main_v2"]

for b in blueprints:
    print(f"compiling: {b}")
    os.system(f"rm {b}.ui")
    os.system(f"blueprint-compiler compile {b}.blp >> {b}.ui")

### SETUP DOTENV

assert load_dotenv()

CLIENT_ID = os.environ["CLIENT_ID"]
REDIRECT_HOST = os.environ["REDIRECT_HOST"]
REDIRECT_PORT = int(os.environ["REDIRECT_PORT"])
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}"

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


### APPLICATION


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id=APP_ID,
            **kwargs,
        )

    def do_activate(self):
        self.window: Adw.ApplicationWindow = (
            MuncherWindow(application=self)
            if user_data  # this is a crime, ideally should check againts MS api if token is valid?
            else LoginWindow(application=self)
        )

        self.window.present()


@Gtk.Template(filename="main_v2.ui")
class MainV2(Adw.ApplicationWindow):
    __gtype_name__ = "MainV2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


@Gtk.Template(filename="login.ui")
class LoginWindow(Adw.ApplicationWindow):
    __gtype_name__ = "LoginWindow"

    web_view: WebKit.WebView = Gtk.Template.Child()
    browser_link: Gtk.LinkButton = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app: Application = kwargs["application"]

        login_url = mc.microsoft_account.get_login_url(CLIENT_ID, REDIRECT_URI)
        self.web_view.load_uri(login_url)
        self.browser_link.set_uri(login_url)

        thread = threading.Thread(
            target=self.listen_to_auth,
            daemon=True,
        )
        thread.start()

    def listen_to_auth(self):
        import flask

        app = flask.Flask(__name__)

        @app.route("/", methods=["GET"])
        def webhook():
            code = flask.request.args["code"]

            if not code:
                return "Error! Something went wrong, code missing from redirect."

            self.on_login_accepted(code)
            return "Auth completed! You may return to the launcher."  # TODO really fancy page that says the exact same thing

        app.run(host=REDIRECT_HOST, port=REDIRECT_PORT)

    def on_login_accepted(self, auth_code: str):
        try:
            login_result = mc.microsoft_account.complete_login(
                CLIENT_ID, None, REDIRECT_URI, str(auth_code), None
            )
            print("logged in")
            login_data: UserData = {
                "username": login_result["name"],
                "token": login_result["access_token"],
                "uuid": login_result["id"],
                "data_version": 1,
            }
            save(login_data)

        except Exception as e:
            print("Login failed:", e)
            raise RuntimeError("Login failure.")

        ## todo fix this jank
        self.app.window = MuncherWindow(application=self.app)
        self.app.window.present()
        self.close()


@Gtk.Template(filename="main.ui")
class MuncherWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MuncherWindow"

    button_play: Adw.SplitButton = Gtk.Template.Child()
    button_play_content: Adw.SplitButton = Gtk.Template.Child()
    button_play_spinner: Adw.Spinner = Gtk.Template.Child()
    version_popover: Gtk.Popover = Gtk.Template.Child()
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

        self.version_popover.set_visible(False)
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
            self.install_progress_bar.set_text(
                f"{status.split(' ')[0]}..."
            )  # FIXME hack

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

        # FIXME create separate debug mode
        # options = mc.utils.generate_test_options()

        if user_data is None:
            raise RuntimeError("UserData cannot be null")

        options: MinecraftOptions = {
            "launcherName": "muncher",
            "username": user_data["username"],
            "uuid": user_data["uuid"],
            "token": user_data["token"],
        }

        minecraft_command = mc.command.get_minecraft_command(
            self.selected_version, self.minecraft_directory, options
        )

        subprocess.Popen(minecraft_command, start_new_session=True)
        time.sleep(3)
        self.app.quit()


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
