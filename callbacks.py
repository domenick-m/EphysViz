import dearpygui.dearpygui as dpg
from util_funcs import *
from globals import *
from intanutil.read_data import read_data
import numpy as np
from scipy.signal import bessel, sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk


def view_all_chans_callback(sender, app_data, user_data):
    dpg.show_item('spike_panels')
    dpg.split_frame()
    for row in range(8):
        for col in range(4):
            dpg.set_axis_limits_auto(f'panel_xaxis_row{row}_col{col}')


def spike_chan_callback(sender, app_data, user_data):
    cfg_set('spike_chan', int(app_data.split('Ch ')[1])) 
    prepare_spike_panels()
    unfreeze_x_axes()


def start_drag_callback(sender, app_data, user_data):
    new_start = dpg.get_value(sender)
    if cfg_get('spike_start') // 30 != new_start:
        if new_start < 0:
            dpg.set_value(sender, 0)
            return
        if new_start >= cfg_get('spike_end') // 30:
            dpg.set_value(sender, cfg_get('spike_end') // 30 - 1)
            return
        cfg_set('spike_start', int(new_start * 30))
        with dpg.mutex():
            prepare_spike_panels()


def end_drag_callback(sender, app_data, user_data):
    new_end = dpg.get_value(sender)
    if cfg_get('spike_end') // 30 != new_end:
        if new_end > data_get('n_samples') // 30:
            dpg.set_value(sender, data_get('n_samples') // 30)
            return
        if new_end <= cfg_get('spike_start') // 30:
            dpg.set_value(sender, cfg_get('spike_start') // 30 + 1)
            return
        cfg_set('spike_end', int(new_end * 30))
        with dpg.mutex():
            prepare_spike_panels()


def thresh_mult_callback(sender, app_data, user_data):
    cfg_set('threshold_mult', app_data)
    set_threshold_crossings()
    prepare_spike_panels()
    plot_spikes()


def update_filt_order(sender, app_data, user_data):
    cfg_set('filter_order', app_data)
    refresh_plots(filter_update=True)

    
def update_filt_type(sender, app_data, user_data):
    cfg_set('filter_type', app_data)
    refresh_plots(filter_update=True)


def update_band_type(sender, app_data, user_data):
    cfg_set('band_type', app_data)
    refresh_plots(filter_update=True)


def update_low_filter(sender, app_data, user_data):
    cfg_set('filter_range', (app_data, cfg_get('filter_range')[1]))
    refresh_plots(filter_update=True)


def update_high_filter(sender, app_data, user_data):
    cfg_set('filter_range', (cfg_get('filter_range')[0], app_data))
    refresh_plots(filter_update=True)


def update_notch(sender, app_data, user_data):
    cfg_set('notch_filter', not app_data == 'None')
    refresh_plots(filter_update=True)


def include_bt_callback(sender, app_data, user_data):
    chan = int(sender.split('_')[1])
    if app_data:
        dpg.configure_item(f'plot_{chan}', enabled=True)
        set_ch_info(chan, 'plot', False)
        set_ch_info(chan, 'incl', True)
    else:
        dpg.set_value(f'plot_{chan}', value=False)
        dpg.configure_item(f'plot_{chan}', enabled=False)
        set_ch_info(chan, 'plot', False)
        set_ch_info(chan, 'incl', False)

    set_plotted_channels()
    set_included_channels()

    refresh_plots(filter_update=True, first_plot=False)


def plot_bt_callback(sender, app_data, user_data):
    chan = int(sender.split('_')[1])
    set_ch_info(chan, 'plot', app_data)
    refresh_plots(filter_update=True, first_plot=False)


def imp_thresh_callback(sender, app_data, user_data):
    sort_channels()    
    update_impedance_table()
    refresh_plots(filter_update=True, first_plot=True)


def file_dialog_cb(sender, app_data, user_data):

    dpg.hide_item("plots_window")
    dpg.hide_item("tabs_window")
    dpg.show_item("loading_indicator")

    # load in the data from file
    rhs_data = read_data(list(app_data['selections'].values())[0])
    data_set('n_samples', rhs_data['amplifier_data'].shape[1])
    data_set('raw_data', rhs_data['amplifier_data'])
    
    # extract the 30kHz analog data
    data_set(
        'analog_data', 
        rhs_data['board_adc_data'] if 'board_adc_data' in rhs_data else None)
    
    # extract the impedances
    channel_info = rhs_data['amplifier_channels']
    data_set('impedances', [
        chan['electrode_impedance_magnitude'] for chan in channel_info
    ])
    
    # dont plot or include channels over impedance threshold
    sort_channels()
    
    # set the spike range to the range of the data    
    cfg_set('spike_end', data_get('n_samples'))
    dpg.set_value('end_drag', data_get('n_samples') // 30)
    dpg.set_value('end_drag_panel', data_get('n_samples') // 30)
    border = int(data_get('n_samples') / 30 * 0.2)
    for label in ['xaxis_spk_label_tag', 'xaxis_spk_label_tag_panel']:
        dpg.set_axis_limits(
            label, -border, data_get('n_samples') // 30 + border)
        dpg.set_axis_ticks(label, 
                           tuple([(f'{i:,.0f} ms', i) for i in np.linspace(
                               0, data_get('n_samples') // 30, 4)]))

    dpg.show_item("plots_window")
    dpg.show_item("tabs_window")
        
    refresh_plots(
        cfg_get('visible_range'), filter_update=True, first_plot=True)
    
    dpg.hide_item("loading_indicator")

def skip_reverse(sender, add_data, user_data):
    if cfg_get('paused'):
        waveform_type = cfg_get('waveform_type').lower()
        plotted_chans = data_get(f'plotted_chans_{waveform_type}')
        amplif_range = dpg.get_axis_limits(f'xaxis_tag{plotted_chans[0][1]}')
        amplif_range = amplif_range[1] - amplif_range[0]
        new_limits = (0, amplif_range)

        with dpg.mutex():
            align_axes('skip_reverse', new_limits, True)


def skip_forward(sender, add_data, user_data):
    if cfg_get('paused'):
        n_samples = data_get('n_samples')
        waveform_type = cfg_get('waveform_type').lower()
        plotted_chans = data_get(f'plotted_chans_{waveform_type}')
        amplif_range = dpg.get_axis_limits(f'xaxis_tag{plotted_chans[0][1]}')
        amplif_range = amplif_range[1] - amplif_range[0]
        new_limits = (n_samples - amplif_range, n_samples)

        with dpg.mutex():
            align_axes('skip_forward', new_limits, True)


def play(sender, add_data, user_data):
    cfg_set('paused', False)
    dpg.configure_item(
        'play_bt', enabled=False, texture_tag='play_disabled_texture')
    dpg.configure_item('pause_bt', enabled=True, texture_tag='pause_texture')
    

def pause(sender, add_data, user_data):
    cfg_set('paused', True)
    dpg.configure_item(
        'pause_bt', enabled=False, texture_tag='pause_disabled_texture')
    dpg.configure_item('play_bt', enabled=True, texture_tag='play_texture')


def time_slider_drag(sender, app_data, user_data):
    if cfg_get('paused'):
        waveform_type = cfg_get('waveform_type').lower()
        plotted_chans = data_get(f'plotted_chans_{waveform_type}')
        amplif_range = dpg.get_axis_limits(f'xaxis_tag{plotted_chans[0][1]}')
        new_limits = (app_data, app_data + amplif_range[1] - amplif_range[0])
        with dpg.mutex():
            align_axes('time_slider', new_limits, False)
            fit_y_axes()

def plot_zoom_callback(sender, app_data, user_data):
    if cfg_get('paused'):
        if dpg.is_item_hovered('amplif_plots_group'):
            unfreeze_x_axes()
            waveform_type = cfg_get('waveform_type').lower()
            def_chan = data_get(f'plotted_chans_{waveform_type}')[0][1]

            with dpg.mutex():
                new_limits = dpg.get_axis_limits(f'xaxis_tag{def_chan}')
                align_axes('amplif_plots_group', new_limits)
                fit_y_axes()
            dpg.split_frame()
            with dpg.mutex():
                new_limits = dpg.get_axis_limits(f'xaxis_tag{def_chan}')
                align_axes('amplif_plots_group', new_limits)

        elif dpg.is_item_hovered('analog_plots_group'):
            unfreeze_x_axes()
            new_limits = dpg.get_axis_limits(f'a_xaxis_tag0')

            with dpg.mutex():
                align_axes('analog_plots_group', new_limits)
                fit_y_axes()
            dpg.split_frame()
            with dpg.mutex():
                align_axes('analog_plots_group', new_limits)


def plot_drag_callback(sender, app_data, user_data):
    if cfg_get('paused'):
        if dpg.is_item_hovered('amplif_plots_group'):
            unfreeze_x_axes()
            waveform_type = cfg_get('waveform_type').lower()
            def_chan = data_get(f'plotted_chans_{waveform_type}')[0][1]
            new_limits = dpg.get_axis_limits(f'xaxis_tag{def_chan}')

            with dpg.mutex():
                align_axes('amplif_plots_group', new_limits)
                fit_y_axes()

        elif dpg.is_item_hovered('analog_plots_group'):
            unfreeze_x_axes()
            new_limits = dpg.get_axis_limits(f'a_xaxis_tag0')

            with dpg.mutex():
                align_axes('analog_plots_group', new_limits)
                fit_y_axes()


def dir_dialog_cb(sender, app_data, user_data): 
    selected_dir = os.path.dirname(list(app_data['selections'].values())[0])
    write_settings('defaults', 'path', selected_dir)


def plot_type_cb(sender, app_data, user_data):
    cfg_set('waveform_type', app_data)
    set_plotted_channels()
    refresh_plots(filter_update=False, first_plot=True)


def toggle_spikes_cb(sender, app_data, user_data):
    cfg_set('show_spikes', app_data)
    set_plot_heights(False)
    # dpg.split_frame()
    # align_channel_labels()


def amplif_height_cb(sender, app_data, user_data):
    cfg_set('amplif_plot_heights', app_data)
    set_plot_heights(False)
    dpg.split_frame()
    align_channel_labels()


def analog_height_cb(sender, app_data, user_data):
    cfg_set('analog_plot_heights', app_data)
    set_plot_heights(False)
    dpg.split_frame()
    align_channel_labels()


def query_cb(sender, app_data, user_data):
    locs = cfg_get('locs')
    if sender.startswith('a_plot'):
        i = sender.split('a_plot')[1]
        prefix = 'a_'
    else:
        i = sender.split('plot')[1]
        prefix = ''
    if app_data != locs[int(i)]:
        dpg.configure_item(
            f'{prefix}query_text{i}', 
            show=True,
            label=f'{int((app_data[1] - app_data[0]) / 30)} ms',
            default_value=(app_data[1], app_data[3]),
        )
        locs[int(i)] = app_data
        cfg_set('locs', locs)


def remove_query_cb(sender, app_data, user_data):
    tag = sender.split('_clicked_handler')[0]
    if tag.startswith('a_plot'):
        tag = tag.split('a_plot')[1]
        dpg.configure_item(f'a_query_text{tag}', show=False)
    else:
        tag = tag.split('plot')[1]
        dpg.configure_item(f'query_text{tag}', show=False)