import dearpygui.dearpygui as dpg
from util_funcs import *
from globals import *
from intanutil_rhs.read_data import read_data as rhs_read_data
from intanutil_rhd.read_data import read_data as rhd_read_data
import numpy as np
from scipy.signal import bessel, sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk


def start_excl_drag_callback(sender, app_data, user_data):
    new_start = dpg.get_value(sender)    
    # thresh_bins = int(data_get('n_samples') / 30 * 0.005)
    if np.abs(cfg_get('spike_excl_start') - new_start) > 0:
        if new_start < 0:
            dpg.set_value(sender, 0)
            return
        if new_start >= cfg_get('spike_excl_end'):
            dpg.set_value(sender, cfg_get('spike_excl_end') - 1)
            return
        cfg_set('spike_excl_start', new_start)
        with dpg.mutex():
            set_threshold_crossings()
            prepare_spike_panels(False)
            plot_spikes()


def end_excl_drag_callback(sender, app_data, user_data):
    new_end = dpg.get_value(sender)
    n_samples_ms = data_get('n_samples') // 30
    # thresh_bins = int(n_samples_ms * 0.005)
    if np.abs(cfg_get('spike_excl_end') - new_end) > 0:
        if new_end > n_samples_ms:
            dpg.set_value(sender, n_samples_ms)
            return
        if new_end <= cfg_get('spike_excl_start'):
            dpg.set_value(sender, cfg_get('spike_excl_start') + 1)
            return
        cfg_set('spike_excl_end', new_end)
        with dpg.mutex():
            set_threshold_crossings()
            prepare_spike_panels(False)
            plot_spikes()


def excl_toggle_callback(sender, app_data, user_data):
    dpg.configure_item('spike_panel_excl_range', show=app_data)
    cfg_set('exclude_period', app_data)
    set_threshold_crossings()
    prepare_spike_panels(False)
    plot_spikes()


def show_thresh_callback(sender, app_data, user_data):
    cfg_set('show_thresholds', app_data)
    spike_range = cfg_get('spike_start') * 30, cfg_get('spike_end') * 30
    electrode_mapping = cfg_get('electrode_mapping')
    if app_data:
        panel_range = cfg_get('spike_panel_range')
        plot_x = list(range(*panel_range))
        plot_x = np.array(plot_x) / 30
        panel_chan = int(dpg.get_value('spk_sco_ch').split('Ch ')[1])

        for row in range(4):
            for col in range(4):
                #chan = electrode_mapping[row][col]
                chan = 4 * row + col
                tag = f'panel_yaxis_row{row}_col{col}'

                if data_get('chan_info')[chan]['incl']:
                    crossings = data_get(f'crossings_{chan}')
                    crossings = crossings[crossings < spike_range[1]]
                    crossings = crossings[crossings > spike_range[0]]
                    if len(crossings) > 0:
                        threshold = data_get(f'thresholds_{chan}')
                        dpg.add_line_series(tag=f'threshold_line_{chan}',
                                            x=plot_x,
                                            y=[-threshold for _ in range(*panel_range)],
                                            parent=tag)
                        dpg.bind_item_theme(dpg.last_item(), 'white_bar')
        threshold = data_get(f'thresholds_{panel_chan}')
        dpg.add_line_series(tag='threshold_line',
                            label=' Threshold',
                            x=plot_x,
                            y=[-threshold for _ in range(*panel_range)],
                            parent='spike_yaxis_tag')
        dpg.bind_item_theme(dpg.last_item(), 'white_bar')
    else:
        dpg.delete_item('threshold_line')
        for row in range(4):
            for col in range(4):
                #chan = electrode_mapping[row][col]
                chan = 4 * row + col
                tag = f'panel_yaxis_row{row}_col{col}'
                if dpg.get_alias_id(f'threshold_line_{chan}') in dpg.get_item_children(tag)[1]:
                    dpg.delete_item(f'threshold_line_{chan}')


def tab_resize_callback(sender, app_data, user_data):
    pause()
    pos = dpg.get_item_pos('tabs_window')
    width = dpg.get_item_width('tabs_window')
    height = dpg.get_item_height('tabs_window')
    new_width = cfg_get('viewport_width') - width
    p_height, p_width, p_pos = cfg_get('tabs_window_state')

    if p_width != width and p_pos == pos:
        cfg_set('tabs_reset_state', True)
        pos = p_pos
        width = p_width
        height = p_height

    elif height != p_height:
        cfg_set('tabs_reset_state', True)
        pos = p_pos
        width = p_width
        height = p_height
    else:
        cfg_set('tabs_moved_state', True)
        cfg_set('tabs_window_state', (
            height,
            width,
            pos
        ))
        cfg_set('plots_window_width', new_width)
        cfg_set('tabs_window_width', width)
        dpg.configure_item('amplif_plots', width=new_width)
        dpg.configure_item('plot_window_width_group', width=new_width)
        dpg.configure_item('analog_plots_child', width=new_width)
        dpg.configure_item('analog_plots', width=new_width - cfg_get('channel_labels_width'))
        dpg.configure_item('amplif_plots', width=new_width - cfg_get('channel_labels_width'))
        cfg_set('subplots_width', new_width - cfg_get('channel_labels_width'))


def a_plot_resize_callback(sender, app_data, user_data):
    pause()
    pos = dpg.get_item_pos('analog_plots_child')
    width = dpg.get_item_width('analog_plots_child')
    height = dpg.get_item_height('analog_plots_child')
    p_height, p_width, p_pos = cfg_get('analog_window_state')
    p_tabs_height, p_tabs_width, p_tabs_pos = cfg_get('tabs_window_state')
    tabs_width = dpg.get_item_width('tabs_window')

    if p_height != height and p_pos == pos:
        cfg_set('analog_reset_state', True)
        pos = p_pos
        height = p_height
        width = p_width

    elif p_width != width:
        cfg_set('analog_reset_state', True)
        pos = p_pos
        width = p_width
        height = p_height

    else:
        new_height = cfg_get('subplots_height') - height
        dpg.configure_item('amplif_plots_child', height=new_height)
        dpg.configure_item('analog_plot_spacer', height=height)

        cfg_set('amplif_plots_height', new_height)
        cfg_set('analog_plots_height', height)

        try:
            set_plot_heights(resizing=True)
        except:
            pass
        dpg.split_frame()
        align_channel_labels()

    cfg_set('analog_window_state', (
        height,
        width,
        pos
    ))


def mouse_release_callback(sender, app_data, user_data):
    if cfg_get('analog_reset_state'):
        if cfg_get('tabs_moved_state'):
            cfg_set('analog_reset_state', False)
            cfg_set('tabs_moved_state', False)
            pos = dpg.get_item_pos('analog_plots_child')
            width = dpg.get_item_width('analog_plots_child')
            height = dpg.get_item_height('analog_plots_child')
            cfg_set('analog_window_state', (height, width, pos))
        else:
            height, width, pos = cfg_get('analog_window_state')
            dpg.configure_item(
                'analog_plots_child', 
                height=height,
                width=width,
                pos=pos
            )
            cfg_set('analog_reset_state', False)
            
    elif cfg_get('tabs_reset_state'):
        height, width, pos = cfg_get('tabs_window_state')
        dpg.configure_item(
            'tabs_window', 
            height=height,
            width=width,
            pos=pos
        )
        cfg_set('tabs_reset_state', False)

    elif cfg_get('tabs_moved_state'):
        cfg_set('tabs_moved_state', False)


def view_all_chans_callback(sender, app_data, user_data):
    pause()
    dpg.show_item('spike_panels')
    dpg.split_frame()
    for row in range(8):
        for col in range(4):
            dpg.set_axis_limits_auto(f'panel_xaxis_row{row}_col{col}')


def spike_chan_callback(sender, app_data, user_data):
    with dpg.mutex():
        cfg_set('spike_chan', int(app_data.split(' ')[1])) 
        prepare_spike_panels()
        unfreeze_x_axes()


def start_drag_callback(sender, app_data, user_data):
    new_start = dpg.get_value(sender)
    new_start = min(max(0, new_start), cfg_get('spike_end') - 1)
    # if cfg_get('spike_start') != new_start:
    cfg_set('spike_start', new_start)
    dpg.set_value('start_drag', new_start)
    dpg.set_value('start_drag_panel', new_start)
    with dpg.mutex():
        prepare_spike_panels(False)


def end_drag_callback(sender, app_data, user_data):
    new_end = dpg.get_value(sender)
    new_end = min(max(cfg_get('spike_start') + 1, new_end), data_get('n_samples') // 30)
    # if cfg_get('spike_end') != new_end:
    cfg_set('spike_end', new_end)
    dpg.set_value('end_drag', new_end)
    dpg.set_value('end_drag_panel', new_end)
    with dpg.mutex():
        prepare_spike_panels(False)


def thresh_mult_callback(sender, app_data, user_data):
    pause()
    cfg_set('threshold_mult', app_data)
    set_threshold_crossings()
    prepare_spike_panels(False)
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
    dpg.split_frame()
    fit_y_axes(True)


def plot_bt_callback(sender, app_data, user_data):
    chan = int(sender.split('_')[1])
    set_ch_info(chan, 'plot', app_data)
    set_plotted_channels()
    refresh_plots(filter_update=True, first_plot=False)
    dpg.split_frame()
    fit_y_axes(True)


def imp_thresh_callback(sender, app_data, user_data):
    cfg_set('impedance_threshold', app_data)
    sort_channels()    
    update_impedance_table()
    refresh_plots(filter_update=True, first_plot=True)
    set_threshold_crossings()
    prepare_spike_panels()
    plot_spikes()
    set_plot_heights(resizing=True)
    dpg.split_frame()
    align_channel_labels()


def file_dialog_cb(sender, app_data, user_data):

    dpg.hide_item("analog_plots_child")
    dpg.hide_item("plots_window")
    dpg.hide_item("tabs_window")
    dpg.show_item("loading_indicator")

    # load in the data from file

    filename = list(app_data['selections'].values())[0]
    file_extension = filename.split('.')[-1]
    if file_extension == 'rhs':
        read_data = rhs_read_data(filename=filename)
    else:
        read_data = rhd_read_data(filename=filename)
    data_set('n_samples', read_data['amplifier_data'].shape[1])
    data_set('raw_data', read_data['amplifier_data'])
    
    # extract the 30kHz analog data
    data_set(
        'analog_data', 
        read_data['board_adc_data'] if 'board_adc_data' in read_data else None)
    
    # extract the impedances
    channel_info = read_data['amplifier_channels']
    data_set('impedances', [
        chan['electrode_impedance_magnitude'] for chan in channel_info
    ])
    
    # dont plot or include channels over impedance threshold
    sort_channels()


    total_time_ms = data_get('n_samples') // 30
    quad = total_time_ms // 4
    # set the spike range to the range of the data    
    dpg.set_value('end_drag', total_time_ms)
    dpg.set_value('end_drag_panel', total_time_ms)
    cfg_set('spike_end', total_time_ms)
    dpg.set_value('start_excl_drag', quad)
    dpg.set_value('end_excl_drag', total_time_ms - quad)
    cfg_set('spike_excl_start', quad)
    cfg_set('spike_excl_end', total_time_ms - quad)
    border = int(data_get('n_samples') / 30 * 0.2)
    for label in ['xaxis_spk_label_tag', 
                  'xaxis_spk_label_tag_panel', 
                  'xaxis_spk_excl_label_tag']:
        dpg.set_axis_limits(
            label, -border, total_time_ms + border)
        dpg.set_axis_ticks(label, 
                           tuple([(f'{i:,.0f} ms', i) for i in \
                                  np.linspace(0, total_time_ms, 4)]))

    dpg.show_item("plots_window")
    dpg.show_item("tabs_window")
    if data_get('analog_data') is not None:
        # analog_plots_child
        dpg.show_item("analog_plots_child")
    else:
        dpg.configure_item('analog_plot_spacer', height=0)
        
    refresh_plots(
        cfg_get('visible_range'), filter_update=True, first_plot=True)
    
    dpg.hide_item("loading_indicator")

    dpg.split_frame()
    set_plot_heights(False)

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


def play(sender, app_data, user_data):
    cfg_set('paused', False)
    dpg.configure_item(
        'play_bt', enabled=False, texture_tag='play_disabled_texture')
    dpg.configure_item('pause_bt', enabled=True, texture_tag='pause_texture')


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
    cfg_set('show_spikes', int(app_data))
    set_plot_heights(False)


def amplif_height_cb(sender, app_data, user_data):
    pause()
    cfg_set('amplif_plot_heights', app_data)
    set_plot_heights(True)
    dpg.split_frame()
    align_channel_labels() 


def analog_height_cb(sender, app_data, user_data):
    pause()
    cfg_set('analog_plot_heights', app_data)
    set_plot_heights(True)
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