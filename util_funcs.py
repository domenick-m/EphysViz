import os
import sys
import tkinter as tk
import configparser


def sec_to_hms(total_secs):
    """Convert seconds to a tuple of hours, minutes, and seconds."""
    hours, remainder = divmod(int(total_secs), 3600)
    minutes, seconds = divmod(remainder, 60)
    return hours, minutes, seconds

def get_screen_size():
    """Retrieve the screen height and width in pixels."""
    # create a temporary tkinter root window
    root = tk.Tk()  
    # get screen height and width
    screen_height = root.winfo_screenheight()  
    screen_width = root.winfo_screenwidth()  
    # close the temporary window
    root.destroy()  
    return screen_height, screen_width

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_settings_path(app_name, filename="settings.ini"):
    """Return the path to the settings file for a given app."""
    if sys.platform.startswith('win'): # windows
        settings_dir = os.path.join(os.environ['APPDATA'], app_name)
    elif sys.platform.startswith('darwin'): # mac
        settings_dir = os.path.join(
            os.path.expanduser('~/Library/Application Support/'), app_name)
    else:  # linux and other platforms
        settings_dir = os.path.join(os.path.expanduser('~'), f'.{app_name}')
    # create the settings directory if it doesn't exist
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)
    return os.path.join(settings_dir, filename)

def write_settings(section, setting, value, filename="settings.ini"):
    """Write a setting value to a configuration file."""
    config = configparser.ConfigParser()
    settings_path = get_settings_path(filename)
    if os.path.exists(settings_path):
        config.read(settings_path)
    if section not in config.sections():
        config.add_section(section)
    config.set(section, setting, value)
    with open(settings_path, 'w') as configfile:
        config.write(configfile)

def read_settings(section, setting, default=None, filename="settings.ini"):
    """Read a setting value from a configuration file, returning default if not 
    found."""
    config = configparser.ConfigParser()
    settings_path = get_settings_path(filename)
    config.read(settings_path)
    return config.get(section, setting) if config.has_option(section, setting) \
           else default

