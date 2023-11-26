import os
import sys
import configparser
from distutils.util import strtobool

cfg = {}
data = {'chan_info': {i: {} for i in range(32)}}

def load_defaults():
    # load default configs from settings.ini
    global cfg
    cfg['amplif_plot_heights'] = float(read_settings(
        'defaults', 'amplif_plot_heights', 35
    ))
    cfg['analog_plot_heights'] = float(read_settings(
        'defaults', 'analog_plot_heights', 35
    ))
    cfg['impedance_threshold'] = int(read_settings(
        'defaults', 'impedance_threshold', 5000
    ))
    cfg['path'] = str(read_settings('defaults', 'path', os.path.expanduser('~')))
    cfg['filter_type'] = read_settings('defaults', 'filter_type', 'Butterworth')
    cfg['band_type'] = read_settings('defaults', 'band_type', 'Bandpass')
    cfg['filter_order'] = int(read_settings('defaults', 'filter_order', 4))
    filt_range = read_settings('defaults', 'filter_range', "(250, 5000)")
    filt_range = filt_range.replace('(', '').replace(')', '').split(',')
    cfg['filter_range'] = (int(filt_range[0]), int(filt_range[1]))
    cfg['notch_filter'] = bool(strtobool(read_settings('defaults', 'notch_filter', 'True')))
    cfg['show_spikes'] = bool(strtobool(read_settings('defaults', 'show_spikes', 'False')))
    cfg['play_speed'] = read_settings('defaults', 'play_speed', '0.5x')
    cfg['spike_chan'] = int(read_settings('defaults', 'spike_chan', 0))
    cfg['threshold_mult'] = float(read_settings('defaults', 'threshold_mult', 4.5))
    cfg['waveform_type'] = read_settings('defaults', 'waveform_type', 'Filtered')
    
def cfg_get(key):
    global cfg
    return cfg[key]

def cfg_set(key, value):
    global cfg
    cfg[key] = value

def data_get(key):
    global data
    return data[key]

def data_set(key, value):
    global data
    data[key] = value

def set_ch_info(ch, key, value):
    global data
    data['chan_info'][ch][key] = value

def save_settings():
    for setting in [
        'amplif_plot_heights',
        'analog_plot_heights',
        'impedance_threshold',
        'path',
        'filter_type',
        'band_type',
        'filter_order',
        'filter_range',
        'notch_filter',
        'show_spikes',
        'play_speed',
        'spike_chan',
        'threshold_mult',
        'waveform_type',
    ]:
        write_settings('defaults', setting, cfg[setting])

def get_settings_path(app_name='EphysViz', filename='settings.ini'):
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

def write_settings(section, setting, value, filename='settings.ini'):
    """Write a setting value to a configuration file."""
    config = configparser.ConfigParser()
    settings_path = get_settings_path()
    if os.path.exists(settings_path):
        config.read(settings_path)
    if section not in config.sections():
        config.add_section(section)
    config.set(section, setting, str(value))
    with open(settings_path, 'w') as configfile:
        config.write(configfile)

def read_settings(section, setting, default=None, filename="settings.ini"):
    """Read a setting value from a configuration file, returning default if not 
    found."""
    config = configparser.ConfigParser()
    settings_path = get_settings_path()
    config.read(settings_path)
    return config.get(section, setting) if config.has_option(section, setting) \
           else default
