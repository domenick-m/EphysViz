import os
import sys
import tkinter as tk
import configparser
import dearpygui.dearpygui as dpg
from scipy.signal import bessel, sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk
from matplotlib.colors import rgb_to_hsv, hsv_to_rgb
from globals import *

def create_filters():
    # create filters
    data_set('filter', build_filter(
        cfg_get('filter_type'), 
        cfg_get('band_type'),
        cfg_get('filter_order'), 
        cfg_get('filter_range'), 
        cfg_get('sample_rate')
    ))
    b, a = iirnotch(60, 30, fs=30000)
    sos = zpk2sos(*tf2zpk(b, a))
    data_set('notch_sos', sos )

def align_channel_labels(channel_type):
    # ONLY CALL THIS IF YOU HAVE ANALOG DATA
    prefix = 'a_' if channel_type == 'analog' else ''
    for chan in range(cfg_get(f'max_{channel_type}_channels')):
        if data_get('chan_info')[chan]['plot']:
            dpg.show_item(f'{prefix}ch{chan}')
            x_pos, y_pos = dpg.get_item_pos(f'{prefix}plot{chan}')
            plot_height = cfg_get(f'{channel_type}_plot_heights')
            dpg.set_item_pos(
                f'{prefix}ch{chan}', 
                [x_pos - 60, y_pos + plot_height / 2 - 14]
            )
        else:
            dpg.hide_item(f'{prefix}ch{chan}')

def color_channels():
    # should color the channel labels and plots based on number of plots shown
    pass

def plot_data(plot_range):
    for chan in range(cfg_get(f'max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            dpg.set_value(
                f'{cfg["waveform_type"].lower()}_data_{chan}',
                [
                    list(range(*plot_range)),
                    list(data[f'{cfg["waveform_type"].lower()}_data'][
                        chan, plot_range[0]:plot_range[1]
                    ])
                ]
            )
            dpg.configure_item(f'yaxis_tag{chan}', lock_min=False, lock_max=False)
            dpg.fit_axis_data(f'yaxis_tag{chan}')
            dpg.configure_item(f'yaxis_tag{chan}', lock_min=True, lock_max=True)

    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            dpg.set_value(
                f'analog_data_{chan}',
                [
                    list(range(*plot_range)),
                    list(data['analog_data'][
                        chan, plot_range[0]:plot_range[1]
                    ])
                ]
            )
            dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=False, lock_max=False)
            dpg.fit_axis_data(f'a_yaxis_tag{chan}')
            dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=True, lock_max=True)


def buffer_handler(new_limits):
    # compares the visible limits to the new_limits (from zooming or dragging)
    # checks if new limits go beyond the buffer, redraws buffer if so
    # DOES NOT SET NEW LIMITS?
    # handle out of bounds for dragging / zoom?

    visible_range = cfg_get('visible_range')

    # BUFFER LOGIC:
    # buffer = 50% of visible range is added to each side of the visible range
    # meaning that it it not visible, but is loaded in memory in case of a drag
    # or zoom that would reveal it
    # when a new zoom/pan is performed, if the new limits are outside of the 
    # first 25% of the buffer, max/min visible +/- (buffer * 0.25)), then redraw
    # the buffer with the new limits
    
    # get the buffer and view limits
    buffer = int((visible_range[1] - visible_range[0]) * cfg_get('buffer_mult'))
    view_limit = buffer * 0.5

    # if the new limits are outside of the first 25% of the buffer, redraw
    if (
        new_limits[0] < visible_range[0] - view_limit or \
        new_limits[1] > visible_range[1] + view_limit
    ):
        plot_range = (
            int(max(new_limits[0] - buffer, 0)), 
            int(min(new_limits[1] + buffer, data_get('n_samples')))
        )
        cfg_set('visible_range', new_limits)
        plot_data(plot_range)

def align_axes(sender, new_limits):
    visible_range = cfg_get('visible_range')
    if visible_range == new_limits: return
    buffer_handler(new_limits)

    if sender == 'amplif_plots_group':
        # align analog plots, time axis, and time controls
        if data_get('analog_data') is not None:
            for i in range(cfg_get('max_analog_channels')):
                dpg.set_axis_limits(f'a_xaxis_tag{i}', *new_limits)
        dpg.set_axis_limits(
            'xaxis_label_tag', *[int(i / 30) for i in new_limits]
        )
        start_time = new_limits[0] / cfg_get('sample_rate')
        full_time = data_get('n_samples') / cfg_get('sample_rate')
        _, full_m, full_s = sec_to_hms(full_time)
        _, start_m, start_s = sec_to_hms(start_time)

        dpg.set_value(
            'time_text', 
            f'{start_m:02d}:{start_s:02d} / {full_m:02d}:{full_s:02d}'
        )
        dpg.set_value('time_slider', start_time)

    elif sender == 'analog_plots_group':
        # align amplif plots, time axis, and time controls
        print('analog plots group')

    elif sender == 'time_slider':
        # align amplif plots and analog plots, and time axis
        print('time slider')

    else: # align all (skip time & play)
        # align amplif plots and analog plots, and time axis and time controls
        print(sender)


# def plot_chan_spk_panel(cfg, data):

# Function to adjust the brightness and saturation of colors
def adjust_color_brightness_saturation(rgb_colors, brightness_factor, saturation_factor):
    # Convert RGB colors to HSV
    hsv_colors = rgb_to_hsv(rgb_colors)
    
    # Adjust brightness (value) and saturation
    hsv_colors[:, 1] *= saturation_factor
    hsv_colors[:, 2] *= brightness_factor
    
    # Make sure no value exceeds 1.0
    hsv_colors[hsv_colors > 1.0] = 1.0
    
    # Convert back to RGB
    adjusted_rgb_colors = hsv_to_rgb(hsv_colors)
    
    # Normalize the adjusted colors to the range of 0 to 255 for display
    adjusted_rgb_colors_scaled = [(int(r*255), int(g*255), int(b*255), 255) for r, g, b in adjusted_rgb_colors]
    
    return adjusted_rgb_colors_scaled

def prepare_plots():
    # get the channels to plot
    colors = cfg_get('colors')
    chans_to_plot = []
    ratios = []
    for chan in range(cfg_get('max_amplif_channels')):
        c_info = data_get('chan_info')[chan]
        if c_info['plot'] and c_info['incl']:
            chans_to_plot.append(chan)
            # show the correct line series
            dpg.configure_item(
                f'{cfg["waveform_type"].lower()}_data_{chan}', 
                show=True
            )
            ratios.extend([1, int(cfg_get('show_spikes'))])
        else:
            # dpg.configure_item(f'plot{chan}', show=False)
            ratios.extend([0, 0])
            
    n_ch_to_plot = len(chans_to_plot)
    # resize the amplif plots to match the new number of channels
    min_height = int(cfg_get('amplif_plots_height') / n_ch_to_plot)
    cfg_set('amplif_plot_heights', max(cfg_get('amplif_plot_heights'), min_height))
    dpg.configure_item(
        'amplif_plots', 
        height=cfg_get('amplif_plot_heights') * n_ch_to_plot,
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
            cfg_get('visible_range')[0],
            cfg_get('visible_range')[1]
        )
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            color = f'color_{chan % len(colors)}'
            # set to the correct color
            dpg.bind_item_theme(f'analog_data_{chan}', color)
            dpg.bind_item_theme(f'a_ch{chan}', color)
            # set axis limits
            dpg.set_axis_limits(
                f'a_xaxis_tag{chan}', 
                cfg_get('visible_range')[0],
                cfg_get('visible_range')[1]
            )
    else:
        cfg_set('amplif_plots_height', cfg_get('amplif_plots_height') * 1 / 0.9)
        dpg.configure_item(
            'amplif_plots_child',
            height=cfg_get('amplif_plots_height')
        )
        dpg.configure_item(
            'amplif_plots',
            height=cfg_get('amplif_plots_height')
        )
        dpg.hide_item('analog_plots_child')
        # amplif_plots_child

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
    # return screen_height - 200, int(screen_width) - 700

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



