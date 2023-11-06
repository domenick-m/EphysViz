import os
import sys
import tkinter as tk
import configparser
import dearpygui.dearpygui as dpg
from scipy.signal import bessel, sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk

def prepare_plots(cfg, data, colors):
    # get the channels to plot
    chans_to_plot = []
    ratios = []
    for chan in range(cfg['max_amplif_channels']):
        c_info = data['chan_info'][chan]
        if c_info['plot'] and c_info['incl']:
            chans_to_plot.append(chan)
            # show the correct line series
            dpg.configure_item(
                f'{cfg["waveform_type"].lower()}_data_{chan}', 
                show=True
            )
            ratios.extend([1, int(cfg['show_spikes'])])
        else:
            # dpg.configure_item(f'plot{chan}', show=False)
            ratios.extend([0, 0])
            
    n_ch_to_plot = len(chans_to_plot)
    # resize the amplif plots to match the new number of channels
    min_height = int(cfg['amplif_plots_height'] / n_ch_to_plot)
    cfg['amplif_plot_heights'] = max(cfg['amplif_plot_heights'], min_height)
    dpg.configure_item(
        'amplif_plots', 
        height=cfg['amplif_plot_heights'] * n_ch_to_plot,
        row_ratios=ratios
    )
    for idx, chan in enumerate(chans_to_plot):
        color = f'color_{idx % len(colors)}'
        tag = f'{cfg["waveform_type"].lower()}_data_{chan}'
        # set to the correct color
        dpg.bind_item_theme(tag, color)
        dpg.bind_item_theme(f'ch{chan}', color)
        # set axis limits
        dpg.set_axis_limits(
            f'xaxis_tag{chan}', 
            cfg['visible_range'][0],
            cfg['visible_range'][1]
        )
    for chan in range(cfg['max_analog_channels']):
        color = f'color_{chan % len(colors)}'
        # set to the correct color
        dpg.bind_item_theme(f'analog_data_{chan}', color)
        dpg.bind_item_theme(f'a_ch{chan}', color)
        # set axis limits
        dpg.set_axis_limits(
            f'a_xaxis_tag{chan}', 
            cfg['visible_range'][0],
            cfg['visible_range'][1]
        )
    return cfg

def build_filter(filter_type, band_type, filt_order, filt_range, fs):
    filt_range = filt_range[1] if band_type == 'Lowpass' \
                 else filt_range[0] if band_type == 'Highpass' else filt_range
    if filter_type == 'Butterworth':
        filter = butter(
            filt_order, filt_range, 
            btype=band_type, analog=False, output='sos', fs=fs
        )
    elif filter_type == 'Bessel':
        filter = bessel(
            filt_order, filt_range, 
            btype=band_type, analog=False, output='sos', fs=fs, norm='phase'
        )
    else: return None
    return filter

def filter_data(data, filter, notch_sos=None):
    data = data.T
    if notch_sos is not None:
        data = sosfiltfilt(notch_sos, data, axis=0)
    data = sosfiltfilt(filter, data, axis=0).T    
    return data 

def center_label(label, tab_width, char_width):
    """Centers a label within a given tab width by padding it with spaces."""
    label_width = len(label) * char_width
    space_count = max(0, int((tab_width - label_width) / 2 / char_width))
    return ' ' * space_count + label + ' ' * space_count

def sec_to_hms(total_secs):
    """Convert seconds to a tuple of hours, minutes, and seconds."""
    hours, remainder = divmod(int(total_secs), 3600)
    minutes, seconds = divmod(remainder, 60)
    return hours, minutes, seconds

def get_screen_size():
    """Retrieve the screens height and width in pixels."""
    # create a temporary tkinter root window
    root = tk.Tk()  
    # get screen height and width
    screen_height = root.winfo_screenheight()  
    screen_width = root.winfo_screenwidth()  
    # close the temporary window
    root.destroy() 
    return screen_height, int(screen_width)

def get_max_viewport_size():
    """Retrieve the max viewport height and width in pixels."""
    # start the render loop and get the viewport size
    if dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
        viewport_height = dpg.get_viewport_height()
        viewport_width = dpg.get_viewport_width()
        dpg.render_dearpygui_frame()
    return viewport_height, viewport_width

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)

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
    config.set(section, setting, value)
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



