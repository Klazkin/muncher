import re
import subprocess
import sys
from operator import sub
from os import environ
from syslog import LOG_DAEMON

import gi
from dotenv import load_dotenv

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk


class Application(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="org.example.App",
            **kwargs,
        )

    def do_activate(self):
        self.window: Adw.ApplicationWindow = SampleWindow(application=self)
        self.window.present()


@Gtk.Template(filename="main.ui")
class SampleWindow(Adw.ApplicationWindow):
    __gtype_name__ = "SampleWindow"

    label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def login():
    client_id = environ["CLIENT_ID"]
    redirect_uri = environ["REDIRECT_URI"]

    login_url = mc.microsoft_account.get_login_url(client_id, redirect_uri)

    print(login_url)
    #
    redirect_url = input("redirect_url:")

    if not mc.microsoft_account.url_contains_auth_code(redirect_url):
        print("no code")
        exit(-1)

    auth_code = mc.microsoft_account.get_auth_code_from_url(redirect_url)

    print("code:", auth_code)

    login_result = mc.microsoft_account.complete_login(
        client_id, None, redirect_uri, str(auth_code), None
    )


if __name__ == "__main__":
    assert load_dotenv()

    import minecraft_launcher_lib as mc

    # Get latest version
    #
    minecraft_directory = mc.utils.get_minecraft_directory()

    latest_version = mc.utils.get_latest_version()["release"]

    print(minecraft_directory, latest_version)

    mc.install.install_minecraft_version(latest_version, minecraft_directory)

    options = mc.utils.generate_test_options()

    minecraft_command = mc.command.get_minecraft_command(
        latest_version, minecraft_directory, options
    )

    completed = subprocess.run(minecraft_command)

    print("process finished with", completed)
    # print(minecraft_command)

    # app = Application()
    # app.run(sys.argv)
