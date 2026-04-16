import sys

import gi

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


if __name__ == "__main__":
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

    print(minecraft_command)

    # app = Application()
    # app.run(sys.argv)
