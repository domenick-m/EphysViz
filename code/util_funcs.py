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
#                                 DATA FUNCS                                   #
#------------------------------------------------------------------------------#

def sort_channels():
    """ _ """
    # sorts the channels by impedance
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('impedances')[chan] > cfg_get('impedance_threshold') * 1000:
            set_ch_info(chan, 'incl', False)
            set_ch_info(chan, 'plot', False)
        else:
            set_ch_info(chan, 'incl', True)
            set_ch_info(chan, 'plot', True)
    # creates lists for easy access
    set_included_channels()
    set_plotted_channels()


def set_included_channels():
    """ _ """
    # sets the channels that are included in the CAR
    for waveform_type in ['raw', 'filtered', 're-referenced']:
        included_chans = []
        idx = 0
        for chan in range(cfg_get('max_amplif_channels')):
            if data_get('chan_info')[chan]['incl']:
                included_chans.append((chan if waveform_type == 'raw' else idx, 
                                       chan))
                idx += 1
        data_set(f'included_chans_{waveform_type}', included_chans)


def set_plotted_channels():
    """ _ """
    # sets the channels that are plotted
    for waveform_type in ['raw', 'filtered', 're-referenced']:
        plotted_chans = []
        idx = 0
        for chan in range(cfg_get('max_amplif_channels')):
            if data_get('chan_info')[chan]['incl']:
                if data_get('chan_info')[chan]['plot']:
                    plotted_chans.append((chan if waveform_type == 'raw' else idx, 
                                        chan))
                idx += 1
        data_set(f'plotted_chans_{waveform_type}', plotted_chans)


def car_data():
    """ _ """
    # average across channels for all time points and subtract from each channel
    included_chans = [i for _, i in data_get('included_chans_raw')]
    incl_data = data_get('raw_data')[included_chans] # (C, T)
    data_set('re-referenced_data', incl_data - np.mean(incl_data, axis=0))   


def build_filter():
    """ _ """
    band_type = cfg_get('band_type')
    filt_order = cfg_get('filter_order')
    filt_range = cfg_get('filter_range')
    fs = cfg_get('sample_rate')
    # If not using bandpass, filt_range is a single value
    filt_range = filt_range[1] if band_type == 'Lowpass' else \
                 filt_range[0] if band_type == 'Highpass' else \
                 filt_range
    if cfg_get('filter_type') == 'Butterworth':
        built_filter = butter(filt_order, filt_range, btype=band_type, 
                              analog=False, output='sos', fs=fs)
    else:  # filter_type == 'Bessel'
        built_filter = bessel(filt_order, filt_range, btype=band_type, 
                              analog=False, output='sos', fs=fs, norm='phase')
    data_set('filter', built_filter)
    sos = zpk2sos(*tf2zpk(*iirnotch(60, 30, fs=30000)))
    data_set('notch_sos', sos)


def filter_data():
    """ _ """
    # filters the CAR'd data
    data = data_get('re-referenced_data').T
    if cfg_get('notch_filter'):
        data = sosfiltfilt(data_get('notch_sos'), data, axis=0)
    data_set('filtered_data', sosfiltfilt(data_get('filter'), data, axis=0).T)


def set_threshold_crossings():
    """ _ """
    threshold_multiplier = cfg_get('threshold_mult')
    filtered_data = data_get('filtered_data')

    mask = np.ones(data_get('n_samples'), dtype=bool)
    if cfg_get('exclude_period'):
        start = int(cfg_get('spike_excl_start') * 30)
        end = int(cfg_get('spike_excl_end') * 30)
        mask[start:end] = False 
            
    # get threshold and crossings for each channel
    for idx, chan in data_get('included_chans_filtered'):
        # set the threshold
        filtered = filtered_data[idx]
        rms = np.sqrt(np.mean(filtered[mask] ** 2, axis=0))
        threshold = rms * threshold_multiplier
        data_set(f'thresholds_{chan}', threshold)
        # find the negative crossings
        cross = np.zeros_like(filtered)
        cross_init = (filtered[1:] < -threshold) & (filtered[:-1] >= -threshold) & mask[1:]
        cross[1:] = cross_init
        data_set(f'crossings_{chan}', np.where(cross)[0])

#------------------------------------------------------------------------------#
#                                  PLOT FUNCS                                  #
#------------------------------------------------------------------------------#

def refresh_plots(new_limits=None, filter_update=False, first_plot=False):
    """ _ """
    pause()
    if new_limits is None:
        waveform_type = cfg_get('waveform_type')
        def_chan = data_get(f'plotted_chans_{waveform_type.lower()}')[0][1]
        new_limits = dpg.get_axis_limits(f'xaxis_tag{def_chan}')

    if filter_update:
        car_data()
        build_filter()
        filter_data()

    buffer_handler(new_limits, first_plot)
    prepare_plots(first_plot)
    fit_y_axes(first_plot or filter_update)
    prepare_psd()
    set_threshold_crossings()
    prepare_spike_panels()
    plot_spikes()

    if first_plot:
        prepare_impedance_heatmap()
        update_impedance_table()

    dpg.split_frame()
    prepare_time_controls(new_limits)
    align_channel_labels()
    unfreeze_x_axes()


def prepare_plots(first_plot=False):
    """ _ """
    # get the channels to plot
    colors = cfg_get('plot_colors')
    set_plot_heights(first_plot)
    waveform_type = cfg_get('waveform_type').lower()
    plotted_chans = data_get(f'plotted_chans_{waveform_type}')
    for idx, (data_idx, chan) in enumerate(plotted_chans):
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
            dpg.configure_item(f'include_{chan}', enabled=False)
        else:
            for text in [f'tab_ch{chan}', f'impedance_ch{chan}']:
                dpg.bind_item_theme(text, 'chan')
            for box in [f'include_{chan}', f'plot_{chan}']:
                dpg.set_value(box, value=True)
            dpg.configure_item(f'plot_{chan}', enabled=True)
            dpg.configure_item(f'include_{chan}', enabled=True)


def plot_spikes():
    """ _ """
    # should this be plot all at once or buffer like continuous data?
    for chan in range(cfg_get('max_amplif_channels')):
        if data_get('chan_info')[chan]['plot']:
            crossings = data_get(f'crossings_{chan}')
            dpg.configure_item(f'spikes_{chan}', show=True)
            y_vals = list(np.ones_like(crossings))
            dpg.set_value(f'spikes_{chan}', [list(crossings), y_vals])
        else:
            dpg.configure_item(f'spikes_{chan}', show=False)


def prepare_spike_panels(set_xaxis_limits=True):
    """ _ """
    # TODO: CLEAN UP
    start_range = max(0, cfg_get('spike_start') * 30)
    end_range = min(cfg_get('spike_end') * 30, data_get('n_samples'))
    electrode_mapping = cfg_get('electrode_mapping')
    filt_data = data_get('filtered_data')
    panel_range = cfg_get('spike_panel_range')
    plot_x = list(range(*panel_range))
    plot_x = np.array(plot_x) / 30
    included_chans = data_get('included_chans_filtered')
    panel_chan = cfg_get('spike_chan')
    idxs = {chan: idx for idx, chan in data_get('included_chans_filtered')}
    if panel_chan not in idxs:
        panel_chan = included_chans[0][1]
    chans_with_spikes = []
    spaces = " " * cfg_get("panel_label_spaces")
    total_spikes = 0
    for row in range(8):
        for col in range(4):
            chan = electrode_mapping[row][col]
            if chan == panel_chan:
                dpg.delete_item('spike_yaxis_tag', children_only=True)
                # get crossings less than spike_range[1] and greater than spike_range[0]
                crossings = data_get(f'crossings_{chan}')
                crossings = crossings[crossings < end_range]
                crossings = crossings[crossings > start_range]

                dpg.configure_item('spike_panel_plot', 
                                   label=f'Ch {chan:02d}  -  {len(crossings)} Spikes')

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

                y_range = ymax - ymin
                dpg.set_axis_limits('spike_yaxis_tag', 
                                    ymin - y_range * 0.05, 
                                    ymax + y_range * 0.05)
                if set_xaxis_limits:
                    dpg.set_axis_limits('spike_xaxis_tag', 
                                        panel_range[0]*1.2/30, 
                                        panel_range[1]*1.2/30)
                if cfg_get('show_thresholds'):
                    threshold = data_get(f'thresholds_{chan}')
                    dpg.add_line_series(label=' Threshold',
                                        tag='threshold_line',
                                        x=plot_x,
                                        y=[-threshold for _ in range(*panel_range)],
                                        parent='spike_yaxis_tag')
                    dpg.bind_item_theme(dpg.last_item(), 'white_bar')

            tag = f'panel_yaxis_row{row}_col{col}'
            dpg.delete_item(tag, children_only=True)
            if data_get('chan_info')[chan]['incl']:
                crossings = data_get(f'crossings_{chan}')
                crossings = crossings[crossings < end_range]
                crossings = crossings[crossings > start_range]

                dpg.configure_item(
                    f'spike_panel_row{row}_col{col}', 
                    label=f'Ch {chan:02d}  -  {str(len(crossings)) + " Spikes":<10}{spaces}')
                total_spikes += len(crossings)

                ymin = 1e10
                ymax = -1e10
                for cross in crossings:
                    color_idx = int((cross) / data_get("n_samples") * 256)
                    x_min = max(cross + panel_range[0], 0)
                    x_max = min(cross + panel_range[1], data_get('n_samples'))
                    padded = list(filt_data[idxs[chan], x_min:x_max])
                    
                    ymin = min((ymin, min(padded)))
                    ymax = max((ymax, max(padded)))
                    if len(plot_x) == len(padded):
                        dpg.add_line_series(x=plot_x,
                                            y=padded,
                                            parent=tag)
                        dpg.bind_item_theme(dpg.last_item(),
                                            f'custom_color_{color_idx}')
                if len(crossings) > 0:
                    chans_with_spikes.append(f'Ch {chan}')
                if cfg_get('show_thresholds'):
                    threshold = data_get(f'thresholds_{chan}')
                    dpg.add_line_series(tag=f'threshold_line_{chan}',
                                        label='',
                                        x=plot_x,
                                        y=[-threshold for _ in range(*panel_range)],
                                        parent=tag)
                    dpg.bind_item_theme(dpg.last_item(), 'white_bar')
                dpg.set_axis_limits(tag, ymin*1.1, ymax*1.1)
                if set_xaxis_limits:
                    dpg.set_axis_limits(f'panel_xaxis_row{row}_col{col}',
                                    panel_range[0]/30, 
                                    panel_range[1]/30)
            else:
                dpg.configure_item(f'spike_panel_row{row}_col{col}', 
                                   label=f'Ch {chan:02d}{" " * 15}{spaces}')
    # spike_panels_subplot
    dpg.set_value('spike_panels_subplot_label', f'Total Spikes: {total_spikes}')
    chans_with_spikes = sorted(chans_with_spikes, key=lambda x: int(x.split(' ')[1]))
    dpg.configure_item('spk_sco_ch', items=chans_with_spikes, default_value=f'Ch {panel_chan}')


def prepare_impedance_heatmap():
    """ _ """
    values = []
    min_sc = 400
    max_sc = 2000 # considering over 2MOhms to be bad
    color_range = max_sc - min_sc
    start_x = 0.125
    start_y = 0.94
    gap_width = 0.25
    gap_height = 0.125
    dpg.configure_item('colormap_scale', min_scale=min_sc, max_scale=max_sc)
    for row in range(8):
        for col in range(4):
            ch_idx = cfg_get('electrode_mapping')[row][col]
            color_val = data_get('impedances')[ch_idx] / 1000
            values.append(color_val)
            color_val = max(min_sc, min(color_val, max_sc))
            color_val = (color_val - min_sc) / color_range
            color_int = int(color_val * 255)
            color = list((np.array(dpg.get_colormap_color(
                'jet_colormap',
                color_int,
            )) * 255).astype(int))
            imp= data["impedances"][ch_idx] / 1000
            dpg.add_plot_annotation(
                color=color,
                parent='imp_heatmap',
                default_value=(start_x + (col * gap_width), 
                               start_y - (row * gap_height)),
                label=f'Ch {ch_idx:02d}\n{" " if imp < 1000 else ""}{imp:,.0f}')
    dpg.add_heat_series(values, 
                        rows=8, cols=4, 
                        scale_min=min_sc, 
                        scale_max=2000,
                        format="",
                        parent='imp_plot_yaxis')


def prepare_psd():
    """ _ """
    labels = ['Raw', 'CAR', 'Filtered']
    signals = [data_get(k).T for k in ['raw_data', 
                                       're-referenced_data', 
                                       'filtered_data'] ]

    # calculate the PSD
    n_bins = cfg_get('sample_rate') // 2 + 1
    freqs, S = [], []
    for s, l in zip(signals, labels):
        nch = s.shape[1]
        f, p = np.zeros((n_bins, nch)), np.zeros((n_bins, nch))
        for ich in range(nch):
            f[:, ich], p[:, ich] = signal.welch(s[:, ich], 
                                                fs=cfg_get('sample_rate'), 
                                                nperseg=cfg_get('sample_rate'))
        S.append(p)
        freqs.append(f)
    p_max = np.max(p.mean(axis=1)[0:15000])
    for f, p, l in zip(freqs, S, labels):
        dpg.set_value(f'psd_{l}', [f.mean(axis=1)[0:15000], 
                                   p.mean(axis=1)[0:15000]])
    dpg.set_axis_limits('psd_yaxis_tag', -10000, p_max * 10)
    dpg.set_axis_limits('psd_xaxis_tag', -50, 1500)


def align_channel_labels():
    """ _ """
    for channel_type in ['amplif', 'analog']:
        analog = channel_type == 'analog'
        prefix = 'a_' if analog else ''
        if not analog or data_get(f'{channel_type}_data') is not None:
            for chan in range(cfg_get(f'max_{channel_type}_channels')):
                if data_get('chan_info')[chan]['plot'] or analog:
                    dpg.show_item(f'{prefix}ch{chan}')
                    x_pos, y_pos = dpg.get_item_pos(f'{prefix}plot{chan}')
                    plot_height = cfg_get(f'{channel_type}_plot_heights')
                    dpg.set_item_pos(f'{prefix}ch{chan}', 
                                     [10, y_pos + plot_height / 2 - 14])
                else:
                    dpg.hide_item(f'{prefix}ch{chan}')


def plot_data(plot_range, play=False):
    """ _ """
    n_colors = len(cfg_get('plot_colors'))
    waveform_type = cfg_get('waveform_type').lower()
    data = data_get(f'{waveform_type}_data')[:, plot_range[0]:plot_range[1]]

    for idx, chan in data_get(f'plotted_chans_{waveform_type}'):
        ch_tag = f'{waveform_type}_data_{chan}'
        ch_data = [list(range(*plot_range)), list(data[idx])]
        if play:
            dpg.delete_item(ch_tag)
            dpg.add_line_series(*ch_data, tag=ch_tag, parent=f'yaxis_tag{chan}')
            dpg.bind_item_theme(ch_tag, f'color_{idx % n_colors}')
        else:
            dpg.set_value(ch_tag, ch_data)
    if data_get('analog_data') is not None:
        data = data_get('analog_data')[:, plot_range[0]:plot_range[1]]
        for chan in range(cfg_get('max_analog_channels')):
            ch_tag = f'analog_data_{chan}'
            ch_data = [list(range(*plot_range)), list(data[chan])]
            if play:
                dpg.delete_item(ch_tag)
                dpg.add_line_series(*ch_data, tag=ch_tag, 
                                    parent=f'a_yaxis_tag{chan}')
                dpg.bind_item_theme(ch_tag, f'color_{chan % n_colors}')

            else:
                dpg.set_value(ch_tag, ch_data)
    if play:
        dpg.set_axis_limits('xaxis_label_tag', *[i // 30 for i in plot_range])
        prepare_time_controls(plot_range)


def get_play_limits(last_update_time, current_time):
    """ _ """
    n_samples = data_get('n_samples')
    play_speed = float(cfg_get('play_speed').split('x')[0])
    waveform_type = cfg_get('waveform_type').lower()
    plotted_chans = data_get(f'plotted_chans_{waveform_type}')
    current_limit = dpg.get_axis_limits(f'xaxis_tag{plotted_chans[0][1]}')
    current_limit = (max(current_limit[0], 0), min(current_limit[1], n_samples))
    lim_range = current_limit[1] - current_limit[0]

    elapsed_time = current_time - last_update_time
    # new_samples = 100
    new_samples = int(elapsed_time * cfg_get('sample_rate') * play_speed)
    new_start = current_limit[0] + new_samples

    # if playing past the end
    if new_start > data_get('n_samples') - lim_range:
        cfg_set('paused', True)
        dpg.configure_item(
            'pause_bt', enabled=False, texture_tag='pause_disabled_texture')
        dpg.configure_item('play_bt', enabled=True, texture_tag='play_texture')
        return int(current_limit[0]), int(current_limit[1])
    
    new_end = new_start + lim_range
    return int(new_start), int(new_end)


def align_axes(sender, new_limits, first_plot=False):
    """ _ """
    visible_range = cfg_get('visible_range')
    if visible_range == new_limits: return
    buffer_handler(new_limits, first_plot=first_plot)

    if sender == 'amplif_plots_group':
        # align analog plots, time axis, and time controls
        if data_get('analog_data') is not None:
            dpg.set_axis_limits(f'a_xaxis_tag0', *new_limits)
        dpg.set_axis_limits('xaxis_label_tag', *[i // 30 for i in new_limits])
        prepare_time_controls(new_limits)

    elif sender == 'analog_plots_group':
        # align amplif plots, time axis, and time controls
        waveform_type = cfg_get('waveform_type').lower()
        plotted_chans = data_get(f'plotted_chans_{waveform_type}')
        dpg.set_axis_limits(f'xaxis_tag{plotted_chans[0][1]}', *new_limits)
        dpg.set_axis_limits('xaxis_label_tag', *[i // 30 for i in new_limits])
        prepare_time_controls(new_limits)

    else:
        # align amplif plots and analog plots, and time axis
        waveform_type = cfg_get('waveform_type').lower()
        plotted_chans = data_get(f'plotted_chans_{waveform_type}')
        dpg.set_axis_limits(f'xaxis_tag{plotted_chans[0][1]}', *new_limits)
        if data_get('analog_data') is not None:
            dpg.set_axis_limits(f'a_xaxis_tag0', *new_limits)
        dpg.set_axis_limits('xaxis_label_tag', *[i // 30 for i in new_limits])
        prepare_time_controls(new_limits)


def unfreeze_x_axes():
    """ _ """
    for chan in range(cfg_get('max_amplif_channels')):
        dpg.set_axis_limits_auto(f'xaxis_tag{chan}')
    if data_get('analog_data') is not None:
        for chan in range(cfg_get('max_analog_channels')):
            dpg.set_axis_limits_auto(f'a_xaxis_tag{chan}')
    dpg.set_axis_limits_auto('psd_xaxis_tag')
    dpg.set_axis_limits_auto('spike_xaxis_tag')


def fit_y_axes(first_plot=False):
    """ _ """
    alpha = cfg_get('y_fit_alpha')
    visible_range = cfg_get('visible_range')
    waveform_type = cfg_get('waveform_type').lower()
    plotted_chans = data_get(f'plotted_chans_{waveform_type}')

    new_history = []
    plotted_data = []
    if not first_plot:
        visible_range = dpg.get_axis_limits(f'xaxis_tag{plotted_chans[0][1]}')
        prev_limits = np.array(cfg_get('y_lim_history')) * alpha
    data = data_get(f'{waveform_type}_data')
    visible_range = max(visible_range[0], 0), min(visible_range[1], data.shape[1])
    data = data[:, int(visible_range[0]):int(visible_range[1])]
    new_limits = np.concatenate((np.min(data, axis=1, keepdims=True), 
                                 np.max(data, axis=1, keepdims=True)), 1)
    new_limits = new_limits * (1 if first_plot else 1 - alpha)

    ideal_size = len(plotted_chans)
    if data_get('analog_data') is not None:
        ideal_size += cfg_get('max_analog_channels')
    if not first_plot and len(prev_limits) != ideal_size:
        prev_limits = np.zeros((ideal_size, 2))

    for idx, (data_idx, chan) in enumerate(plotted_chans):
        p_lims = prev_limits[idx] if not first_plot else 0
        smooth_limits = p_lims + new_limits[data_idx]
        new_history.append(smooth_limits)
        dpg.set_axis_limits(f'yaxis_tag{chan}', *smooth_limits)

    if data_get('analog_data') is not None:
        data = data_get('analog_data')
        data = data[:, int(visible_range[0]):int(visible_range[1])]
        new_limits = np.concatenate((np.min(data, axis=1, keepdims=True), 
                                     np.max(data, axis=1, keepdims=True)), 1)
        new_limits = new_limits * (1 if first_plot else 1 - alpha)
        n_amp_chans = len(plotted_chans)
        for chan in range(cfg_get('max_analog_channels')):
            p_lims = prev_limits[chan + n_amp_chans] if not first_plot else 0
            smooth_limits = p_lims + new_limits[chan]
            new_history.append(smooth_limits)
            dpg.set_axis_limits(f'a_yaxis_tag{chan}', *smooth_limits)
    cfg_set('y_lim_history', new_history)


def set_plot_heights(first_plot=False, resizing=False):
    """ _ """
    # SHOULD SPLIT FRAME AFTER THIS AND ALIGN CHANNEL LABELS
    
    if data_get('analog_data') is None:
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
            # spk_plt_height = cfg_get('show_spikes') * 0.1
            # height_ratios.extend([1 - spk_plt_height, spk_plt_height])
            if cfg_get('show_spikes'):
                height_ratios.extend([0.9, 0.1])
                dpg.configure_item(f'spikes_{chan}', show=True)
            else:
                height_ratios.extend([1, 0])
                dpg.configure_item(f'spikes_{chan}', show=False)
            
            # only show selected waveform type
            for waveform in ['raw', 'filtered', 're-referenced']:
                dpg.configure_item(f'{waveform}_data_{chan}', show=(
                                   cfg["waveform_type"].lower() == waveform))
        else:
            # if channel is not plotted, set height to 0                
            height_ratios.extend([0, 0])
            
    n_ch_to_plot = len(chans_to_plot)
    na_ch_to_plot = cfg_get('max_analog_channels')
    plot_heights = cfg_get('amplif_plot_heights')
    a_plot_heights = cfg_get('analog_plot_heights')

    # resize the amplif plots to match the new number of channels
    if first_plot or resizing:
        # if first plot and def height is small overwrite it
        min_height = cfg_get('amplif_plots_height') / n_ch_to_plot
        if plot_heights < min_height or resizing:
            cfg_set('amplif_plot_heights', min_height)
            dpg.set_value('amplif_heights_input', min_height)
            plot_heights = min_height
        a_min_height = cfg_get('analog_plots_height') / na_ch_to_plot
        if a_plot_heights < a_min_height or resizing:
            cfg_set('analog_plot_heights', a_min_height)
            dpg.set_value('analog_heights_input', a_min_height)
            a_plot_heights = a_min_height
        
    dpg.configure_item('amplif_plots', 
                       height=plot_heights * n_ch_to_plot,
                       row_ratios=height_ratios)
    dpg.configure_item('analog_plots', height=a_plot_heights * na_ch_to_plot)


def buffer_handler(new_limits, first_plot=False):
    """ _ """
    # compares the visible limits to the new_limits (from zooming or dragging)
    # checks if new limits go beyond the buffer, redraws buffer if so
    visible_range = cfg_get('visible_range')
    # get the buffer and view limits
    buffer = int((visible_range[1] - visible_range[0]) * cfg_get('buffer_mult'))
    view_limit = buffer * 0.5

    # if the new limits are outside of the first 25% of the buffer, redraw
    if (new_limits[0] < visible_range[0] - view_limit or \
        new_limits[1] > visible_range[1] + view_limit or \
        first_plot
    ):
        plot_range = (int(max(new_limits[0] - buffer, 0)), 
                      int(min(new_limits[1] + buffer, data_get('n_samples'))))
        cfg_set('visible_range', new_limits)
        plot_data(plot_range)

#------------------------------------------------------------------------------#
#                                   UI FUNCS                                   #
#------------------------------------------------------------------------------#

def pause(sender=None, app_data=None, user_data=None):
    cfg_set('paused', True)
    dpg.configure_item(
        'pause_bt', enabled=False, texture_tag='pause_disabled_texture')
    dpg.configure_item('play_bt', enabled=True, texture_tag='play_texture')


def get_max_viewport_size():
    """Retrieve the max viewport height and width in pixels."""
    # start the render loop and get the viewport size
    if dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
        viewport_height = dpg.get_viewport_height()
        viewport_width = dpg.get_viewport_width()
        dpg.render_dearpygui_frame()
    return viewport_height, viewport_width


def prepare_time_controls(limits):
    """ _ """
    limits = max(limits[0], 0), min(limits[1], data_get('n_samples'))
    n_samples = data_get('n_samples')
    _, full_m, full_s = sec_to_hms(n_samples / cfg_get('sample_rate'))
    _, start_m, start_s = sec_to_hms(limits[0] / cfg_get('sample_rate'))
    # set elapsed / full time text
    dpg.set_value('time_text', 
                  f'{start_m:02d}:{start_s:02d}/{full_m:02d}:{full_s:02d}')
                #   f'{start_m:02d}:{start_s:02d} / {full_m:02d}:{full_s:02d}')

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
            dpg.configure_item(f'skip_{dir}_bt', 
                               texture_tag=texture, 
                               enabled=enabled)

#------------------------------------------------------------------------------#
#                                  ETC FUNCS                                   #
#------------------------------------------------------------------------------#

def sec_to_hms(total_secs):
    """Convert seconds to a tuple of hours, minutes, and seconds."""
    hours, remainder = divmod(int(total_secs), 3600)
    minutes, seconds = divmod(remainder, 60)
    return hours, minutes, seconds


def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('./resources')
    return os.path.join(base_path, relative_path)


def get_screen_size():
    """ Retrieve the screens height and width in pixels """
    # create a temporary tkinter root window
    root = tk.Tk()  
    # get screen height and width
    screen_height = root.winfo_screenheight()  
    screen_width = root.winfo_screenwidth()  
    # close the temporary window
    root.destroy() 
    return screen_height, int(screen_width)


def adjust_color(rgb_colors, brightness_factor, saturation_factor):
    """ Function to adjust the brightness and saturation of colors """
    # convert RGB colors to HSV
    hsv_colors = rgb_to_hsv(rgb_colors)
    # adjust brightness (value) and saturation
    hsv_colors[:, 1] *= saturation_factor
    hsv_colors[:, 2] *= brightness_factor
    # make sure no value exceeds 1.0
    hsv_colors[hsv_colors > 1.0] = 1.0
    # convert back to RGB
    adjusted_rgb_colors = hsv_to_rgb(hsv_colors)
    # normalize the adjusted colors to the range of 0 to 255 for display
    adjusted_rgb_colors_scaled = [(int(r*255), int(g*255), int(b*255), 255) \
                                  for r, g, b in adjusted_rgb_colors]
    return adjusted_rgb_colors_scaled

#------------------------------------------------------------------------------#

















