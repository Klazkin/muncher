import asyncio
import os
import subprocess
import sys

import gi
import minecraft_launcher_lib as mc
from dotenv import load_dotenv
from gi.repository import Adw, Gio, GLib, Gtk

assert load_dotenv()
client_id = os.environ["CLIENT_ID"]
redirect_uri = os.environ["REDIRECT_URI"]

print("Starting compilation")

os.system("rm main.ui")
os.system("blueprint-compiler compile main.blp >> main.ui")

print("Finished compilation")

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="org.example.App",
            **kwargs,
        )

    def do_activate(self):
        self.window: Adw.ApplicationWindow = MuncherWindow(application=self)
        self.window.present()


@Gtk.Template(filename="main.ui")
class MuncherWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MuncherWindow"

    button_play = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.button_play.connect("clicked", on_play_pressed)


def on_play_pressed(_):
    minecraft_directory = mc.utils.get_minecraft_directory()
    latest_version = mc.utils.get_latest_version()["release"]

    mc.install.install_minecraft_version(latest_version, minecraft_directory)

    options = mc.utils.generate_test_options()

    minecraft_command = mc.command.get_minecraft_command(
        latest_version, minecraft_directory, options
    )

    completed = subprocess.run(minecraft_command, start_new_session=True)
    print("process finished with", completed)


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
