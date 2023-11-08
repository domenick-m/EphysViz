import dearpygui.dearpygui as dpg
from util_funcs import *
from globals import *
from intanutil.read_data import read_data
import numpy as np
from scipy.signal import bessel, sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk


def file_dialog_cb(sender, app_data, user_data):
    dpg.hide_item("plots_window")
    dpg.hide_item("tabs_window")
    dpg.show_item("loading_indicator")

    # dpg.split_frame()
    # with dpg.mutex():

    # LOAD IN DATA
    rhs_data = read_data(list(app_data['selections'].values())[0])

    data_set('raw_data', rhs_data['amplifier_data'])
    data_set(
        'analog_data', 
        rhs_data['board_adc_data'] if 'board_adc_data' in rhs_data else None
    )
    channel_info = rhs_data['amplifier_channels']
    data_set('impedances', [
        chan['electrode_impedance_magnitude'] for chan in channel_info
    ])
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('impedances')[chan] > cfg_get('impedance_threshold') * 1000:
            data_get('chan_info')[chan] = {'plot':False, 'incl':False}
        else:
            data_get('chan_info')[chan] = {'plot':True, 'incl':True}
    data_set('n_samples', data_get('raw_data').shape[1])

    # CAR the data (included channels only)
    chans_to_car = [
        chan for chan in range(cfg_get('max_amplif_channels')) \
        if data_get('chan_info')[chan]['incl']
    ]
    car = np.mean(data_get('raw_data')[chans_to_car], axis=0)
    data_set('car_data', data_get('raw_data')[chans_to_car] - car)

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('car_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))

    # create buffered data
    vis_range = cfg_get('visible_range')[1] - cfg_get('visible_range')[0]
    buffer = vis_range * cfg_get('buffer_mult')
    plotted_range = (
        int(max(cfg_get('visible_range')[0] - buffer, 0)), 
        int(min(cfg_get('visible_range')[1] + buffer, data_get('n_samples')))
    )

    # add raw data to the plot
    for chan in range(cfg_get('max_amplif_channels')):
        dpg.add_line_series(
            tag=f'raw_data_{chan}',
            x=list(range(*plotted_range)),
            y=data_get('raw_data')[chan, plotted_range[0]:plotted_range[1]],
            parent=f'yaxis_tag{chan}',
            show=False,
        )
    
    # add car data to the plot
    for idx, chan in enumerate(chans_to_car):
        dpg.add_line_series(
            tag=f're-referenced_data_{chan}',
            x=list(range(*plotted_range)),
            y=data_get('car_data')[idx, plotted_range[0]:plotted_range[1]],
            parent=f'yaxis_tag{chan}',
            show=False,
        )

    # # add filtered data to the plot
    for idx, chan in enumerate(chans_to_car):
        dpg.add_line_series(
            tag=f'filtered_data_{chan}',
            x=list(range(*plotted_range)),
            y=list(data_get('filtered_data')[idx, plotted_range[0]:plotted_range[1]]),
            parent=f'yaxis_tag{chan}',
            show=False,
        )
    # add analog data to the plot
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            dpg.add_line_series(
                tag=f'analog_data_{chan}',
                x=list(range(*plotted_range)),
                y=list(data_get('analog_data')[chan, plotted_range[0]:plotted_range[1]]),
                parent=f'a_yaxis_tag{chan}',
                show=True,
            )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()

    dpg.hide_item("loading_indicator")
    dpg.show_item("plots_window")
    dpg.show_item("tabs_window")

    # align the channel labels to the plots
    dpg.split_frame()
    with dpg.mutex():
        for pre, ran, ph in zip(
            ['', 'a_'], 
            [cfg_get('max_amplif_channels'), cfg_get('max_analog_channels')],
            [cfg_get('amplif_plot_heights'), cfg_get('analog_plot_heights')]
        ):
            for chan in range(ran):
                x_pos, y_pos = dpg.get_item_pos(f'{pre}plot{chan}')
                extra = 43 if pre == 'a_' else 0
                dpg.set_item_pos(
                    f'{pre}ch{chan}', 
                    [x_pos - 60 - extra, y_pos + ph / 2 - 14]
                    )
        # allow dragging / scrolling
        for chan in range(cfg_get('max_amplif_channels')):
            dpg.set_axis_limits_auto(f'xaxis_tag{chan}')
            dpg.set_axis_limits_auto(f'yaxis_tag{chan}')
            dpg.fit_axis_data(f'yaxis_tag{chan}')
            dpg.configure_item(f'yaxis_tag{chan}', lock_min=True, lock_max=True)

        for chan in range(cfg_get('max_analog_channels')):
            dpg.set_axis_limits_auto(f'a_xaxis_tag{chan}')
            dpg.set_axis_limits_auto(f'a_yaxis_tag{chan}')
            dpg.fit_axis_data(f'a_yaxis_tag{chan}')
    
    min_scale = 400
    # min_scale = 800
    dpg.configure_item('colormap_scale', min_scale=min_scale, max_scale=2000)
    dpg.add_heat_series(
        list(np.array(data_get('impedances')) / 1000), 
        rows=8, cols=4, 
        scale_min=min_scale, 
        scale_max=2000,
        format="",
        parent='imp_plot_yaxis'
    )

    start_x = 0.125
    start_y = 0.94
    gap_width = 0.25
    gap_height = 0.125
    ch_idx = 0
    for row in range(8):
        for col in range(4):
            min_color_val = min_scale
            max_color_val = 2000
            color_val = data_get('impedances')[ch_idx] / 1000
            if color_val < min_color_val:
                color_val = min_color_val
            if color_val > max_color_val:
                color_val = max_color_val
            color_range = max_color_val - min_color_val
            color_val = (color_val - min_color_val) / color_range
            color_int = int(color_val * 255)
            color = list((np.array(dpg.get_colormap_color(
                    'jet_colormap',
                    color_int,
                )) * 255).astype(int))
            
            imp= data["impedances"][ch_idx] / 1000
            dpg.add_plot_annotation(
                tag=f'bind_me{ch_idx}',
                label=f'Ch {ch_idx:02d}\n{" " if imp < 1000 else ""}{imp:,.0f}',
                color=color,
                default_value=(start_x + (col * gap_width), 
                                start_y - (row * gap_height)),
                parent='needs_cm'
            )
            ch_idx += 1
    dpg.configure_item('time_slider', max_value=data_get('n_samples'))

def skip_reverse(sender, add_data, user_data):
    print('skip_reverse')

def skip_forward(sender, add_data, user_data):
    print('skip_forward')

def play(sender, add_data, user_data):
    print('play')

def pause(sender, add_data, user_data):
    print('pause')

def time_slider_drag(sender, add_data, user_data):
    print('time_slider_drag')

def plot_zoom_callback(sender, app_data, user_data):
    if dpg.is_item_hovered('amplif_plots_group'):
        dpg.split_frame()
        with dpg.mutex():
            align_axes('amplif_plots_group', dpg.get_axis_limits(f'xaxis_tag0'))
    elif dpg.is_item_hovered('analog_plots_group'):
        dpg.split_frame()
        with dpg.mutex():
            align_axes('analog_plots_group', dpg.get_axis_limits(f'a_xaxis_tag0'))

def plot_drag_callback(sender, app_data, user_data):
    if dpg.is_item_hovered('amplif_plots_group'):
        with dpg.mutex():
            align_axes('amplif_plots_group', dpg.get_axis_limits(f'xaxis_tag0'))
    elif dpg.is_item_hovered('analog_plots_group'):
        with dpg.mutex():
            align_axes('analog_plots_group', dpg.get_axis_limits(f'a_xaxis_tag0'))

    # if sender in ['amplif_plots_group', 'analog_plots_group']:

    # if dpg.is_item_hovered('amplif_plots_group'):
    #     # with dpg.mutex():
    #     for i in range(cfg_get('max_amplif_channels')):
    #         dpg.configure_item(f'yaxis_tag{i}', lock_min=False, lock_max=False)
    #         dpg.fit_axis_data(f'yaxis_tag{i}')
    #         dpg.configure_item(f'yaxis_tag{i}', lock_min=True, lock_max=True)
    #     x_min, x_max = dpg.get_axis_limits(f'xaxis_tag0')

    #     buffer = (cfg_get('visible_range')[1] - cfg_get('visible_range')[0]) * cfg_get('buffer_mult')
    #     if x_max > cfg_get('visible_range')[1] + buffer * 0.25:
    #         cfg_set('visible_range', (x_min, x_max))
    #         plot_range = (
    #             int(max(cfg_get('visible_range')[0] - buffer, 0)), 
    #             int(cfg_get('visible_range')[1] + buffer)
    #         )
    #         for i in range(cfg_get('max_amplif_channels')):
    #             dpg.set_value(
    #                 f'{cfg["waveform_type"].lower()}_data_{i}',
    #                 [
    #                     list(range(*plot_range)),
    #                     list(data[f'{cfg["waveform_type"].lower()}_data'][i, plot_range[0]:plot_range[1]])
    #                 ]
    #             )

def mapping_change_cb(sender, app_data, user_data):
    prev_chan = sender.split('_')[0][2:]
    prev_sender_value = read_settings('mapping', sender, prev_chan)
    for chan in range(cfg_get('max_amplif_channels')):
        old_parent = f'ch{chan}_mapping'
        if int(read_settings('mapping', old_parent, chan)) == int(app_data):
            write_settings('mapping', old_parent, prev_sender_value)
            dpg.set_value(old_parent, f'{int(prev_sender_value):02d}')
            break
    write_settings('mapping', sender, app_data)
    dpg.set_value(sender, f'{int(app_data):02d}')

def dir_dialog_cb(sender, app_data, user_data): 
    selected_dir = os.path.dirname(list(app_data['selections'].values())[0])
    write_settings('defaults', 'path', selected_dir)

def plot_type_cb(sender, app_data, user_data):
    print(sender, app_data, user_data)

def toggle_spikes_cb(sender, app_data, user_data):
    dpg.configure_item(
        'amplif_plots', 
        height=cfg_get('amplif_plot_heights') * cfg_get('max_amplif_channels') * (1.5 if app_data else 1),
        row_ratios=[1, 0.5 if app_data else 0] * cfg_get('max_amplif_channels'),
    )
    dpg.split_frame()
    for chan in range(cfg_get('max_amplif_channels')):
        o_x_pos, _ = dpg.get_item_pos(f'ch{chan}')
        _, y_pos = dpg.get_item_pos(f'plot{chan}')
        dpg.set_item_pos(
            f'ch{chan}', 
            [o_x_pos, y_pos + cfg_get('amplif_plot_heights') / 2 - 14]
        )

def amplif_height_cb(sender, app_data, user_data):
    if app_data > int(cfg_get('amplif_plots_height') / cfg_get('max_amplif_channels')):
        # for chan in range(cfg_get('max_amplif_channels')):
        #     dpg.set_item_height(f'plot{chan}', app_data)
        dpg.configure_item('amplif_plots', height=app_data * cfg_get('max_amplif_channels'))
        dpg.split_frame()
        for chan in range(cfg_get('max_amplif_channels')):
            o_x_pos, _ = dpg.get_item_pos(f'ch{chan}')
            _, y_pos = dpg.get_item_pos(f'plot{chan}')
            dpg.set_item_pos(
                f'ch{chan}', 
                [o_x_pos, y_pos + app_data / 2 - 14]
            )

def analog_height_cb(sender, app_data, user_data):
    if app_data > int(cfg_get('amplif_plots_height') / cfg_get('max_analog_channels')):
        for chan in range(cfg_get('max_analog_channels')):
            dpg.set_item_height(f'a_plot{chan}', app_data)
        dpg.configure_item('analog_plots', height=app_data * cfg_get('max_analog_channels'))
        dpg.split_frame()
        for chan in range(cfg_get('max_analog_channels')):
            o_x_pos, _ = dpg.get_item_pos(f'a_ch{chan}')
            _, y_pos = dpg.get_item_pos(f'a_plot{chan}')
            dpg.set_item_pos(f'a_ch{chan}', [o_x_pos, y_pos + app_data / 2 - 14])

def query_cb(sender, app_data, user_data):
    locs = cfg_get('locs')
    i = sender.split('plot')[1]
    if app_data != locs[int(i)]:
        dpg.configure_item(
            f'query_text{i}', 
            show=True,
            default_value=(app_data[1], app_data[3]),
        )
        locs[int(i)] = app_data
        cfg_set('locs', locs)

    # dpg.split_frame()
    # if not dpg.is_plot_queried(sender):
    #     dpg.configure_item(f'query_text{i}', show=False)
    # dpg.configure_item

def remove_query_cb(sender, app_data, user_data):
    print(sender)

    # for i in range(cfg_get('max_amplif_channels')):
    #     dpg.configure_item(f'query_text{i}', show=False)
