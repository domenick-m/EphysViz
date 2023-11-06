import dearpygui.dearpygui as dpg
from util_funcs import *
import numpy as np
from intanutil.read_data import read_data
from scipy.signal import iirnotch

# create dictionaries to store configs and the data
cfg, data = {}, {}
data['chan_info'] = {}
cfg['app_name'] = 'EphysViz'
cfg['max_amplif_channels'] = 32 # NeuroNexus
cfg['max_analog_channels'] = 2 # EKG
cfg['sample_rate'] = 30000 # Hz
cfg['screen_height'], cfg['screen_width']  = get_screen_size()

# load default configs from settings.ini
cfg['amplif_plot_heights'] = read_settings(
    'defaults', 'amplif_plot_heights', 25
)
cfg['analog_plot_heights'] = read_settings(
    'defaults', 'analog_plot_heights', 60
)
cfg['impedance_threshold'] = read_settings(
    'defaults', 'impedance_threshold', 5000
)
cfg['path'] = read_settings('defaults', 'path', os.path.expanduser('~'))
cfg['filter_type'] = read_settings('defaults', 'filter_type', 'Butterworth')
cfg['band_type'] = read_settings('defaults', 'band_type', 'Bandpass')
cfg['filter_order'] = read_settings('defaults', 'filter_order', 4)
cfg['filter_range'] = read_settings('defaults', 'filter_range', (250, 3000))
cfg['notch_filter'] = read_settings('defaults', 'notch_filter', True)
cfg['show_spikes'] = read_settings('defaults', 'show_spikes', False)
cfg['waveform_type'] = read_settings('defaults', 'waveform_type', 'Filtered')

# create filters
notch_sos = zpk2sos(*tf2zpk(*iirnotch(60, 30, fs=cfg['sample_rate'])))
filter = build_filter(
    cfg['filter_type'], cfg['band_type'], 
    cfg['filter_order'], cfg['filter_range'], cfg['sample_rate']
)

# create a dearpygui context
dpg.create_context()

# create a viewport (base window) that fills up the entire screen
dpg.create_viewport(
    title='EphysViz',
    x_pos=0, y_pos=0, 
    height=cfg['screen_height'],  
    width=cfg['screen_width'],
)

# setup dearpygui and show the viewport
dpg.setup_dearpygui()
dpg.show_viewport()

# get the maximum allowed viewport size
cfg['viewport_height'], cfg['viewport_width'] = get_max_viewport_size()

#------------------------------------------------------------------------------#
#  MENU BAR                                                                    #
#--------------------------------------------------------#---------------------#
#  PLOT CONTROL BAR                                      | TAB BARS            #
#--------------------------------------------------------#---------------------#
#  SUBPLOTS                                              |                     #
#                                                        |                     #
#          AMPLIFIER CHANNELS                            |                     #
#                                                        |                     #
#                                                        |                     #
#                                                        |                     #
#                                                        |                     #
#                                                        |                     #
#          ANALOG CHANNELS                               |                     #
#                                                        |                     #
#                      X-AXIS LABEL                      |                     #
#--------------------------------------------------------#---------------------#
#  TIME CONTROL BAR                                      |                     #
#--------------------------------------------------------#---------------------#

# add plot parameters to the config
cfg['num_ticks'] = 11
cfg['buffer_mult'] = 0.5 # axis range * this mult = unseen buffer
cfg['menu_bar_height'] = 26
cfg['visible_range'] = 0, 20000 # 30kHz samples (0.66s)
cfg['time_controls_height'] = 70
cfg['channel_labels_width'] = 200
cfg['plot_cntrl_bar_height'] = 50
cfg['plots_window_width'] = cfg['viewport_width'] * 0.75
cfg['tabs_window_width'] = cfg['viewport_width'] * 0.25
cfg['bar_heights'] = (
    cfg['menu_bar_height'] + 
    cfg['time_controls_height'] + 
    cfg['plot_cntrl_bar_height']
)
cfg['subplots_height'] = cfg['viewport_height'] - cfg['bar_heights']
cfg['amplif_plots_height'] = cfg['subplots_height'] * 0.9
cfg['analog_plots_height'] = cfg['subplots_height'] * 0.1
cfg['subplots_width'] = cfg['plots_window_width'] - cfg['channel_labels_width']
cfg['amplif_plot_heights'] = max(
    int(cfg['amplif_plots_height'] / cfg['max_amplif_channels']),
    cfg['amplif_plot_heights']
)
cfg['analog_plot_heights'] = max(
    int(cfg['analog_plots_height'] / cfg['max_analog_channels']),
    cfg['analog_plot_heights']
)

# set the default font
with dpg.font_registry():
    default_font = dpg.add_font(resource_path('SF-Mono-Light.otf'), 21)
dpg.bind_font(default_font)


# ------ THEMES ------ #

# Tab10 (no grey)
colors = [
    [31, 119, 180],  # Blue
    [255, 127, 14],  # Orange
    [44, 160, 44],   # Green
    [214, 39, 40],   # Red
    [148, 103, 189], # Purple
    [140, 86, 75],   # Brown
    [227, 119, 194], # Pink
    [188, 189, 34],  # Olive
    [23, 190, 207]   # Cyan
]

# create a default theme with the style editor!

for idx, color in enumerate(colors):
    with dpg.theme(tag=f'color_{idx}'):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)

with dpg.theme(tag='test'):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 1, 1)
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding, 0, 0, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize, 0, category=dpg.mvThemeCat_Plots)


# ------ TEXTURE LOADING ------ #

icon_names = [
    'play', 'play_disabled', 'pause', 'pause_disabled',
    'skip_left', 'skip_left_disabled', 'skip_right', 'skip_right_disabled', 
]

for name in icon_names:
    _, _, _, im_data = dpg.load_image(resource_path(f"{name}.png"))
    with dpg.texture_registry(show=False):
        dpg.add_static_texture(
            height=20, width=20, 
            default_value=im_data, 
            tag=f"{name}_texture"
        )

# ------ WINDOWS ------ #

#   -- MENU BAR
with dpg.viewport_menu_bar(tag='menu_bar', show=False):
    dpg.add_spacer(height=100)
    with dpg.menu(label="File"):
        dpg.add_spacer(height=100)
        dpg.add_menu_item(
            label="Open...", 
            callback=lambda: dpg.show_item("file_dialog")
        )
        dpg.add_menu_item(
            label="Save Settings as Default", 
            callback=lambda: print("Save Clicked")
        )
        dpg.add_menu_item(
            label="Set Default Directory", 
            callback=lambda: dpg.show_item("dir_dialog")
        )
        dpg.add_menu_item(
            label="Edit Electrode Mapping", 
            callback=lambda: dpg.show_item("mapping_settings")
        )
    dpg.add_spacer(height=100)


#   -- ELECTRODE MAPPING SETTINGS
# callback on enter press
def mapping_change_cb(sender, app_data, user_data):
    prev_chan = sender.split('_')[0][2:]
    prev_sender_value = read_settings('mapping', sender, prev_chan)
    for chan in range(cfg['max_amplif_channels']):
        old_parent = f'ch{chan}_mapping'
        if int(read_settings('mapping', old_parent, chan)) == int(app_data):
            write_settings('mapping', old_parent, prev_sender_value)
            dpg.set_value(old_parent, f'{int(prev_sender_value):02d}')
            break
    write_settings('mapping', sender, app_data)
    dpg.set_value(sender, f'{int(app_data):02d}')

# create a window for electrode mapping settings
win_width = 400
win_height = cfg['viewport_height'] * 0.8
pos = [
    (cfg['viewport_width'] - win_width) / 2 , 
    (cfg['viewport_height'] - win_height) / 2
]
with dpg.window(
    label='Electrode Mapping Settings',
    tag='mapping_settings', 
    pos=pos, show=False, 
    height=win_height, width=win_width,
    no_collapse=True, no_resize=True, no_move=True,
    modal=True,
):
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=20)
        dpg.add_text('Intan')
        dpg.add_spacer(width=140)
        dpg.add_text('NeuroNexus')
    dpg.add_spacer(height=2)
    for chan in range(cfg['max_amplif_channels']):
        tag = f'ch{chan}_mapping'
        neuronex_ch = int(read_settings('mapping', tag, chan))
        dpg.add_spacer(height=5)
        with dpg.group(horizontal=True):
            dpg.add_text(f'Channel {chan:02d}')
            dpg.add_spacer(width=30)
            dpg.add_text('->')
            dpg.add_spacer(width=30)
            dpg.add_text('Channel')
            dpg.add_spacer(width=1)
            dpg.add_input_text(
                tag=tag,
                default_value=f'{neuronex_ch:02d}', 
                callback=mapping_change_cb,
                on_enter=True,
                width=50
            )


#   -- DIR SELECTION
# callback for the file dialog
def dir_dialog_cb(sender, app_data, user_data): 
    selected_dir = os.path.dirname(list(app_data['selections'].values())[0])
    write_settings('defaults', 'path', selected_dir)

# create a directory selection dialog
dpg.add_file_dialog(
    tag='dir_dialog',
    label='Select default directory...',
    show=False, modal=True,
    directory_selector=True,
    height=cfg['viewport_height'] * 0.65,
    width=cfg['viewport_width'] * 0.5,
    callback=dir_dialog_cb,
    default_path=read_settings('defaults', 'path', os.path.expanduser('~')),
)


#   -- FILE SELECTION
# callback for the file dialog
def file_dialog_cb(sender, app_data, user_data):
    global data, cfg

    dpg.hide_item("plots_window")
    dpg.hide_item("tabs_window")
    dpg.show_item("loading_indicator")

    # with dpg.mutex():

    # LOAD IN DATA
    rhs_data = read_data(list(app_data['selections'].values())[0])

    data['raw_data'] = rhs_data['amplifier_data']
    data['analog_data'] = rhs_data['board_adc_data']
    print(data['raw_data'].shape, data['analog_data'].shape)
    channel_info = rhs_data['amplifier_channels']
    data['impedances'] = [
        chan['electrode_impedance_magnitude'] for chan in channel_info
    ]
    for chan in range(cfg['max_amplif_channels']):
        if data['impedances'][chan] > cfg['impedance_threshold'] * 1000:
            data['chan_info'][chan] = {'plot':False, 'incl':False}
        else:
            data['chan_info'][chan] = {'plot':True, 'incl':True}
    data['n_samples'] = data['raw_data'].shape[1]

    # CAR the data (included channels only)
    chans_to_car = [
        chan for chan in range(cfg['max_amplif_channels']) \
        if data['chan_info'][chan]['incl']
    ]
    car = np.mean(data['raw_data'][chans_to_car], axis=0)
    data['car_data'] = data['raw_data'][chans_to_car] - car

    # filter the data
    data['filtered_data'] = filter_data(
        data['car_data'], 
        filter, 
        notch_sos=notch_sos if cfg['notch_filter'] else None
    )

    # create buffered data
    vis_range = cfg['visible_range'][1] - cfg['visible_range'][0]
    buffer = vis_range * cfg['buffer_mult']
    plotted_range = (
        int(max(cfg['visible_range'][0] - buffer, 0)), 
        int(min(cfg['visible_range'][1] + buffer, data['n_samples']))
    )

    # add raw data to the plot
    for chan in range(cfg['max_amplif_channels']):
        dpg.add_line_series(
            tag=f'raw_data_{chan}',
            x=list(range(*plotted_range)),
            y=data['raw_data'][chan, plotted_range[0]:plotted_range[1]],
            parent=f'yaxis_tag{chan}',
            show=False,
        )
    
    # add car data to the plot
    for idx, chan in enumerate(chans_to_car):
        dpg.add_line_series(
            tag=f're-referenced_data_{chan}',
            x=list(range(*plotted_range)),
            y=data['car_data'][idx, plotted_range[0]:plotted_range[1]],
            parent=f'yaxis_tag{chan}',
            show=False,
        )

    # # add filtered data to the plot
    for idx, chan in enumerate(chans_to_car):
        dpg.add_line_series(
            tag=f'filtered_data_{chan}',
            x=list(range(*plotted_range)),
            y=list(data['filtered_data'][idx, plotted_range[0]:plotted_range[1]]),
            parent=f'yaxis_tag{chan}',
            show=False,
        )

    # # add filtered data to the plot
    for chan in range(cfg['max_analog_channels']):
        dpg.add_line_series(
            tag=f'analog_data_{chan}',
            x=list(range(*plotted_range)),
            y=list(data['analog_data'][chan, plotted_range[0]:plotted_range[1]]),
            parent=f'a_yaxis_tag{chan}',
            show=True,
        )

    # prepare the plots (hide invisible channels, set axis limits, set colors)
    cfg = prepare_plots(cfg, data, colors)

    dpg.hide_item("loading_indicator")
    dpg.show_item("plots_window")
    dpg.show_item("tabs_window")

    # align the channel labels to the plots
    dpg.split_frame()
    with dpg.mutex():
        for pre, ran, ph in zip(
            ['', 'a_'], 
            [cfg['max_amplif_channels'], cfg['max_analog_channels']],
            [cfg['amplif_plot_heights'], cfg['analog_plot_heights']]
        ):
            for chan in range(ran):
                x_pos, y_pos = dpg.get_item_pos(f'{pre}plot{chan}')
                extra = 43 if pre == 'a_' else 0
                dpg.set_item_pos(
                    f'{pre}ch{chan}', 
                    [x_pos - 60 - extra, y_pos + ph / 2 - 14]
                )
    # allow dragging / scrolling
    for chan in range(cfg['max_amplif_channels']):
        dpg.set_axis_limits_auto(f'xaxis_tag{chan}')
        dpg.set_axis_limits_auto(f'yaxis_tag{chan}')
        dpg.fit_axis_data(f'yaxis_tag{chan}')

    for chan in range(cfg['max_analog_channels']):
        dpg.set_axis_limits_auto(f'a_xaxis_tag{chan}')
        dpg.set_axis_limits_auto(f'a_yaxis_tag{chan}')
        dpg.fit_axis_data(f'a_yaxis_tag{chan}')

# create a .RHS file selection dialog (visisble by default)
with dpg.file_dialog(
    tag='file_dialog', 
    label='Select file to open...', 
    show=True, modal=True,
    directory_selector=False, 
    height=cfg['viewport_height'] * 0.65, 
    width=cfg['viewport_width'] * 0.5,
    callback=file_dialog_cb, 
    default_path=read_settings('defaults', 'path', os.path.expanduser('~'))
):
    dpg.add_file_extension('.rhs', color=(0, 255, 0, 255))
    dpg.add_file_extension('.RHS', color=(0, 255, 0, 255))


#   -- LOADING INDICATOR
pos = [cfg['viewport_width'] / 2 - 140, cfg['viewport_height'] / 2 - 110,]
with dpg.window(tag='loading_indicator', pos=pos, show=False, no_collapse=True):
    dpg.add_spacer(height=5)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=20)
        dpg.add_loading_indicator()
        dpg.add_spacer(width=5)
        with dpg.group():
            dpg.add_spacer(height=11)
            dpg.add_text('Loading...')
        dpg.add_spacer(width=40)
    dpg.add_spacer(height=5)


#   -- PLOTS WINDOW
def plot_type_cb(sender, app_data, user_data):
    print(sender, app_data, user_data)

def toggle_spikes_cb(sender, app_data, user_data):
    dpg.configure_item(
        'amplif_plots', 
        height=cfg['amplif_plot_heights'] * cfg['max_amplif_channels'] * (1.5 if app_data else 1),
        row_ratios=[1, 0.5 if app_data else 0] * cfg['max_amplif_channels'],
    )
    dpg.split_frame()
    for chan in range(cfg['max_amplif_channels']):
        o_x_pos, _ = dpg.get_item_pos(f'ch{chan}')
        _, y_pos = dpg.get_item_pos(f'plot{chan}')
        dpg.set_item_pos(
            f'ch{chan}', 
            [o_x_pos, y_pos + cfg['amplif_plot_heights'] / 2 - 14]
        )

def amplif_height_cb(sender, app_data, user_data):
    if app_data > int(cfg['amplif_plots_height'] / cfg['max_amplif_channels']):
        # for chan in range(cfg['max_amplif_channels']):
        #     dpg.set_item_height(f'plot{chan}', app_data)
        dpg.configure_item('amplif_plots', height=app_data * cfg['max_amplif_channels'])
        dpg.split_frame()
        for chan in range(cfg['max_amplif_channels']):
            o_x_pos, _ = dpg.get_item_pos(f'ch{chan}')
            _, y_pos = dpg.get_item_pos(f'plot{chan}')
            dpg.set_item_pos(
                f'ch{chan}', 
                [o_x_pos, y_pos + app_data / 2 - 14]
            )

def analog_height_cb(sender, app_data, user_data):
    if app_data > int(cfg['amplif_plots_height'] / cfg['max_analog_channels']):
        for chan in range(cfg['max_analog_channels']):
            dpg.set_item_height(f'a_plot{chan}', app_data)
        dpg.configure_item('analog_plots', height=app_data * cfg['max_analog_channels'])
        dpg.split_frame()
        for chan in range(cfg['max_analog_channels']):
            o_x_pos, _ = dpg.get_item_pos(f'a_ch{chan}')
            _, y_pos = dpg.get_item_pos(f'a_plot{chan}')
            dpg.set_item_pos(f'a_ch{chan}', [o_x_pos, y_pos + app_data / 2 - 14])

locs = {i:None for i in range(cfg['max_amplif_channels'])}
def query_cb(sender, app_data, user_data):
    global locs
    i = sender.split('plot')[1]
    if app_data != locs[int(i)]:
        dpg.configure_item(
            f'query_text{i}', 
            show=True,
            default_value=(app_data[1], app_data[3]),
        )
        locs[int(i)] = app_data

    # dpg.split_frame()
    # if not dpg.is_plot_queried(sender):
    #     dpg.configure_item(f'query_text{i}', show=False)
    # dpg.configure_item
        

with dpg.window(
    tag='plots_window',
    pos=[0, cfg['menu_bar_height']], 
    show=False,
    width=cfg['viewport_width'], 
    height=cfg['viewport_height'] - cfg['menu_bar_height'],
    no_move=True, 
    no_close=True, 
    no_collapse=True, 
    no_title_bar=True, 
    no_bring_to_front_on_focus=True,
):
    #   -- PLOT CONTROLS BAR
    dpg.add_spacer(height=5)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=10)
        dpg.add_text("Plot Type:")
        dpg.add_combo( # dropdown
            items=["Raw", "Re-Referenced", "Filtered"], 
            enabled=True, 
            callback=plot_type_cb,
            default_value="Filtered", 
            width=180, 
        )
        dpg.add_spacer(width=30)
        dpg.add_text('Show Spikes:')
        dpg.add_checkbox(
            callback=toggle_spikes_cb, 
            default_value=read_settings('defaults', 'show_spikes', False)
        )
        dpg.add_spacer(width=(cfg['plots_window_width'] - 1300) * 1)
        dpg.add_text('Amp. Plot Heights:')
        dpg.add_input_int(
            callback=amplif_height_cb, 
            default_value=cfg['amplif_plot_heights'], 
            width=100
        )
        dpg.add_spacer(width=5)
        dpg.add_text('Analog Plot Heights:')
        dpg.add_input_int(
            callback=analog_height_cb, 
            default_value=cfg['analog_plot_heights'], 
            width=100
        )
    dpg.add_spacer(height=10)

    #   -- AMPLIFIER CHANNELS
    with dpg.child_window(
        tag='amplif_plots_child',
        height=cfg['amplif_plots_height'],
        width=cfg['plots_window_width'],
        no_scrollbar=True,
    ):
        with dpg.group(horizontal=True):
            #   -- CHANNEL LABELS
            dpg.add_spacer(width=10)
            with dpg.group():
                for chan in range(cfg['max_amplif_channels']):
                    dpg.add_spacer(height=cfg['subplots_height'] / cfg['max_amplif_channels'] * 0.3)
                    # chan = visible_chans[i]
                    dpg.add_text(f'Ch {chan:02d}', tag=f'ch{chan}')
                    dpg.bind_item_theme(f'ch{chan}', f'color_{chan % len(colors)}')

            #   -- SUBPLOTS
            with dpg.group(tag='amplif_plots_group'):
                show_spikes = read_settings('defaults', 'show_spikes', False)
                with dpg.subplots(
                    tag='amplif_plots',
                    rows=cfg['max_amplif_channels']*2,
                    columns=1,
                    width=cfg['subplots_width'],
                    height=cfg['amplif_plot_heights'] * cfg['max_amplif_channels'] * (1 + show_spikes),
                    row_ratios=[1, 0.2 if show_spikes else 0] * cfg['max_amplif_channels'],
                    link_columns=True,
                ):
                    for i in range(cfg['max_amplif_channels']):
                        with dpg.plot(
                            anti_aliased=False, 
                            no_mouse_pos=True, 
                            tag=f'plot{i}',
                            query=True,
                            callback=query_cb,
                        ):
                            dpg.add_plot_axis(
                                dpg.mvXAxis, 
                                tag=f'xaxis_tag{i}', 
                                no_gridlines=True, 
                                no_tick_marks=True, 
                                no_tick_labels=True
                            )
                            dpg.add_plot_axis(
                                dpg.mvYAxis, 
                                tag=f'yaxis_tag{i}', 
                                no_gridlines=True,
                                no_tick_marks=True, 
                                no_tick_labels=True,  
                                # lock_min=True, lock_max=True
                            )
                            dpg.add_plot_annotation(
                                tag=f'query_text{i}',
                                label="100ms", 
                                default_value=(1, 0), 
                                show=False,
                                # offset=(-15, 15), 
                                # color=[255, 255, 0, 255]
                            )
                        dpg.bind_item_theme(f'plot{i}', 'test', )
                        with dpg.plot(
                            anti_aliased=False, 
                            no_mouse_pos=True, 
                            tag=f'spk_plot{i}',
                        ):
                            dpg.add_plot_axis(
                                dpg.mvXAxis, 
                                tag=f'spk_xaxis_tag{i}', 
                                no_gridlines=True, 
                                no_tick_marks=True, 
                                no_tick_labels=True
                            )
                            dpg.add_plot_axis(
                                dpg.mvYAxis, 
                                tag=f'spk_yaxis_tag{i}', 
                                no_gridlines=True,
                                no_tick_marks=True, 
                                no_tick_labels=True,  
                                lock_min=True, lock_max=True
                            )
                        dpg.bind_item_theme(f'spk_plot{i}', 'test', )

                dpg.bind_item_theme('amplif_plots', 'subplots_theme')

    #   -- ANALOG CHANNELS
    with dpg.child_window(
        tag='analog_plots_child',
        height=cfg['analog_plots_height'],
        width=cfg['plots_window_width'],
        no_scrollbar=True,
    ):
        with dpg.group(horizontal=True):
            #   -- CHANNEL LABELS
            dpg.add_spacer(width=10)
            with dpg.group():
                for chan in range(cfg['max_analog_channels']):
                    dpg.add_text(f'Ch A-{chan:02d}', tag=f'a_ch{chan}')
                    dpg.bind_item_theme(f'a_ch{chan}', f'color_{chan % len(colors)}')

            #  -- SUBPLOTS
            with dpg.subplots(
                tag='analog_plots',
                rows=cfg['max_analog_channels'],
                columns=1,
                width=cfg['subplots_width'],
                height=cfg['analog_plot_heights'] * cfg['max_analog_channels'],
                link_columns=True,
            ):
                for i in range(cfg['max_analog_channels']):
                    with dpg.plot(
                        height=cfg['analog_plot_heights'], 
                        tag=f'a_plot{i}'
                    ):
                        dpg.add_plot_axis(
                            dpg.mvXAxis, 
                            tag=f'a_xaxis_tag{i}', 
                            show=True, 
                            no_gridlines=True, 
                            no_tick_marks=True, 
                            no_tick_labels=True
                        )
                        dpg.add_plot_axis(
                            dpg.mvYAxis, 
                            tag=f'a_yaxis_tag{i}', 
                            no_gridlines=True,  
                            no_tick_marks=True, 
                            no_tick_labels=True,  
                            # lock_min=True, lock_max=True
                        )
                    dpg.bind_item_theme(f'a_plot{i}', 'test', )
    #   -- ANALOG CHANNELS
    with dpg.plot(width=cfg['subplots_width']):
        dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, show=True, tag=f'xaxis_label_tag')
        x_min, x_max = 0, 10000
        dpg.set_axis_limits(dpg.last_item(), x_min, x_max)
        tick_values = np.linspace(x_min, x_max, cfg['num_ticks'])

        tick_labels = []
        for j, value in enumerate(tick_values):
            if j > 0 and (tick_values[j] - tick_values[j-1])/30 < 1: # When differences are less than 1ms,
                label = f"{value/30:.2f}" # format with two decimal places.
            else: # Otherwise, format as integer.
                label = str(int(value/30))
            tick_labels.append((label, value))
        dpg.set_axis_ticks(dpg.last_item(), tuple(tick_labels))

        dpg.add_plot_axis(dpg.mvYAxis, no_gridlines=True, no_tick_marks=True, tag=f'yaxis_label_tag', no_tick_labels=True, lock_min=True, lock_max=True)

    # x axis label
    # with dpg.group(horizontal=True):
    #     dpg.add_text("Time (ms)", tag='x_label')
    #     label_width = len("Time (ms)") * 8  # Assume each character is roughly 8 pixels wide
    #     x_position = (cfg['subplots_width'] - label_width) // 2
    #     dpg.set_item_pos('x_label', [x_position, cfg['subplots_height'] + 30])




def wheel_callback(sender, app_data, user_data):
    if dpg.is_item_hovered('amplif_plots_group'):
        for i in range(cfg['max_amplif_channels']):
            dpg.fit_axis_data(f'yaxis_tag{i}')

def left_click_drag_callback(sender, app_data, user_data):
    if dpg.is_item_hovered('amplif_plots_group'):
        # with dpg.mutex():
        for i in range(cfg['max_amplif_channels']):
            dpg.fit_axis_data(f'yaxis_tag{i}')
        x_min, x_max = dpg.get_axis_limits(f'xaxis_tag0')

        buffer = (cfg['visible_range'][1] - cfg['visible_range'][0]) * cfg['buffer_mult']
        if x_max > cfg['visible_range'][1] + buffer - (buffer * 0.25):
            cfg['visible_range'] = x_min, x_max
            plot_range = (
                int(max(cfg['visible_range'][0] - buffer, 0)), 
                int(cfg['visible_range'][1] + buffer)
            )
            for i in range(cfg['max_amplif_channels']):
                dpg.set_value(
                    f'{cfg["waveform_type"].lower()}_data_{i}',
                    [
                        list(range(*plot_range)),
                        list(data[f'{cfg["waveform_type"].lower()}_data'][i, plot_range[0]:plot_range[1]])
                    ]
                )

def remove_query_cb(sender, app_data, user_data):
    print(sender)

    # for i in range(cfg['max_amplif_channels']):
    #     dpg.configure_item(f'query_text{i}', show=False)


with dpg.handler_registry():
    dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Left, callback=left_click_drag_callback)
    dpg.add_mouse_wheel_handler(callback=wheel_callback)
    dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Middle, callback=remove_query_cb)

for i in range(cfg['max_amplif_channels']):
    with dpg.item_handler_registry(tag=f'plot{i}_handler') as handler_reg:
        dpg.add_item_clicked_handler(
            button=dpg.mvMouseButton_Middle, 
            callback=remove_query_cb, 
            tag=f'plot{i}_clicked_handler', 
        )
    dpg.bind_item_handler_registry(f'plot{i}', f'plot{i}_handler', )
                        
dpg.show_style_editor()
dpg.show_metrics()

#   -- TABS WINDOW
with dpg.window(
    tag='tabs_window',
    pos=[cfg['plots_window_width'], cfg['menu_bar_height']], 
    show=False,
    width=cfg['tabs_window_width'], 
    height=cfg['viewport_height'] - cfg['menu_bar_height'],
    no_move=True, 
    no_close=True, 
    no_collapse=True, 
    no_title_bar=True, 
):
    with dpg.tab_bar(tag='tab_bar') as tb:
        tabsize = cfg['tabs_window_width'] / 3
        letter_width = 11.5  

        # CHANNELS TAB
        centered_label = center_label("Channels", tabsize, letter_width)
        with dpg.tab(label=centered_label, tag='channels_tab'):
            dpg.add_spacer(height=10)

        # FILTERING TAB
        centered_label = center_label("Filtering", tabsize, letter_width)
        with dpg.tab(label=centered_label, tag='filtering_tab'):
            dpg.add_spacer(height=10)

        # SPIKES TAB
        centered_label = center_label("Spikes", tabsize, letter_width)
        with dpg.tab(label=centered_label, tag='spikes_tab'):
            dpg.add_spacer(height=10)
    

# ------ RENDER LOOP ------ #

# start the rendering loop
while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

# clean up
dpg.destroy_context()