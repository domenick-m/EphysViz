import sys
import math
import timeit
import numpy as np
import tkinter as tk
import scipy.signal as signal
import dearpygui.dearpygui as dpg
from intanutil.read_data import read_data
from scipy.signal import sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk
import os


dpg.create_context()
# holding = True

# def callback(sender, app_data, user_data):
#     print("Sender: ", sender)
#     print("App Data: ", list(app_data['selections'].values())[0])
#     holding = False
#     dpg.destroy_context()

# with dpg.file_dialog(directory_selector=False, show=True, callback=callback, id="file_dialog_id", width=700 ,height=400):
#     dpg.add_file_extension(".*")
#     dpg.add_file_extension("", color=(150, 255, 150, 255))
#     dpg.add_file_extension("Source files (*.cpp *.h *.hpp){.cpp,.h,.hpp}", color=(0, 255, 255, 255))
#     dpg.add_file_extension(".h", color=(255, 0, 255, 255), custom_text="[header]")
#     dpg.add_file_extension(".py", color=(0, 255, 0, 255), custom_text="[Python]")

# def test(sender, data):
#     print(sender, data)

# # with dpg.window(label="Tutorial", width=800, height=300):
# #     dpg.add_button(label="File Selector", callback=lambda: dpg.show_item("file_dialog_id"))

# dpg.create_viewport(title='Custom Title', width=800, height=600)
# dpg.setup_dearpygui()
# dpg.show_viewport()
# dpg.start_dearpygui()
# dpg.destroy_context()

# while holding:
#     print('test')

def float_to_time(value):
    hours, remainder = divmod(int(value), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{minutes:02d}:{seconds:02d}'


# create a temporary tkinter root window
root = tk.Tk()  
# get screen width
screen_width = root.winfo_screenwidth()  
# get screen height
screen_height = root.winfo_screenheight()  
# close the temporary window
root.destroy()  

n_plots = 0
plot_heights = 0
n_samples = 0
sample_rate = 0
num_ticks = 0
paused = True
initial_notch = 0
visible_chans = []
all_chans = []
chan_info = {}
show_spikes = False



def test_func(filepath):
    global n_plots, plot_heights, loaded, n_samples, sample_rate, num_ticks, paused, initial_notch, all_chans, visible_chans, chan_info, show_spikes
    # LOAD DATA
    # TODO: convert to file selecter
    print('filepath:', filepath)
    # filepath = '/Users/domenick_mifsud/Desktop/POSITI~1.RHS'
    data = read_data(filepath)
    print(data.keys())

    # extract the channel info (impedance)
    channel_info = data['amplifier_channels']
    # extract the raw 30kHz voltage (𝛍V) data
    raw_30k_data = data['amplifier_data']

    
    impedances = [chan['electrode_impedance_magnitude'] for chan in channel_info]

    
    n_chans, n_samples = raw_30k_data.shape
    # TODO: get this from RHS file
    sample_rate = 30000  # Samples per second (30kHz)

    # --- PLOT VARS ---
    plot_heights = 100
    x_axis_height = 35
    menu_bar_height = 151
    scroll_bar_width = 20

    ax_mult = 0.20
    margin = 0.02
    num_ticks = 10
    tick_interval = 1000 

    plot_window_width = screen_width * 0.75
    tab_bar_width = screen_width - plot_window_width

    max_plots = math.floor((screen_height - x_axis_height - 200) / plot_heights)
    n_plots = int(np.min((max_plots, n_chans)))

    subplots_width = plot_window_width - scroll_bar_width - 120 # 10 is width of ch label
    subplots_height = plot_heights * n_plots

    row_ratios = [plot_heights / subplots_height for _ in range(n_plots)]
    row_ratios.append(x_axis_height / subplots_height)

    # ---- TAB10 (no grey) ----
    color_map = [
        [0.12156862745098039, 0.4666666666666667, 0.7058823529411765],
        [1.0, 0.4980392156862745, 0.054901960784313725],
        [0.17254901960784313, 0.6274509803921569, 0.17254901960784313],
        [0.8392156862745098, 0.15294117647058825, 0.1568627450980392],
        [0.5803921568627451, 0.403921568627451, 0.7411764705882353],
        [0.5490196078431373, 0.33725490196078434, 0.29411764705882354],
        [0.8901960784313725, 0.4666666666666667, 0.7607843137254902],
        [0.7372549019607844, 0.7411764705882353, 0.13333333333333333],
        [0.09019607843137255, 0.7450980392156863, 0.8117647058823529]
    ] 
    # convert to 255
    color_map = [[int(255 * val) for val in color] for color in color_map]



    # ------ DYNAMIC VARS ------
    paused = True

    start_x = 100
    end_x = 50000
    filt_order = 4
    filt_range = (250, 3000)

    rect_pos = [0, 0]

    # def_imp_threshold = 1000 # kOhms
    # def_imp_threshold = 5000 # kOhms
    def_imp_threshold = 999999 # kOhms

    for chan in range(n_chans):
        if impedances[chan] > def_imp_threshold * 1000:
            chan_info[chan] = {'plot':False, 'incl':False}
        else:
            chan_info[chan] = {'plot':True, 'incl':True}
            all_chans.append(chan)
            if len(visible_chans) < n_plots:
                visible_chans.append(chan)

    # get the index where 4 is
    def get_idx(val):
        return np.where(np.array(all_chans) == val)[0][0]
        
    def get_visible_colors(i):
        i_chan = visible_chans[i]
        return all_chans.index(i_chan) % len(color_map)

    waveform_type = 'filt'
    notch_f = 60
    b, a = iirnotch(notch_f, 30, fs=sample_rate)


    #  --- FUNCS ---
    def toggle_spikes(sender, data):
        global show_spikes
        show_spikes = data

        for i in range(n_plots):
            x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
            dpg.configure_item(f'scatter{i}', show=show_spikes)

            plot_data = data_dict[waveform_type][get_idx(visible_chans[i])]
            y_min = np.min(plot_data[int(x_min):int(x_max)])
            y_max = np.max(plot_data[int(x_min):int(x_max)])
            y_delta = (y_max - y_min) * ax_mult
            y_margin = (y_max - y_min) * margin
            edge_mult = 30 if show_spikes else 1
            dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*edge_mult, y_max+y_margin)

            x_axis, y_axis = list(range(n_samples)), crossings[get_idx(visible_chans[i])]
            x_filtered, y_filtered = zip(*[(xi, y_min-y_margin*20) for xi, yi in zip(x_axis, y_axis) if yi == 1])

            dpg.set_value(f'scatter{i}', [list(x_filtered), list(y_filtered)])
            idx = get_visible_colors(i)
            dpg.bind_item_theme(f'scatter{i}', f"plot_theme_{idx}")
            

    def filter_chans(sender, data):
        global chan_info, visible_chans, all_chans
        changed = False

        visible_chans = []
        all_chans = []

        for chan in range(n_chans):
            if impedances[chan] > data * 1000:
                if chan_info[chan]['incl']:
                    changed = True
                chan_info[chan]['incl'] = False
                chan_info[chan]['plot'] = False
                dpg.bind_item_theme(f'chan_sidebar_{chan}', f"disabled_chan")
                dpg.set_value(f'include_{chan}', False)
                dpg.set_value(f'plot_{chan}', False)
            else:
                if not chan_info[chan]['incl']:
                    changed = True
                chan_info[chan]['incl'] = True
                chan_info[chan]['plot'] = True
                dpg.set_value(f'include_{chan}', True)
                dpg.set_value(f'plot_{chan}', True)
                dpg.bind_item_theme(f'chan_sidebar_{chan}', f"enabled_chan")
                all_chans.append(chan)
                if len(visible_chans) < n_plots:
                    visible_chans.append(chan)
        if changed:
            data_dict['car'] = rereference_data(data_dict['raw'], 'CAR')
            data_dict['filt'] = filter_data(data_dict['car'], filt_order, filt_range)
            update_plots()
            for i in range(n_plots):
                chan = visible_chans[i]
                dpg.set_value(f'ch{i}', f"Ch {chan}")
                idx = get_visible_colors(i)
                dpg.bind_item_theme(f'ch{i}', f"plot_theme_{idx}")

    def rereference_data(data, ref_type):
        chans_to_incl = [chan for chan in range(n_chans) if chan_info[chan]['incl']]
        if ref_type == 'CAR':
            car_chan_data = data[chans_to_incl].T
            print(np.mean(car_chan_data, axis=1).shape, '<- mean shape')
            ref_data = car_chan_data - np.mean(car_chan_data, axis=1, keepdims=True)
        elif ref_type == 'LRR':
            print('LRR Not implemented yet :(')
            ref_data = None
        return ref_data.T

    def build_filter(filt_order, filt_range, fs):
        btype = 'bandpass'
        if filt_range[0] is None:
            btype = 'lowpass'
            filt_range = filt_range[1]
        elif filt_range[1] is None:
            btype = 'highpass'
            filt_range = filt_range[0]
        filter = butter(filt_order, filt_range, btype=btype, analog=False, output='sos', fs=fs)
        return btype, filter

    def filter_data(data, filt_order, filt_range, fs=30000):
        # global b, a, notch_f
        # Build and apply the filter
        data = data.T
        btype, filter = build_filter(filt_order, filt_range, fs)
        time_start = timeit.default_timer()
        if notch_f != 'None':
            sos = zpk2sos(*tf2zpk(b, a))
            data = sosfiltfilt(sos, data, axis=0)
        data = sosfiltfilt(filter, data, axis=0).T    
        time_end = timeit.default_timer()
        return data 

    def update_plots():
        # with dpg.mutex():
        for i in range(n_plots):
            vc_idx = get_idx(visible_chans[i])
            dpg.set_value(f'line{i}', [list(range(n_samples)), list(data_dict[waveform_type][vc_idx])])
            idx = get_visible_colors(i)
            dpg.bind_item_theme(f'line{i}', f"plot_theme_{idx}")

                    # for i in range(n_plots):
            plot_data = data_dict[waveform_type][vc_idx]
            y_min = np.min(plot_data[int(x_min):int(x_max)])
            y_max = np.max(plot_data[int(x_min):int(x_max)])
            y_delta = (y_max - y_min) * ax_mult
            y_margin = (y_max - y_min) * margin
            edge_mult = 30 if show_spikes else 1
            tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, 
                                                            y_max - y_delta]]
            dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
            dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*edge_mult, y_max+y_margin)

            if show_spikes:
                x_axis, y_axis = list(range(n_samples)), crossings[get_idx(visible_chans[i])]
                x_filtered, y_filtered = zip(*[(xi, y_min-y_margin*20) for xi, yi in zip(x_axis, y_axis) if yi == 1])

                dpg.set_value(f'scatter{i}', [list(x_filtered), list(y_filtered)])
                dpg.bind_item_theme(f'scatter{i}', f"plot_theme_{idx}")

    def update_high_filter(sender, data):
        # global filt_range
        # global filt_order
        filt_range = (data, filt_range[1])
        data_dict['filt'] = filter_data(data_dict['car'], filt_order, filt_range)
        if waveform_type == 'filt':
            update_plots()

    def update_low_filter(sender, data):
        # global filt_range
        # global filt_order
        filt_range = (filt_range[0], data)
        data_dict['filt'] = filter_data(data_dict['car'], filt_order, filt_range)
        if waveform_type == 'filt':
            update_plots()

    def update_filt_order(sender, data):
        # global filt_range
        # global filt_order
        filt_order = data
        data_dict['filt'] = filter_data(data_dict['car'], filt_order, filt_range)
        if waveform_type == 'filt':
            update_plots()

    def update_x_ticks(sender, app_data, axis_tag):
        x_min, x_max = dpg.get_axis_limits(axis_tag)
        tick_values = np.linspace(x_min, x_max, num_ticks)
        tick_labels = []
        for i, value in enumerate(tick_values):
            label = f"{value/30:.2f}" if i > 0 and (tick_values[i] - tick_values[i-1])/30 < 1 \
                                    else f'{int(value/30):,}'
            tick_labels.append((label, value))
        dpg.set_axis_ticks(axis_tag, tuple(tick_labels))

    def update_time_slider(x_max=None):
        if x_max is None:
            _, x_max = dpg.get_axis_limits('xaxis_tag0')
        dpg.set_value('time_slider', x_max)
        dpg.set_value('time_text', f'{float_to_time(x_max / sample_rate)} / {float_to_time(n_samples / sample_rate)}')

    def rewind():
        for i in range(n_plots):
            x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
            x_range = x_max - x_min
            x_min = 100
            x_max = x_min + x_range
            dpg.set_axis_limits(f'xaxis_tag{i}', x_min, x_range)
            y_min = np.min(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])
            y_max = np.max(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])
            y_delta = (y_max - y_min) * ax_mult
            y_margin = (y_max - y_min) * margin
            edge_mult = 30 if show_spikes else 1
            dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*edge_mult, y_max+y_margin)
            tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, y_max - y_delta]]
            dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
            
            if show_spikes:
                x_axis, y_axis = list(range(n_samples)), crossings[get_idx(visible_chans[i])]
                x_filtered, y_filtered = zip(*[(xi, y_min-y_margin*20) for xi, yi in zip(x_axis, y_axis) if yi == 1])
                dpg.set_value(f'scatter{i}', [list(x_filtered), list(y_filtered)])

        i = n_plots
        x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
        x_range = x_max - x_min
        x_min = 100
        x_max = x_min + x_range
        dpg.set_axis_limits(f'xaxis_tag{i}', x_min, x_max)
        tick_values = np.linspace(x_min, x_max, num_ticks)
        tick_labels = []
        for j, value in enumerate(tick_values):
            label = f"{value/30:.2f}" if j > 0 and (tick_values[j] - tick_values[j-1])/30 < 1 \
                                    else f'{int(value/30):,}'
            tick_labels.append((label, value))
        dpg.set_axis_ticks(f'xaxis_tag{i}', tuple(tick_labels))
        dpg.set_value('time_slider', x_max)
        dpg.set_value('time_text', f'{float_to_time(x_max / sample_rate)} / {float_to_time(n_samples / sample_rate)}')

    def fast_forward():
        for i in range(n_plots):
            x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
            x_range = x_max - x_min
            x_max = n_samples
            x_min = x_max - x_range
            dpg.set_axis_limits(f'xaxis_tag{i}', x_min, x_max)
            y_min = np.min(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])
            y_max = np.max(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])
            y_delta = (y_max - y_min) * ax_mult
            y_margin = (y_max - y_min) * margin
            edge_mult = 30 if show_spikes else 1
            dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*edge_mult, y_max+y_margin)
            tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, y_max - y_delta]]
            dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
            
            if show_spikes:
                x_axis, y_axis = list(range(n_samples)), crossings[get_idx(visible_chans[i])]
                x_filtered, y_filtered = zip(*[(xi, y_min-y_margin*20) for xi, yi in zip(x_axis, y_axis) if yi == 1])
                dpg.set_value(f'scatter{i}', [list(x_filtered), list(y_filtered)])

        i = n_plots
        x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
        x_range = x_max - x_min
        x_max = n_samples
        x_min = x_max - x_range
        dpg.set_axis_limits(f'xaxis_tag{i}', x_min, x_max)
        tick_values = np.linspace(x_min, x_max, num_ticks)
        tick_labels = []
        for j, value in enumerate(tick_values):
            label = f"{value/30:.2f}" if j > 0 and (tick_values[j] - tick_values[j-1])/30 < 1 \
                                    else f'{int(value/30):,}'
            tick_labels.append((label, value))
        dpg.set_axis_ticks(f'xaxis_tag{i}', tuple(tick_labels))
        dpg.set_value('time_slider', x_max)
        dpg.set_value('time_text', f'{float_to_time(x_max / sample_rate)} / {float_to_time(n_samples / sample_rate)}')

    def pause():
        global paused
        paused = True
        dpg.configure_item("play_bt_tag", enabled=True)
        dpg.configure_item("play_bt_tag", texture_tag="play_tag")
        dpg.configure_item("pause_bt_tag", enabled=False)
        dpg.configure_item("pause_bt_tag", texture_tag="pause_d_tag")

    def play():
        global paused
        paused = False
        dpg.configure_item("play_bt_tag", enabled=False)
        dpg.configure_item("play_bt_tag", texture_tag="play_d_tag")
        dpg.configure_item("pause_bt_tag", enabled=True)
        dpg.configure_item("pause_bt_tag", texture_tag="pause_tag")
        for i in range(n_plots):
            y_min = np.min(data_dict[waveform_type][get_idx(visible_chans[i]), 100:])
            y_max = np.max(data_dict[waveform_type][get_idx(visible_chans[i]), 100:])
            y_delta = (y_max - y_min) * ax_mult
            y_margin = (y_max - y_min) * margin
            edge_mult = 30 if show_spikes else 1
            dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*edge_mult, y_max+y_margin)
            tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, y_max - y_delta]]
            dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
            
            if show_spikes:
                x_axis, y_axis = list(range(n_samples)), crossings[get_idx(visible_chans[i])]
                x_filtered, y_filtered = zip(*[(xi, y_min-y_margin*20) for xi, yi in zip(x_axis, y_axis) if yi == 1])
                dpg.set_value(f'scatter{i}', [list(x_filtered), list(y_filtered)])

    def time_slider_drag(sender, data):
        start_idx, end_idx = dpg.get_axis_limits(f'xaxis_tag0')
        t_range = (end_idx - start_idx)
        start_idx = data - t_range
        end_idx = data

        if data < t_range:
            dpg.set_value('time_slider', t_range)
        else:
            for i in range(n_plots):
                # dpg.set_axis_limits_auto(f'xaxis_tag{i}')
                dpg.set_axis_limits(f'xaxis_tag{i}', start_idx, end_idx)
                y_min = np.min(data_dict[waveform_type][get_idx(visible_chans[i]), int(start_idx):int(end_idx)])
                y_max = np.max(data_dict[waveform_type][get_idx(visible_chans[i]), int(start_idx):int(end_idx)])
                y_delta = (y_max - y_min) * ax_mult
                y_margin = (y_max - y_min) * margin
                y_mult = 30 if show_spikes else 1
                dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*y_mult, y_max+y_margin)
                tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, y_max - y_delta]]
                dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
            i = n_plots
            dpg.set_axis_limits(f'xaxis_tag{i}', start_idx, end_idx)
            update_x_ticks(None, None, f'xaxis_tag{i}')
            dpg.set_value('time_text', f'{float_to_time(data / sample_rate)} / {float_to_time(n_samples / sample_rate)}')

    def wheel_callback(sender, data):
        # check if in plots
        # with dpg.mutex():
        for i in range(n_plots):
                x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
                x_min = np.max((x_min, 0))
                y_min = np.min(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])
                y_max = np.max(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])
                y_delta = (y_max - y_min) * ax_mult
                y_margin = (y_max - y_min) * margin
                y_mult = 30 if show_spikes else 1
                dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*y_mult, y_max+y_margin)
                tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, y_max - y_delta]]
                dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
                dpg.set_axis_limits_auto(f'xaxis_tag{i}')
        i = n_plots
        if data < 0: # data < 0 means scroll down (i.e zoom out)
            x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
            x_min = np.max((x_min, 0))
            if x_max > n_samples:
                dpg.set_axis_limits(f'xaxis_tag{i}', x_min, n_samples)
            elif x_min < 0:
                dpg.set_axis_limits(f'xaxis_tag{i}', 0, x_max)
        else: # data >0 means scroll up (i.e zoom in)
            x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
            x_min = np.max((x_min, 0))
            if x_min >= 0:
                dpg.set_axis_limits_auto(f'xaxis_tag{i}')
            elif x_max <= n_samples:
                dpg.set_axis_limits_auto(f'xaxis_tag{i}')
        update_x_ticks(sender, data, f'xaxis_tag{i}')
        update_time_slider()

    def left_click_drag_callback(sender, data):
        if dpg.is_item_hovered('subplots'):
            for i in range(n_plots):
                dpg.set_axis_limits_auto(f'xaxis_tag{i}')
                x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
                # x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
                x_min = np.max((x_min, 0))

                y_min = np.min(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])
                y_max = np.max(data_dict[waveform_type][get_idx(visible_chans[i]), int(x_min):int(x_max)])

                y_delta = (y_max - y_min) * ax_mult
                y_margin = (y_max - y_min) * margin
                y_mult = 30 if show_spikes else 1

                tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, y_max - y_delta]]
                dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
                x_axis, y_axis = list(range(n_samples)), crossings[get_idx(visible_chans[i])]
                x_filtered, y_filtered = zip(*[(xi, y_min-y_margin*20) for xi, yi in zip(x_axis, y_axis) if yi == 1])

                dpg.set_value(f'scatter{i}', [list(x_filtered), list(y_filtered)])
                dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*y_mult, y_max+y_margin)

            i=n_plots
            dpg.set_axis_limits_auto(f'xaxis_tag{i}')
            x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
            update_x_ticks(sender, data, f'xaxis_tag{i}')
            update_time_slider(x_max)

    n_notches = len(all_chans)
    sp_height = (subplots_height - 50)
    notch_height = sp_height / len(all_chans)
    s_bar_height = notch_height * n_plots 

    def ch_up():
        global initial_notch
        global visible_chans
        
        initial_notch = np.max((initial_notch - 1, 0))

        visible_chans = all_chans[initial_notch:initial_notch+n_plots]
        rect_pos[1] = initial_notch * notch_height
        dpg.configure_item('rectangle', pmin=rect_pos, pmax=[rect_pos[0] + scroll_bar_width, rect_pos[1] + s_bar_height])

        update_plots()
        for i in range(n_plots):
            chan = visible_chans[i]
            dpg.set_value(f'ch{i}', f"Ch {chan}")
            idx = get_visible_colors(i)
            dpg.bind_item_theme(f'ch{i}', f"plot_theme_{idx}")

    def ch_down():
        global initial_notch
        global visible_chans

        initial_notch = np.min((initial_notch + 1, n_notches - n_plots))

        visible_chans = all_chans[initial_notch:initial_notch+n_plots]
        rect_pos[1] = initial_notch * notch_height
        dpg.configure_item('rectangle', pmin=rect_pos, pmax=[rect_pos[0] + scroll_bar_width, rect_pos[1] + s_bar_height])

        update_plots()
        for i in range(n_plots):
            chan = visible_chans[i]
            dpg.set_value(f'ch{i}', f"Ch {chan}")
            idx = get_visible_colors(i)
            dpg.bind_item_theme(f'ch{i}', f"plot_theme_{idx}")

    def update_spike_plot(sender, data):
        data = get_idx(int(data))
        dpg.delete_item('spike_yaxis_tag', children_only=True)
        window_size = 320  # 40 samples before and 40 samples after the threshold crossing (assuming 30 kHz sampling rate)
        half_window = window_size // 2
        ch_crossings = np.argwhere(crossings[data])[:, 0]
        ch_crossings = ch_crossings[(ch_crossings >= half_window) & (ch_crossings < n_samples - half_window)]

        binned_crossings = np.floor_divide(ch_crossings, 30)
        unique_bins, counts = np.unique(binned_crossings, return_counts=True)
        single_crossing_bins = unique_bins[counts == 1]
        ch_crossings = np.array([ch_crossings[cr_idx] for cr_idx in range(len(ch_crossings)) if ch_crossings[cr_idx] - ch_crossings[cr_idx-1] > 30])
        ch_crossings = np.array([crossing for crossing in ch_crossings if np.floor_divide(crossing, 30) in single_crossing_bins])
        
        with dpg.mutex():
            for idx in ch_crossings:
                dat = data_dict['filt'][data][idx-half_window:idx+half_window]
                dpg.add_line_series(list(np.arange(-half_window, half_window)/30), list(dat), parent='spike_yaxis_tag')
            dpg.fit_axis_data('spike_yaxis_tag')

    def change_w_type(sender, data):
        # global waveform_type
        og_type = waveform_type
        if data == "Filtered":
            waveform_type = 'filt'
        elif data == "Raw":
            waveform_type = 'raw'
        elif data == "Re-Referenced":
            waveform_type = 'car'
        if og_type != waveform_type:
            update_plots()

    def update_notch(sender, data):
        # global notch_f
        notch_f = data
        data_dict['filt'] = filter_data(data_dict['car'], filt_order, filt_range)
        if waveform_type == 'filt':
            update_plots()

    def update_spike_panel(sender, data):
        data = get_idx(int(data))
        # dpg.delete_item(f'panel_yaxis_tag{data}', children_only=True)
        window_size = 100  # 40 samples before and 40 samples after the threshold crossing (assuming 30 kHz sampling rate)
        half_window = window_size // 2
        ch_crossings = np.argwhere(crossings[data])[:, 0]
        ch_crossings = ch_crossings[(ch_crossings >= half_window) & (ch_crossings < n_samples - half_window)]

        binned_crossings = np.floor_divide(ch_crossings, 30)
        unique_bins, counts = np.unique(binned_crossings, return_counts=True)
        single_crossing_bins = unique_bins[counts == 1]
        ch_crossings = np.array([ch_crossings[cr_idx] for cr_idx in range(len(ch_crossings)) if ch_crossings[cr_idx] - ch_crossings[cr_idx-1] > 30])
        ch_crossings = np.array([crossing for crossing in ch_crossings if np.floor_divide(crossing, 30) in single_crossing_bins])
        
        # with dpg.mutex():
        ymin = 1e10
        ymax = -1e10
        for idx in ch_crossings:
            dat = data_dict['filt'][data][idx-half_window:idx+half_window]
            if np.min(dat) < ymin:
                ymin = np.min(dat)
            if np.max(dat) > ymax:
                ymax = np.max(dat)
            x_list = list(np.arange(-half_window, half_window)/30)
            dpg.add_line_series(x_list, list(dat), tag=f'panel_plot{data}_{idx}', parent=f'panel_yaxis_tag{data}')
            dpg.bind_item_theme(f'panel_plot{data}_{idx}', 'spike_panel_theme')

        dpg.set_axis_limits(f'panel_yaxis_tag{data}', ymin*1.2, ymax*1.2)
        dpg.set_axis_limits(f'panel_xaxis_tag{data}', -half_window/30, half_window/30)

    # ---- DATA ----
    car_data = rereference_data(raw_30k_data, 'CAR')
    filt_data = filter_data(car_data, filt_order, filt_range, sample_rate)

    data_dict = {
        'raw': raw_30k_data,
        'car': car_data,
        'filt': filt_data
    }

    THRESH_MULT = 4.5

    thresholds = []
    for filt in filt_data:                                                          # loop through the groups of channels and calculate the RMS values
        thresholds.append(np.sqrt(np.mean(filt**2, axis=0)) * THRESH_MULT)

    POSITIVE_CROSSINGS = False

    crossings = []
    for filt, threshold in zip(filt_data, thresholds):   
        cross = np.zeros_like(filt)
        cross_init = (filt[1:] < -threshold) & (filt[:-1] >= -threshold)        # find the negative crossings
        cross[1:] = cross_init
        crossings.append(cross)

    
    # ---- THEMES ----
    # dpg.create_context()

    with dpg.theme(tag='bar_theme'):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, [45, 45, 46])
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, [45, 45, 46])

    with dpg.theme(tag='subplots_theme'):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, [37, 37, 38])
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, [37, 37, 38])

    with dpg.theme() as disabled_theme:
        with dpg.theme_component(dpg.mvImageButton, enabled_state=False):
            dpg.add_theme_color(dpg.mvThemeCol_Button, [40, 40, 41])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [40, 40, 41])
    dpg.bind_theme(disabled_theme)

    with dpg.theme(tag=f"disabled_chan"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 0, 0])

    with dpg.theme(tag=f"enabled_chan"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255])

    for idx, color in enumerate(color_map):
        with dpg.theme(tag=f"plot_theme_{idx}"):
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Up, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 4, category=dpg.mvThemeCat_Plots)

            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, color)
                dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize, 0, category=dpg.mvThemeCat_Plots)

            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)

    with dpg.theme(tag=f"spike_panel_theme"):
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 255), category=dpg.mvThemeCat_Plots)
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, [37, 37, 38])
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, [37, 37, 38])

    for tag in ['max_t', 'min_t']:
        with dpg.theme(tag=tag):    
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, [37, 37, 38], category=dpg.mvThemeCat_Plots)

    # ---- TEXTURE LOADING ----
    exe_path = sys.executable
    current_folder = os.path.dirname(os.path.abspath(exe_path))
    files = os.path.join(current_folder, '_internal')
    files='/Users/domenick_mifsud/Documents/NAY'

    play_width, play_height, play_channels, play_data = dpg.load_image(os.path.join(files,"play.png"))
    pause_width, pause_height, pause_channels, pause_data = dpg.load_image(os.path.join(files,"pause.png"))
    ff_width, ff_height, ff_channels, ff_data = dpg.load_image(os.path.join(files,"ff.png"))
    rw_width, rw_height, rw_channels, rw_data = dpg.load_image(os.path.join(files,"rw.png"))
    up_ch_width, up_ch_height, up_ch_channels, up_ch_data = dpg.load_image(os.path.join(files,"up_ch.png"))
    dn_ch_width, dn_ch_height, dn_ch_channels, dn_ch_data = dpg.load_image(os.path.join(files,"dn_ch.png"))

    play_d_width, play_d_height, play_d_channels, play_d_data = dpg.load_image(os.path.join(files,"play_d.png"))
    pause_d_width, pause_d_height, pause_d_channels, pause_d_data = dpg.load_image(os.path.join(files,"pause_d.png"))
    ff_d_width, ff_d_height, ff_d_channels, ff_d_data = dpg.load_image(os.path.join(files,"ff_d.png"))
    rw_d_width, rw_d_height, rw_d_channels, rw_d_data = dpg.load_image(os.path.join(files,"rw_d.png"))

    with dpg.texture_registry(show=False):
        dpg.add_static_texture(width=20, height=20, default_value=play_data, tag="play_tag")
        dpg.add_static_texture(width=20, height=20, default_value=pause_data, tag="pause_tag")
        dpg.add_static_texture(width=20, height=20, default_value=ff_data, tag="ff_tag")
        dpg.add_static_texture(width=20, height=20, default_value=rw_data, tag="rw_tag")
        dpg.add_static_texture(width=15, height=15, default_value=up_ch_data, tag="up_ch_tag")
        dpg.add_static_texture(width=15, height=15, default_value=dn_ch_data, tag="dn_ch_tag")

        dpg.add_static_texture(width=20, height=20, default_value=play_d_data, tag="play_d_tag")
        dpg.add_static_texture(width=20, height=20, default_value=pause_d_data, tag="pause_d_tag")
        dpg.add_static_texture(width=20, height=20, default_value=ff_d_data, tag="ff_d_tag")
        dpg.add_static_texture(width=20, height=20, default_value=rw_d_data, tag="rw_d_tag")

     # ------------- WINDOWS ---------------
    # File menu bar
    with dpg.viewport_menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Open", callback=lambda: print("Save Clicked"))

    with dpg.window(pos=[0,20], width=screen_width, height=screen_height-menu_bar_height, no_title_bar=True, no_collapse=True, no_close=True, horizontal_scrollbar=False, no_move=True, no_bring_to_front_on_focus=True):
        with dpg.group(horizontal=True):
            with dpg.group():

                # TOP BAR 
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=30)
                    dpg.add_combo(items=["Raw", "Re-Referenced", "Filtered"], default_value="Filtered", enabled=True, width=100, callback=change_w_type)
                    dpg.add_spacer(width=30)
                    dpg.add_checkbox(label="Show Spikes", callback=toggle_spikes, default_value=show_spikes)
                    dpg.add_spacer(width=plot_window_width*0.625)
                    dpg.add_input_int(label="Plot Height", default_value=100, width=100)

                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=5)

                    # CHANNEL LABELS
                    with dpg.group():
                        dpg.add_spacer(height=int(subplots_height/n_plots*0.3))  # Adjust as needed to center label
                        for i in range(n_plots):
                            chan = visible_chans[i]
                            dpg.add_text(f"Ch {chan}", tag=f'ch{i}', pos=[0, 0])
                            dpg.bind_item_theme(f'ch{i}', f"plot_theme_{i % len(color_map)}")

                    # PLOTS
                    with dpg.group(tag='subplots'):
                        with dpg.subplots(n_plots+1, 1, label="My Subplots", width=subplots_width, height=subplots_height, 
                                    link_all_x=True, no_title=True, no_menus=True, no_resize=True, row_ratios=row_ratios,):
                            for i in range(n_plots):
                                with dpg.plot(width=-1, tag=f'plot{i}'):
                                    dpg.add_plot_legend()
                                    x_min, x_max = start_x, end_x
                                    dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, show=True, tag=f'xaxis_tag{i}', no_tick_marks=True, no_tick_labels=True)
                                    dpg.set_axis_limits(dpg.last_item(), x_min, x_max)
                                    
                                    dpg.add_plot_axis(dpg.mvYAxis, no_gridlines=True,  tag=f'yaxis_tag{i}', lock_min=True, lock_max=True)

                                    plot_data = data_dict[waveform_type][get_idx(visible_chans[i])]
                                    y_min = np.min(plot_data[int(x_min):int(x_max)])
                                    y_max = np.max(plot_data[int(x_min):int(x_max)])
                                    y_delta = (y_max - y_min) * ax_mult
                                    y_margin = (y_max - y_min) * margin
                                    edge_mult = 30 if show_spikes else 1
                                    tick_labels = [(str(int(val)), val) for val in [y_min + y_delta, 
                                                                                    y_max - y_delta]]
                                    dpg.set_axis_ticks(f'yaxis_tag{i}', tuple(tick_labels))
                                    dpg.add_line_series(list(range(n_samples)), list(plot_data), parent=dpg.last_item(), tag=f'line{i}')
                                    dpg.bind_item_theme(f'line{i}', f"plot_theme_{i % len(color_map)}")
                                    
                                    x_axis, y_axis = list(range(n_samples)), crossings[get_idx(visible_chans[i])]
                                    x_filtered, y_filtered = zip(*[(xi, y_min-y_margin*20) for xi, yi in zip(x_axis, y_axis) if yi == 1])

                                    dpg.add_scatter_series(x_filtered, y_filtered, parent=f'yaxis_tag{i}', tag=f'scatter{i}', show=show_spikes)
                                    dpg.bind_item_theme(f'scatter{i}', f"plot_theme_{i % len(color_map)}")
                                    dpg.set_axis_limits(f'yaxis_tag{i}', y_min-y_margin*edge_mult, y_max+y_margin)

                            # X AXIS PLOT
                            i = n_plots
                            with dpg.plot(width=-1):
                                dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, show=True, tag=f'xaxis_tag{i}')
                                x_min, x_max = start_x, end_x
                                dpg.set_axis_limits(dpg.last_item(), x_min, x_max)
                                tick_values = np.linspace(x_min, x_max, num_ticks)

                                tick_labels = []
                                for j, value in enumerate(tick_values):
                                    if j > 0 and (tick_values[j] - tick_values[j-1])/30 < 1: # When differences are less than 1ms,
                                        label = f"{value/30:.2f}" # format with two decimal places.
                                    else: # Otherwise, format as integer.
                                        label = str(int(value/30))
                                    tick_labels.append((label, value))
                                dpg.set_axis_ticks(dpg.last_item(), tuple(tick_labels))

                                dpg.add_plot_axis(dpg.mvYAxis, no_gridlines=True, no_tick_marks=True, tag=f'yaxis_tag{i}', no_tick_labels=True, lock_min=True, lock_max=True)
                        
                        with dpg.group(horizontal=True):
                            dpg.add_text("Time (ms)", tag='x_label')
                            label_width = len("Time (ms)") * 8  # Assume each character is roughly 8 pixels wide
                            x_position = (subplots_width - label_width) // 2
                            dpg.set_item_pos('x_label', [x_position, subplots_height + 30])

                    dpg.bind_item_theme('subplots', 'subplots_theme')

                    # SCROLL BAR
                    with dpg.child_window(label="canvas_border", tag='canvas_border', width=scroll_bar_width+30, height=subplots_height+1, border=False, no_scrollbar=True):
                        dpg.add_image_button("up_ch_tag", callback=ch_up)
                        with dpg.drawlist(width=scroll_bar_width, height=sp_height, tag="draw_canvas", ):
                            dpg.draw_rectangle(pmin=[0, 0], pmax=[scroll_bar_width, s_bar_height], tag='rectangle', color=(65, 65, 66, 255), fill=(65, 65, 66, 255), rounding=10)
                        dpg.add_image_button("dn_ch_tag", callback=ch_down)

                # MEDIA BAR
                with dpg.group(horizontal=True):
                    dpg.add_image_button("rw_tag", callback=rewind)
                    dpg.add_image_button("play_tag", callback=play, tag='play_bt_tag')
                    dpg.add_image_button("pause_d_tag", callback=pause, enabled=False, tag='pause_bt_tag')

                    start_time = end_x / sample_rate
                    full_time = n_samples / sample_rate
                    with dpg.group():
                        dpg.add_spacer(height=0.7)
                        dpg.add_text(f'{float_to_time(start_time)} / {float_to_time(full_time)}', tag='time_text')
                    with dpg.group():
                        dpg.add_spacer(height=0.7)
                        dpg.add_slider_int(default_value=end_x, min_value=0, max_value=n_samples, format='', tag='time_slider', callback=time_slider_drag, width=plot_window_width-275)
                        dpg.bind_item_theme('time_slider', 'bar_theme')
                    
                    dpg.add_image_button("ff_tag", callback=fast_forward)

    # TAB WINDOW
    spaces = '   '
    with dpg.window(pos=[plot_window_width,20], width=tab_bar_width, height=screen_height-menu_bar_height, no_title_bar=True, no_scrollbar=True, no_collapse=True, no_close=True, tag='tab_bar_window', no_move=True):
        with dpg.tab_bar(tag="test_tab_bar") as tb:
            # CHANNELS TAB
            with dpg.tab(label=f"{spaces}Channels{spaces}", tag="test_tab_1"):
                max_channel_length = len(f"Ch {n_chans - 1}")
                max_impedance_length = max(len(f"{imp/1000:,.2f} kOhm") for imp in impedances)

                dpg.add_spacer(height=10)
                dpg.add_input_int(label="Impedance Threshold (kOhms)", default_value=def_imp_threshold, tag='imp_thresh', width=200, callback=filter_chans)
                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=20)
                    dpg.add_text("Channel".ljust(max_channel_length))
                    dpg.add_spacer(width=25)
                    dpg.add_text("Impedance".ljust(max_impedance_length))
                    dpg.add_text("Include in Ref.")
                    dpg.add_spacer(width=10)
                    dpg.add_text("Plot Channel")

                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=20)
                    with dpg.child(height=screen_height-menu_bar_height-150, width=425):  # Set desired height and width
                        for chan in range(n_chans):
                            with dpg.group(horizontal=True, tag=f'chan_sidebar_{chan}'):
                                # Pad Channel text to max length
                                dpg.add_text(f"Ch {chan}".ljust(max_channel_length), tag=f'tab_ch{chan}')
                                dpg.add_spacer(width=10)
                                # Pad Impedance text to max length
                                dpg.add_text(f"{impedances[chan]/1000:,.2f} kOhm".ljust(max_impedance_length), tag=f'impedance_ch{chan}')
                                dpg.add_spacer(width=60)
                                dpg.add_checkbox(label="", default_value=True, tag=f'include_{chan}')
                                dpg.add_spacer(width=70)
                                dpg.add_checkbox(label="", default_value=True, tag=f'plot_{chan}')
                            if impedances[chan] > dpg.get_value('imp_thresh') * 1000:
                                dpg.bind_item_theme(f'chan_sidebar_{chan}', f"disabled_chan")
                                dpg.set_value(f'include_{chan}', False)
                                dpg.set_value(f'plot_{chan}', False)

            # FILTERING TAB
            with dpg.tab(label=f"{spaces}Filtering{spaces}", tag="test_tab_2"):
                dpg.add_spacer(height=10)
                dpg.add_combo(label='Filter Type', items=["Butterworth", "??"], default_value="Butterworth", enabled=True, width=100)
                dpg.add_input_int(label="Filter Order", enabled=True, default_value=4, callback=update_filt_order, width=100)
                dpg.add_combo(label='Band Type', items=['Band-pass', 'Low-pass', 'High-pass'], default_value='Bandpass', enabled=True, width=100)
                dpg.add_input_int(label="Low", enabled=True, default_value=filt_range[0], callback=update_low_filter, width=100)
                dpg.add_input_int(label="High", enabled=True, default_value=filt_range[1], callback=update_high_filter, width=100)
                dpg.add_combo(label='Notch Filter', items=['None', '60 Hz'], default_value='60 Hz', enabled=True, width=100, callback=update_notch)
                dpg.add_spacer(height=30)

                signals = [data_dict['raw'].T, data_dict['car'].T, data_dict['filt'].T]
                labels = ['Raw', 'CAR', 'Filtered']

                # Calculate the PSD
                n_bins = sample_rate // 2 + 1
                freqs, S = [], []
                for s, l in zip(signals, labels):
                    nch = s.shape[1]
                    f, p = np.zeros((n_bins, nch)), np.zeros((n_bins, nch))
                    for ich in range(nch):
                        f[:, ich], p[:, ich] = signal.welch(s[:, ich], fs=sample_rate, nperseg=sample_rate)
                    freqs.append(f)
                    S.append(p)

                with dpg.plot(height=500, width=-1):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency (Hz)")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Power", tag='psd_yaxis_tag', log_scale=True)
                    p_max = np.max(p.mean(axis=1)[0:15000])
                    for f, p, l in zip(freqs, S, labels):
                        dpg.add_line_series(f.mean(axis=1)[0:15000], p.mean(axis=1)[0:15000], parent='psd_yaxis_tag', label=l, tag=f'psd_{l}')
                    dpg.add_line_series(list(np.arange(-1000,16000)), [p_max+0.1 for i in range(17000)], tag='max_l', parent='psd_yaxis_tag')
                    dpg.add_line_series(list(np.arange(-1000,16000)), [-0.1 for i in range(17000)], tag='min_l', parent='psd_yaxis_tag')
                    dpg.bind_item_theme('min_l', 'min_t')
                    dpg.bind_item_theme('max_l', 'max_t')
                    dpg.add_plot_legend(location=dpg.mvPlot_Location_NorthEast)

            # SPIKES TAB
            with dpg.tab(label=f"{spaces}Spikes{spaces}", tag="test_tab_3"):
                dpg.add_spacer(height=10)
                chans = []
                for chan in range(n_chans):
                    if chan_info[chan]['incl']:
                        chans.append(chan)
                def_ch = chans[0]
                dpg.add_input_float(label="Threshold Multiplier", default_value=4.5, tag='thresh_mult', width=200)
                dpg.add_spacer(height=50)
                with dpg.group(horizontal=True):
                    dpg.add_combo(label='Spike Scope Channel', items=chans, default_value=def_ch, enabled=True, width=100, tag='spk_sco_ch', callback=update_spike_plot)
                    dpg.add_spacer(width=150)
                    dpg.add_button(label="View All Channels", width=200, tag='view_all_chans')
                    with dpg.popup('view_all_chans', mousebutton=dpg.mvMouseButton_Left, modal=True, tag="modal_id"):
                        rows, cols = math.ceil(math.sqrt(len(chans))), math.ceil(len(chans) / math.ceil(math.sqrt(len(chans))))
                        with dpg.subplots(rows, cols, label="Spike Panel", width=subplots_height*1.25, height=subplots_height, no_title=True, no_menus=True, no_resize=True):
                            for i in range(len(chans)):
                                plot_size = 50
                                with dpg.plot(height=plot_size, width=plot_size*1.25):
                                    dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, show=True, tag=f'panel_xaxis_tag{i}')
                                    # dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, show=True, no_tick_marks=True, no_tick_labels=True)
                                    dpg.add_plot_axis(dpg.mvYAxis, label=f'Ch {chans[i]}', no_gridlines=True, show=True, tag=f'panel_yaxis_tag{i}', no_tick_marks=True, no_tick_labels=True)
                                    update_spike_panel(None, chans[i])
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=subplots_height*1.25/2-100)
                            dpg.add_text("Time relative to crossing (ms)")
                    dpg.bind_item_theme('modal_id', 'spike_panel_theme')

                with dpg.plot(height=500, width=-1):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time relative to crossing (ms)")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Voltage (uV)", tag='spike_yaxis_tag')
                    update_spike_plot(None, def_ch)

        dpg.bind_item_theme('tab_bar_window', 'bar_theme')


    # ------ RENDER LOOP ------

    with dpg.handler_registry():
        # dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Left, callback=drag_rect)
        dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Left, callback=left_click_drag_callback)
        dpg.add_mouse_wheel_handler(callback=wheel_callback)

    loaded = True
    dpg.hide_item("loading")

dpg.create_viewport(title='EphysViz', width=screen_width, height=screen_height, x_pos=0, y_pos=0)
dpg.setup_dearpygui()
dpg.show_viewport()
# dpg.start_dearpygui()

first_render = True

def callback(sender, app_data, user_data):
    dpg.show_item("loading")
    global holding
    holding = False
    test_func(list(app_data['selections'].values())[0])

with dpg.file_dialog(directory_selector=False, show=True, callback=callback, id="file_dialog_id", width=700 ,height=400):
    dpg.add_file_extension(".RHS", color=(0, 255, 0, 255), custom_text="[RHS]")

with dpg.window(show=False, tag='loading'):
    dpg.add_loading_indicator()
    dpg.add_text('Loading...')

# def test(sender, data):
#     print(sender, data)

# # with dpg.window(label="Tutorial", width=800, height=300):
# #     dpg.add_button(label="File Selector", callback=lambda: dpg.show_item("file_dialog_id"))

# dpg.create_viewport(title='Custom Title', width=800, height=600)
# dpg.setup_dearpygui()
# dpg.show_viewport()
# dpg.start_dearpygui()
# dpg.destroy_context()

# while holding:
#     print('test')
holding = True
loaded = False

while dpg.is_dearpygui_running():
    if not holding:
        if paused:
            last_update_time = timeit.default_timer()
        else:
            # pass
            if loaded:
                start_idx, end_idx = dpg.get_axis_limits(f'xaxis_tag0')
                current_time = timeit.default_timer()
                elapsed_time = current_time - last_update_time
                last_update_time = current_time
                num_new_samples = int(elapsed_time * sample_rate)
                start_idx += num_new_samples
                end_idx += num_new_samples
                if end_idx > n_samples:
                    paused = True
                    end_idx = n_samples
                else:
                    end_idx = min(end_idx, n_samples)
                    start_idx = min(start_idx, end_idx - 1)
                    start_idx = np.max((start_idx, 0))

                    for i in range(n_plots):
                        dpg.set_axis_limits(f'xaxis_tag{i}', start_idx, end_idx)

                    i = n_plots
                    dpg.set_axis_limits(f'xaxis_tag{i}', start_idx, end_idx)
                    x_min, x_max = dpg.get_axis_limits(f'xaxis_tag{i}')
                    tick_values = np.linspace(x_min, x_max, num_ticks)
                    tick_labels = []
                    for j, value in enumerate(tick_values):
                        label = f"{value/30:.2f}" if j > 0 and (tick_values[j] - tick_values[j-1])/30 < 1 \
                                                else f'{int(value/30):,}'
                        tick_labels.append((label, value))
                    dpg.set_axis_ticks(f'xaxis_tag{i}', tuple(tick_labels))
                    dpg.set_value('time_slider', x_max)
                    dpg.set_value('time_text', f'{float_to_time(x_max / sample_rate)} / {float_to_time(n_samples / sample_rate)}')

    
    # adjust all plot sizes to match:
    # dpg.get_item_pos('tab_bar_window')[0]

    dpg.render_dearpygui_frame()

    if loaded and first_render and not holding:
        print('done it@')
        for i in range(n_plots):
            x_pos, y_pos = dpg.get_item_pos(f'plot{i}')
            # x_pos, y_pos = dpg.get_item_pos(f'yaxis_tag{i}')
            dpg.set_item_pos(f'ch{i}', [x_pos, y_pos+(plot_heights*0.32)])
        first_render = False

dpg.destroy_context()
