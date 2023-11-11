import os
import sys
import numpy as np
import tkinter as tk
import scipy.signal as signal
import dearpygui.dearpygui as dpg
from matplotlib.colors import rgb_to_hsv, hsv_to_rgb
from scipy.signal import bessel, sosfiltfilt, butter, iirnotch, zpk2sos, tf2zpk
from globals import *

#------------------------------------------------------------------------------#
#                                  ETC FUNCS                                   #
#------------------------------------------------------------------------------#

#------------------------------------------------------------------------------#
#                                  PLOT FUNCS                                  #
#------------------------------------------------------------------------------#

#------------------------------------------------------------------------------#
#                                   UI FUNCS                                   #
#------------------------------------------------------------------------------#


def set_plot_heights(first_plot=False):
    # SHOULD SPLIT FRAME AFTER THIS AND ALIGN CHANNEL LABELS
    
    if data_get('analog_data') is not None:
        # if no analog data, hide the analog plots and resize
        dpg.hide_item('analog_plots_child')
        new_height = cfg_get('subplots_height')
        cfg_set('amplif_plots_height', new_height)
        dpg.configure_item('amplif_plots_child', height=new_height)
        dpg.configure_item('amplif_plots', height=new_height)

    height, height_ratios, chans_to_plot = [], [], []
    for chan in range(cfg_get('max_amplif_channels')):
        chan_info = data_get('chan_info')[chan]
        if chan_info['plot'] and chan_info['incl']:
            chans_to_plot.append(chan)
            # if showing spikes then make room for the spike plot
            spk_plt_height = int(cfg_get('show_spikes') * 0.1)
            height_ratios.extend([1 - spk_plt_height, spk_plt_height])
            
            # only show selected waveform type
            for waveform in ['raw', 'filtered', 're-referenced']:
                dpg.configure_item(
                    f'{waveform}_data_{chan}', show=(
                        cfg["waveform_type"].lower() == waveform
                    )
                )
        # if channel is not plotted, set height to 0                
        else:
            height_ratios.extend([0, 0])
            
    n_ch_to_plot = len(chans_to_plot)
    plot_heights = cfg_get('amplif_plot_heights')
    # resize the amplif plots to match the new number of channels
    if first_plot:
        # if first plot and def height is small overwrite it
        min_height = cfg_get('amplif_plots_height') / n_ch_to_plot
        if plot_heights < min_height:
            cfg_set('amplif_plot_heights', min_height)
            dpg.set_value('amplif_heights_input', min_height)
            plot_heights = min_height

    dpg.configure_item(
        'amplif_plots', 
        height=plot_heights * n_ch_to_plot,
        row_ratios=height_ratios
    )
    return chans_to_plot


def get_crossings():
    # get thresholds for each channel
    idx = 0
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            print(data_get('filtered_data').shape)
            filt_chan = data_get('filtered_data')[idx]
            print('testin here', np.mean(filt_chan**2, axis=0))
            rms_chan = np.sqrt(np.mean(filt_chan**2, axis=0))
            threshold = rms_chan * cfg_get('threshold_mult')
            data_set(f'thresholds_{chan}', threshold)

            # find the negative crossings
            cross = np.zeros_like(filt_chan)
            cross_init = (filt_chan[1:] < -threshold) & (filt_chan[:-1] >= -threshold)
            cross[1:] = cross_init
            cross_ = np.where(cross)[0]

            # binned_crossings = np.floor_divide(cross_, 30)
            # unique_bins, counts = np.unique(binned_crossings, return_counts=True)
            # single_crossing_bins = unique_bins[counts == 1]
            # cross_ = np.array([cross_[cr_idx] for cr_idx in range(len(cross_)) if cross_[cr_idx] - cross_[cr_idx-1] > 30])
            # cross_ = np.array([crossing for crossing in cross_ if np.floor_divide(crossing, 30) in single_crossing_bins])
        
            
            # print(cross.shape)
            data_set(f'crossings_{chan}', cross_)
            idx+=1


def prepare_spike_panels():
    panel_chan = int(dpg.get_value('spk_sco_ch').split('Ch ')[1])
    spike_range = cfg_get('spike_start'), cfg_get('spike_end')
    electode_mapping = cfg_get('electode_mapping')
    filt_data = data_get('filtered_data')
    panel_range = cfg_get('spike_panel_range')
    plot_x = list(range(*panel_range))
    samp_rate = cfg_get('sample_rate')

    idxs = {}
    idx = 0
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['incl']:
            idxs[chan] = idx
            idx += 1

    for row in range(8):
        for col in range(4):
            chan = electode_mapping[row][col]
            if chan == panel_chan:
                dpg.delete_item('spike_yaxis_tag', children_only=True)
                # crossings = data_get(f'crossings_{chan}')[spike_range[0]:spike_range[1]]
                # get crossings less than spike_range[1] and greater than spike_range[0]
                crossings = data_get(f'crossings_{chan}')
                sr_range = spike_range[1] - spike_range[0]
                crossings = crossings[crossings < spike_range[1]]
                crossings = crossings[crossings > spike_range[0]]
                ymin = 1e10
                ymax = -1e10
                for cross in crossings:
                    x_min = max(cross + panel_range[0], 0)
                    x_max = min(cross + panel_range[1], data_get('n_samples'))
                    padded = list(filt_data[idxs[chan], x_min:x_max])
                    
                    ymin = min((ymin, min(padded)))
                    ymax = max((ymax, max(padded)))

                    if len(plot_x) == len(padded):
                        dpg.add_line_series(
                            x=plot_x,
                            y=padded,
                            parent='spike_yaxis_tag',
                        )
                        dpg.bind_item_theme(
                            dpg.last_item(),
                            f'custom_color_{int((cross) / data_get("n_samples") * 256)}'
                        )


                threshold = data_get(f'thresholds_{chan}')
                dpg.add_line_series(
                    x=plot_x,
                    y=[-threshold for _ in range(*panel_range)],
                    parent='spike_yaxis_tag'
                )
                dpg.bind_item_theme(dpg.last_item(), 'white_bar')
                y_range = ymax - ymin
                dpg.set_axis_limits(
                    'spike_yaxis_tag', 
                    ymin - y_range * 0.05, 
                    ymax + y_range * 0.05
                )
                dpg.set_axis_limits(
                    'spike_xaxis_tag', 
                    panel_range[0]*1.2, 
                    panel_range[1]*1.2)
                
            tag = f'panel_yaxis_row{row}_col{col}'
            dpg.configure_item(tag, label=f'Ch {chan:02d}')
            dpg.delete_item(tag, children_only=True)
            if data_get('chan_info')[chan]['incl']:
                crossings = data_get(f'crossings_{chan}')
                sr_range = spike_range[1] - spike_range[0]
                crossings = crossings[crossings < spike_range[1]]
                crossings = crossings[crossings > spike_range[0]]
                ymin = 1e10
                ymax = -1e10
                for cross in crossings:
                    x_min = max(cross + panel_range[0], 0)
                    x_max = min(cross + panel_range[1], data_get('n_samples'))
                    padded = list(filt_data[idxs[chan], x_min:x_max])
                    
                    ymin = min((ymin, min(padded)))
                    ymax = max((ymax, max(padded)))

                    if len(plot_x) == len(padded):
                        dpg.add_line_series(
                            x=plot_x,
                            y=padded,
                            parent=tag,
                        )
                        dpg.bind_item_theme(
                            dpg.last_item(),
                            f'custom_color_{int((cross) / data_get("n_samples") * 256)}'
                        )


                threshold = data_get(f'thresholds_{chan}')
                dpg.add_line_series(
                    x=plot_x,
                    y=[-threshold for _ in range(*panel_range)],
                    parent=tag
                )
                dpg.bind_item_theme(dpg.last_item(), 'white_bar')
                dpg.set_axis_limits(tag, ymin*1.9, ymax*1.9)
                dpg.set_axis_limits(
                    f'panel_xaxis_row{row}_col{col}',
                    panel_range[0]*1.2, 
                    panel_range[1]*1.2)

            else:
                dpg.configure_item(
                    tag,
                    show=False
                )


def plot_spikes():
    # should this be plot all at once or buffer like continuous data?
    
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            crossings = data_get(f'crossings_{chan}')
            dpg.configure_item(
                f'spikes_{chan}', 
                show=True
            )
            y_vals = list(np.ones_like(crossings))
            dpg.set_value(
                f'spikes_{chan}', [list(crossings), y_vals]
            )
        else:
            dpg.configure_item(
                f'spikes_{chan}', 
                show=False
            )


def unfreeze_x_axes():
    for chan in range(cfg_get('max_amplif_channels')):
        dpg.set_axis_limits_auto(f'xaxis_tag{chan}')
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            dpg.set_axis_limits_auto(f'a_xaxis_tag{chan}')


def update_impedance_table():
    for chan in range(cfg_get('max_amplif_channels')):
        imp = data_get('impedances')[chan]
        dpg.set_value(
            f'impedance_ch{chan}', 
            f'{imp/1000:,.0f} kOhms'
        )
        if imp > cfg_get('impedance_threshold') * 1000:
            for text in [f'tab_ch{chan}', f'impedance_ch{chan}']:
                dpg.bind_item_theme(text, 'disabled_chan')
            for box in [f'include_{chan}', f'plot_{chan}']:
                dpg.set_value(box, value=False)
            dpg.configure_item(f'plot_{chan}', enabled=False)
        else:
            for text in [f'tab_ch{chan}', f'impedance_ch{chan}']:
                dpg.bind_item_theme(text, 'chan')
            for box in [f'include_{chan}', f'plot_{chan}']:
                dpg.set_value(box, value=True)
            dpg.configure_item(f'plot_{chan}', enabled=True)


def prepare_time_controls(limits):
    n_samples = data_get('n_samples')
    full_h, full_m, full_s = sec_to_hms(n_samples / cfg_get('sample_rate'))
    start_h, start_m, start_s = sec_to_hms(limits[0] / cfg_get('sample_rate'))
    # set elapsed / full time text
    dpg.set_value(
        'time_text', 
        f'{start_m:02d}:{start_s:02d} / {full_m:02d}:{full_s:02d}'
    )

    # set the width of the time slider
    lim_range = limits[1] - limits[0]
    time_slider_width = int(cfg_get('subplots_width') - 195)
    width = lim_range / n_samples * time_slider_width
    dpg.bind_item_theme('time_slider', f'grab_{max(int(width), 5)}')

    # set max value and handle position of the time slider
    max_val = n_samples - lim_range
    dpg.configure_item('time_slider', max_value=max_val)
    dpg.set_value('time_slider', limits[0])

    # enable or disable the skip buttons
    for i, lim, dir in zip([0, 1], [0, n_samples], ['left', 'right']):
        # enabled = limits[i] <= lim if dir == 'left' else limits[i] >= lim
        enabled = limits[i] > lim if dir == 'left' else limits[i] < lim
        if cfg_get(f'skip_{dir}_enabled') != enabled:
            cfg_set(f'skip_{dir}_enabled', enabled)
            texture = f'skip_{dir}_{"disabled_" if not enabled else ""}texture'
            dpg.configure_item(
                f'skip_{dir}_bt', texture_tag=texture, enabled=enabled
            )


def prepare_impedance_heatmap():
    # change if needed
    min_scale = 400
    max_scale = 2000 # considering over 2MOhms to be bad
    dpg.configure_item(
        'colormap_scale', min_scale=min_scale, max_scale=max_scale
    )

    start_x = 0.125
    start_y = 0.94
    gap_width = 0.25
    gap_height = 0.125
    values = []
    for row in range(8):
        # values_row = []
        for col in range(4):
            ch_idx = cfg_get('electode_mapping')[row][col]
            min_color_val = min_scale
            max_color_val = 2000
            color_val = data_get('impedances')[ch_idx] / 1000
            values.append(color_val)
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
                label=f'Ch {ch_idx:02d}\n{" " if imp < 1000 else ""}{imp:,.0f}',
                color=color,
                default_value=(start_x + (col * gap_width), 
                                start_y - (row * gap_height)),
                parent='imp_heatmap'
            )
            ch_idx += 1
        # values.append(values_row)
    
    dpg.add_heat_series(
        values, 
        rows=8, cols=4, 
        scale_min=min_scale, 
        scale_max=2000,
        format="",
        parent='imp_plot_yaxis'
    )


def prepare_psd():
    signals = [
        data_get('raw_data').T, 
        data_get('re-referenced_data').T, 
        data_get('filtered_data').T
    ]
    labels = ['Raw', 'CAR', 'Filtered']

    # Calculate the PSD
    n_bins = cfg_get('sample_rate') // 2 + 1
    freqs, S = [], []
    for s, l in zip(signals, labels):
        nch = s.shape[1]
        f, p = np.zeros((n_bins, nch)), np.zeros((n_bins, nch))
        for ich in range(nch):
            f[:, ich], p[:, ich] = signal.welch(
                s[:, ich], fs=cfg_get('sample_rate'), 
                nperseg=cfg_get('sample_rate')
            )
        freqs.append(f)
        S.append(p)
    p_max = np.max(p.mean(axis=1)[0:15000])
    for f, p, l in zip(freqs, S, labels):
        dpg.set_value(f'psd_{l}', [
            f.mean(axis=1)[0:15000], p.mean(axis=1)[0:15000]
        ])
    dpg.set_axis_limits('psd_yaxis_tag', -10000, p_max * 10)
    dpg.set_axis_limits('psd_xaxis_tag', -50, 1500)


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


def align_channel_labels():
    for channel_type in ['amplif', 'analog']:
        analog = channel_type == 'analog'
        prefix = 'a_' if analog else ''
        if not analog or data_get(f'{channel_type}_data') is not None:
            for chan in range(cfg_get(f'max_{channel_type}_channels')):
                if data_get('chan_info')[chan]['plot']:
                    dpg.show_item(f'{prefix}ch{chan}')
                    x_pos, y_pos = dpg.get_item_pos(f'{prefix}plot{chan}')
                    plot_height = cfg_get(f'{channel_type}_plot_heights')
                    dpg.set_item_pos(
                        f'{prefix}ch{chan}', 
                        [x_pos - 40, y_pos + plot_height / 2 - 14]
                    )
                else:
                    dpg.hide_item(f'{prefix}ch{chan}')


def threshold_impedances():
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('impedances')[chan] > cfg_get('impedance_threshold') * 1000:
            set_ch_info(chan, 'incl', False)
            set_ch_info(chan, 'plot', False)
        else:
            set_ch_info(chan, 'incl', True)
            set_ch_info(chan, 'plot', True)


def color_channels():
    # should color the channel labels and plots based on number of plots shown
    pass


def plot_data_play(plot_range):
    # this version of plot data is for the play function, it deletes and re-adds
    # the plotted data instead of setting the values
    idx = 0
    n_colors = len(cfg_get('colors'))
    for chan in range(cfg_get(f'max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            tag = f'{cfg["waveform_type"].lower()}_data'
            dpg.delete_item(f'{tag}_{chan}')
            dpg.add_line_series(
                tag=f'{tag}_{chan}',
                x=list(range(*plot_range)),
                y=list(data[tag][idx, plot_range[0]:plot_range[1]]),
                show=True,
                parent=f'yaxis_tag{chan}'
            )
            dpg.bind_item_theme(f'{tag}_{chan}', 
                                f'color_{idx % n_colors}')
            idx += 1
            dpg.set_axis_limits(f'xaxis_tag{chan}', *plot_range)
            # dpg.bind_item_handler_registry(f'plot{chan}', f'plot{chan}_handler', ) 

    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            dpg.delete_item(f'analog_data_{chan}')
            dpg.add_line_series(
                tag=f'analog_data_{chan}',
                x=list(range(*plot_range)),
                y=list(data['analog_data'][chan, plot_range[0]:plot_range[1]]),
                show=True,
                parent=f'a_yaxis_tag{chan}'
            )
            dpg.bind_item_theme(f'analog_data_{chan}', 
                                f'color_{chan % n_colors}')
            dpg.set_axis_limits(f'a_xaxis_tag{chan}', *plot_range)
            # dpg.bind_item_handler_registry(
            #     f'a_plot{chan}', f'a_plot{chan}_handler'
            # ) 
    dpg.set_axis_limits(
        'xaxis_label_tag', *[int(i / 30) for i in plot_range]
    )
    prepare_time_controls(plot_range)


def plot_data(plot_range, first_plot=False):
    # store the first visible channel as the default channel (for axis limits)
    dc_set_amplif, dc_set_analog = False, False
    idx = 0
    for chan in range(cfg_get(f'max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            if first_plot and not dc_set_amplif:
                cfg_set('default_amplif_channel', chan)
                dc_set_amplif = True
            dpg.set_value(
                f'{cfg["waveform_type"].lower()}_data_{chan}',
                [
                    list(range(*plot_range)),
                    list(data[f'{cfg["waveform_type"].lower()}_data'][
                        idx, plot_range[0]:plot_range[1]
                    ])
                ]
            )
            idx += 1
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            if first_plot and not dc_set_analog:
                cfg_set('default_analog_channel', chan)
                dc_set_analog = True
            dpg.set_value(
                f'analog_data_{chan}',
                [
                    list(range(*plot_range)),
                    list(data['analog_data'][
                        chan, plot_range[0]:plot_range[1]
                    ])
                ]
            )


def pre_fit_y_axes():
    for chan in range(cfg_get(f'max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            dpg.configure_item(f'yaxis_tag{chan}', lock_min=False, lock_max=False)
            dpg.fit_axis_data(f'yaxis_tag{chan}')
            # dpg.configure_item(f'yaxis_tag{chan}', lock_min=True, lock_max=True)
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=False, lock_max=False)
            dpg.fit_axis_data(f'a_yaxis_tag{chan}')
            # dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=True, lock_max=True)


def post_fit_y_axes():
    for chan in range(cfg_get(f'max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            # dpg.configure_item(f'yaxis_tag{chan}', lock_min=False, lock_max=False)
            # dpg.fit_axis_data(f'yaxis_tag{chan}')
            dpg.configure_item(f'yaxis_tag{chan}', lock_min=True, lock_max=True)
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            # dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=False, lock_max=False)
            # dpg.fit_axis_data(f'a_yaxis_tag{chan}')
            dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=True, lock_max=True)


def fit_y_axes():
    for chan in range(cfg_get(f'max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            dpg.configure_item(f'yaxis_tag{chan}', lock_min=False, lock_max=False)
            dpg.fit_axis_data(f'yaxis_tag{chan}')
            dpg.configure_item(f'yaxis_tag{chan}', lock_min=True, lock_max=True)
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=False, lock_max=False)
            dpg.fit_axis_data(f'a_yaxis_tag{chan}')
            dpg.configure_item(f'a_yaxis_tag{chan}', lock_min=True, lock_max=True)


def buffer_handler(new_limits, first_plot=False):
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
        new_limits[1] > visible_range[1] + view_limit or \
        first_plot
    ):
        plot_range = (
            int(max(new_limits[0] - buffer, 0)), 
            int(min(new_limits[1] + buffer, data_get('n_samples')))
        )
        cfg_set('visible_range', new_limits)
        plot_data(plot_range, first_plot=first_plot)


def align_axes(sender, new_limits, first_plot=False):
    visible_range = cfg_get('visible_range')
    if visible_range == new_limits: return
    buffer_handler(new_limits, first_plot=first_plot)

    if sender == 'amplif_plots_group':
        # align analog plots, time axis, and time controls
        if data_get('analog_data') is not None:
            for i in range(cfg_get('max_analog_channels')):
                dpg.set_axis_limits(f'a_xaxis_tag{i}', *new_limits)
        dpg.set_axis_limits(
            'xaxis_label_tag', *[int(i / 30) for i in new_limits]
        )
        prepare_time_controls(new_limits)

    elif sender == 'analog_plots_group':
        # align amplif plots, time axis, and time controls
        for i in range(cfg_get('max_amplif_channels')):
            dpg.set_axis_limits(f'xaxis_tag{i}', *new_limits)
        dpg.set_axis_limits(
            'xaxis_label_tag', 
            *[int(i / 30) for i in new_limits]
        )
        prepare_time_controls(new_limits)

    else:
        # align amplif plots and analog plots, and time axis
        for i in range(cfg_get('max_amplif_channels')):
            dpg.set_axis_limits(f'xaxis_tag{i}', *new_limits)
        if data_get('analog_data') is not None:
            for i in range(cfg_get('max_analog_channels')):
                dpg.set_axis_limits(f'a_xaxis_tag{i}', *new_limits)
        dpg.set_axis_limits(
            'xaxis_label_tag', *[int(i / 30) for i in new_limits]
        )
        prepare_time_controls(new_limits)


def adjust_color_brightness_saturation(rgb_colors, brightness_factor, saturation_factor):
    # Function to adjust the brightness and saturation of colors
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


def replot(first_plot=False):
    pass


def prepare_plots(first_plot=False):
    # get the channels to plot
    colors = cfg_get('plot_colors')
    chans_to_plot = set_plot_heights(first_plot)
    for idx, chan in enumerate(chans_to_plot):
        color = f'color_{idx % len(colors)}'
        tag = f'{cfg["waveform_type"].lower()}_data_{chan}'
        # set to the correct color
        dpg.bind_item_theme(tag, color)
        dpg.bind_item_theme(f'ch{chan}', color)
        dpg.bind_item_theme(f'spikes_{chan}', color)
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


def get_play_limits(last_update_time, current_time):
    current_limit = dpg.get_axis_limits(
        f'xaxis_tag{cfg_get("default_amplif_channel")}'
    )
    lim_range = current_limit[1] - current_limit[0]
    elapsed_time = current_time - last_update_time
    n_new = int(
        elapsed_time * \
        cfg_get('sample_rate') * \
        float(cfg_get('play_speed').split('x')[0])
    )
    new_start = current_limit[0] + n_new
    if new_start > data_get('n_samples') - lim_range:
        cfg_set('paused', True)
        dpg.configure_item(
            'pause_bt', enabled=False, texture_tag='pause_disabled_texture'
        )
        dpg.configure_item('play_bt', enabled=True, texture_tag='play_texture')
        return int(current_limit[0]), int(current_limit[1])
    new_end = new_start + lim_range
    return int(new_start), int(new_end)


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
    # return screen_height, int(screen_width)
    return screen_height - 200, int(screen_width) - 500


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



