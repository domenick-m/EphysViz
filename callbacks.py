import dearpygui.dearpygui as dpg
from util_funcs import *
from globals import *
from intanutil.read_data import read_data
import numpy as np
from scipy.signal import bessel, sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk


def view_all_chans_callback(sender, app_data, user_data):
    dpg.show_item('spike_panels')
    dpg.split_frame()
    dpg.set_axis_limits_auto('spike_xaxis_tag')
    # dpg.configure_item('spike_panels', modal=True)

def spike_chan_callback(sender, app_data, user_data):
    print('chan:', app_data)
    cfg_set('spike_chan', int(app_data.split('Ch ')[1])) 

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
    
        prepare_spike_panels()
        plot_spikes()

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
    
        prepare_spike_panels()
        plot_spikes()

def thresh_mult_callback(sender, app_data, user_data):
    cfg_set('threshold_mult', app_data)
    
    # replot spikes, and panels

def update_filt_order(sender, app_data, user_data):
    cfg_set('filter_order', app_data)
    create_filters()

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))
    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    pre_fit_y_axes()

    prepare_psd()
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()
    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()
        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')

    
def update_filt_type(sender, app_data, user_data):
    cfg_set('filter_type', app_data)
    create_filters()

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))
    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    pre_fit_y_axes()
    prepare_psd()
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()

    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()

        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')

def update_band_type(sender, app_data, user_data):
    print('test', app_data)
    cfg_set('band_type', app_data)
    create_filters()

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))
    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    pre_fit_y_axes()

    prepare_psd()
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()

    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()
        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')


def update_low_filter(sender, app_data, user_data):
    print('test', app_data)
    cfg_set('filter_range', (app_data, cfg_get('filter_range')[1]))
    create_filters()

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))
    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    pre_fit_y_axes()
    prepare_psd()
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()

    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()

        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')


def update_high_filter(sender, app_data, user_data):
    print('test', app_data)
    cfg_set('filter_range', (cfg_get('filter_range')[0], app_data))
    create_filters()

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))
    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    pre_fit_y_axes()
    prepare_psd()
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()

    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()

        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')


def update_notch(sender, app_data, user_data):
    print('test', app_data)
    if app_data == 'None':
        cfg_set('notch_filter', False)
    else:
        cfg_set('notch_filter', True)

        # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if app_data else None
    ))
    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    pre_fit_y_axes()
    prepare_psd()
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()

    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()

        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')


def include_bt_callback(sender, app_data, user_data):
    chan = int(sender.split('_')[1])
    with dpg.mutex():
        if app_data:
            dpg.configure_item(f'plot_{chan}', enabled=True)
            set_ch_info(chan, 'plot', False)
            set_ch_info(chan, 'incl', True)
        else:
            dpg.set_value(f'plot_{chan}', value=False)
            dpg.configure_item(f'plot_{chan}', enabled=False)
            set_ch_info(chan, 'plot', False)
            set_ch_info(chan, 'incl', False)
    
        # car (could be new included) 
        chans_to_car = [
            chan for chan in range(cfg_get('max_amplif_channels')) \
            if data_get('chan_info')[chan]['incl']
        ]
        car = np.mean(data_get('raw_data')[chans_to_car], axis=0)
        data_set('re-referenced_data', data_get('raw_data')[chans_to_car] - car)

        # filter the data
        data_set('filtered_data', filter_data(
            data_get('re-referenced_data'), 
            data_get('filter'), 
            notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
        ))
        # plot the data
        buffer_handler(
            dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
            first_plot=True
        )

        # prepare the plots (hide invisible channels, set axis limits, set colors)
        prepare_plots()
        pre_fit_y_axes()
        prepare_psd()
        chans_avail = []
        for chan in range(cfg_get('max_amplif_channels')):
            if data_get('chan_info')[chan]['incl']:
                chans_avail.append(f'Ch {chan:02d}')

        dpg.configure_item(
            'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
        )
        prepare_spike_panels()


    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()

        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')


def plot_bt_callback(sender, app_data, user_data):
    chan = int(sender.split('_')[1])
    set_ch_info(chan, 'plot', app_data)

    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    pre_fit_y_axes()

    dpg.split_frame()
    with dpg.mutex():
        # auto fit the y limits
        post_fit_y_axes()
        # align the channel labels
        align_channel_labels()

def imp_thresh_callback(sender, app_data, user_data):
    print('imp_thresh_callback')
    print(f'where segfault01')
    cfg_set('impedance_threshold', app_data)
    print(f'where segfault02')
    threshold_impedances()
    print(f'where segfault03')
    update_impedance_table()
    print(f'where segfault04')

    # car (could be new included) 
    chans_to_car = [
        chan for chan in range(cfg_get('max_amplif_channels')) \
        if data_get('chan_info')[chan]['incl']
    ]
    print(f'where segfault05')
    car = np.mean(data_get('raw_data')[chans_to_car], axis=0)
    print(f'where segfault06')
    data_set('re-referenced_data', data_get('raw_data')[chans_to_car] - car)
    print(f'where segfault07')

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))
    print(f'where segfault08')
    # plot the data
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )
    print(f'where segfault09')

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    print(f'where segfault10')
    pre_fit_y_axes()
    print(f'where segfault11')
    prepare_psd()
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()

    dpg.split_frame()
    print(f'where segfault12=')
    with dpg.mutex():
        print(f'where segfault13')
        # auto fit the y limits
        post_fit_y_axes()
        print(f'where segfault14')
        # align the channel labels
        align_channel_labels()
        print(f'where segfault15')
        dpg.set_axis_limits_auto('psd_xaxis_tag')
        dpg.fit_axis_data('psd_xaxis_tag')

        print(f'where segfault16')

def file_dialog_cb(sender, app_data, user_data):
    print('file_dialog_cb')
    dpg.hide_item("plots_window")
    dpg.hide_item("tabs_window")
    dpg.show_item("loading_indicator")
    print(f'where segfault01')
    new_range = (0, 20000)
    cfg_set('visible_range', new_range) # 30kHz samples (0.66s)
    print(f'where segfault02')
    # dpg.split_frame()
    # with dpg.mutex():
    print(f'where segfault03')
    # load in the data from file
    rhs_data = read_data(list(app_data['selections'].values())[0])
    print(f'where segfault04')
    data_set('n_samples', rhs_data['amplifier_data'].shape[1])
    print(f'where segfault05')
    # extract the 30kHz amplifier data
    data_set('raw_data', rhs_data['amplifier_data'])
    print(f'where segfault06')
    # extract the 30kHz analog data
    data_set(
        'analog_data', 
        rhs_data['board_adc_data'] if 'board_adc_data' in rhs_data else None
    )
    print(f'where segfault07')
    # extract the impedances
    channel_info = rhs_data['amplifier_channels']
    print(f'where segfault08')
    data_set('impedances', [
        chan['electrode_impedance_magnitude'] for chan in channel_info
    ])
    print(f'where segfault09')
    # dont plot or include channels over impedance threshold
    threshold_impedances()
    print(f'where segfault10')
    # common avg reference the data (included channels only)
    chans_to_car = [
        chan for chan in range(cfg_get('max_amplif_channels')) \
        if data_get('chan_info')[chan]['incl']
    ]
    print(f'where segfault11')
    car = np.mean(data_get('raw_data')[chans_to_car], axis=0)
    print(f'where segfault12')
    data_set('re-referenced_data', data_get('raw_data')[chans_to_car] - car)
    print(f'where segfault13')

    # filter the data
    data_set('filtered_data', filter_data(
        data_get('re-referenced_data'), 
        data_get('filter'), 
        notch_sos=data_get('notch_sos') if cfg_get('notch_filter') else None
    ))
    print(f'where segfault14')

    # set the spike range to the range of the data
    cfg_set('spike_start', 0)
    print(f'where segfault14.25')
    cfg_set('spike_end', data_get('n_samples'))
    dpg.set_value('end_drag', data_get('n_samples') // 30)
    dpg.set_value('end_drag_panel', data_get('n_samples') // 30)

    print(f'where segfault14.5')

    # plot
    buffer_handler(new_range, first_plot=True)

    print(f'where segfault15')
    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()
    print(f'where segfault16')

    # prepare the impedance heatmap on the channels tab
    prepare_impedance_heatmap()
    print(f'where segfault17')

    # prepare the impedance table on the channels tab
    update_impedance_table()
    print(f'where segfault18')

    # prepare the PSD on the filtering tab
    prepare_psd()
    print(f'where segfault19')

    get_crossings()
    print(f'where segfault19.25')

    # prepare the spike panels on the spike tab
    chans_avail = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            chans_avail.append(f'Ch {chan:02d}')

    dpg.configure_item(
        'spk_sco_ch', items=chans_avail, default_value=chans_avail[0]
    )
    prepare_spike_panels()
    print(f'where segfault19.5')
    plot_spikes()
    print(f'where segfault19.75')

    if cfg_get('show_spikes'):
        height = 0
        row_ratios = []
        for chan in range(cfg_get('max_amplif_channels')):
            if data_get('chan_info')[chan]['plot']:
                dpg.configure_item(f'spikes_{chan}', show=cfg_get('show_spikes'))
                height += cfg_get('amplif_plot_heights')
                row_ratios.append(1)
                if cfg_get('show_spikes'): 
                    height += 0.1
                    row_ratios.append(0.1)
                else:
                    row_ratios.append(0)
            else:
                row_ratios.append(0)
                row_ratios.append(0)

        dpg.configure_item('amplif_plots', height=height, row_ratios=row_ratios)

    
    print(f'where segfault19.9')
    dpg.split_frame()
    print(f'where segfault19.99')
    align_channel_labels()
    print(f'where segfault20')

    # prepare the media/time controls
    prepare_time_controls(new_range)
    print(f'where segfault21')
    dpg.set_axis_limits(
        'xaxis_label_tag', *[int(i / 30) for i in new_range]
    )
    border = int(data_get('n_samples') / 30 * 0.2)
    # dpg.set_axis_limits(
    #     'xaxis_spk_label_tag', -border, data_get('n_samples') // 30 + border
    # )
    # dpg.set_axis_ticks(
    #     'xaxis_spk_label_tag', 
    #     tuple([(f'{i:,.0f} ms', i) for i in np.linspace(
    #             0, data_get('n_samples') // 30, 4
    #     )])
    # )
    for label in ['xaxis_spk_label_tag', 'xaxis_spk_label_tag_panel']:
        dpg.set_axis_limits(
            label, -border, data_get('n_samples') // 30 + border
        )
        dpg.set_axis_ticks(
            label, 
            tuple([(f'{i:,.0f} ms', i) for i in np.linspace(
                    0, data_get('n_samples') // 30, 4
            )])
        )
    print(f'where segfault22')

    pre_fit_y_axes()
    print(f'where segfault23')

    dpg.hide_item("loading_indicator")
    dpg.show_item("plots_window")
    dpg.show_item("tabs_window")
    print(f'where segfault24')

    dpg.split_frame()
    print(f'where segfault24')
    with dpg.mutex():
        print(f'where segfault25')
        # auto fit the y limits
        post_fit_y_axes()
        print(f'where segfault26')
        # allow dragging and scrolling of the x axis
        unfreeze_x_axes()
        # align the channel labels
        print(f'where segfault27')
        align_channel_labels()
        print(f'where segfault28')
        dpg.set_axis_limits_auto('psd_xaxis_tag')
        # dpg.fit_axis_data('psd_xaxis_tag')
        print(f'where segfault29')
    
def skip_reverse(sender, add_data, user_data):
    if cfg_get('paused'):
        def_amplif_chan = cfg_get('default_amplif_channel')
        amplif_range = dpg.get_axis_limits(f'xaxis_tag{def_amplif_chan}')
        amplif_range = amplif_range[1] - amplif_range[0]
        new_limits = (0, amplif_range)

        with dpg.mutex():
            align_axes('skip_reverse', new_limits)

def skip_forward(sender, add_data, user_data):
    if cfg_get('paused'):
        n_samples = data_get('n_samples')
        def_amplif_chan = cfg_get('default_amplif_channel')
        amplif_range = dpg.get_axis_limits(f'xaxis_tag{def_amplif_chan}')
        amplif_range = amplif_range[1] - amplif_range[0]
        new_limits = (n_samples - amplif_range, n_samples)

        with dpg.mutex():
            align_axes('skip_forward', new_limits)

def play(sender, add_data, user_data):
    print('play')
    print(f'where segfault01')
    cfg_set('paused', False)
    print(f'where segfault02')
    dpg.configure_item(
        'play_bt', enabled=False, texture_tag='play_disabled_texture'
    )
    print(f'where segfault03')
    dpg.configure_item('pause_bt', enabled=True, texture_tag='pause_texture')
    print(f'where segfault04')


def pause(sender, add_data, user_data):
    cfg_set('paused', True)
    dpg.configure_item(
        'pause_bt', enabled=False, texture_tag='pause_disabled_texture'
    )
    dpg.configure_item('play_bt', enabled=True, texture_tag='play_texture')

def time_slider_drag(sender, app_data, user_data):
    if cfg_get('paused'):
        def_amplif_chan = cfg_get('default_amplif_channel')
        amplif_range = dpg.get_axis_limits(f'xaxis_tag{def_amplif_chan}')
        new_limits = (app_data, app_data + amplif_range[1] - amplif_range[0])

        with dpg.mutex():
            align_axes('time_slider', new_limits)

def plot_zoom_callback(sender, app_data, user_data):
    if cfg_get('paused'):
        if dpg.is_item_hovered('amplif_plots_group'):
            unfreeze_x_axes()
            def_chan = cfg_get('default_amplif_channel')
            pre_fit_y_axes()
            dpg.split_frame()
            with dpg.mutex():
                align_axes(
                    'amplif_plots_group', 
                    dpg.get_axis_limits(f'xaxis_tag{def_chan}')
                )
                post_fit_y_axes()
        elif dpg.is_item_hovered('analog_plots_group'):
            unfreeze_x_axes()
            def_chan = cfg_get('default_analog_channel')
            pre_fit_y_axes()
            dpg.split_frame()
            with dpg.mutex():
                align_axes(
                    'analog_plots_group', 
                    dpg.get_axis_limits(f'a_xaxis_tag{def_chan}')
                )
                post_fit_y_axes()

def plot_drag_callback(sender, app_data, user_data):
    if cfg_get('paused'):
        if dpg.is_item_hovered('amplif_plots_group'):
            pre_fit_y_axes()
            unfreeze_x_axes()
            def_chan = cfg_get('default_amplif_channel')
            with dpg.mutex():
                align_axes(
                    'amplif_plots_group', 
                    dpg.get_axis_limits(f'xaxis_tag{def_chan}')
                )
            post_fit_y_axes()
        elif dpg.is_item_hovered('analog_plots_group'):
            unfreeze_x_axes()
            def_chan = cfg_get('default_analog_channel')
            with dpg.mutex():
                align_axes(
                    'analog_plots_group', 
                    dpg.get_axis_limits(f'a_xaxis_tag{def_chan}')
                )
            post_fit_y_axes()

def dir_dialog_cb(sender, app_data, user_data): 
    selected_dir = os.path.dirname(list(app_data['selections'].values())[0])
    write_settings('defaults', 'path', selected_dir)

def plot_type_cb(sender, app_data, user_data):
    print(app_data)
    cfg_set('waveform_type', app_data)
    # plot
    buffer_handler(
        dpg.get_axis_limits(f'xaxis_tag{cfg_get("default_amplif_channel")}'), 
        first_plot=True
    )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    prepare_plots()

def toggle_spikes_cb(sender, app_data, user_data):
    height = 0
    row_ratios = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            dpg.configure_item(f'spikes_{chan}', show=app_data)
            height += cfg_get('amplif_plot_heights')
            row_ratios.append(1)
            if app_data: 
                height += 0.1
                row_ratios.append(0.1)
            else:
                row_ratios.append(0)
        else:
            row_ratios.append(0)
            row_ratios.append(0)

    dpg.configure_item('amplif_plots', height=height, row_ratios=row_ratios)

    dpg.split_frame()
    align_channel_labels()

def amplif_height_cb(sender, app_data, user_data):
    cfg_set('amplif_plot_heights', app_data)
    height = 0
    row_ratios = []
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            dpg.configure_item(f'spikes_{chan}', show=cfg_get('show_spikes'))
            height += app_data
            row_ratios.append(1)
            if cfg_get('show_spikes'): 
                height += 0.1
                row_ratios.append(0.1)
            else:
                row_ratios.append(0)
        else:
            row_ratios.append(0)
            row_ratios.append(0)

    dpg.configure_item('amplif_plots', height=height, row_ratios=row_ratios)


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