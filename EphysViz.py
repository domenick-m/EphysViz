import timeit
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.signal import iirnotch
import dearpygui.dearpygui as dpg
from util_funcs import *
from callbacks import *
from globals import *

# set static configs
cfg_set('app_name', 'EphysViz')
cfg_set('max_amplif_channels', 32) # NeuroNexus
cfg_set('max_analog_channels', 2) # EKG
cfg_set('sample_rate', 30000) # Hz

# load default configs from settings.ini
load_defaults()

# create the filters according to the default configs
create_filters()

# create a dearpygui context
dpg.create_context()

# create a viewport (base window) that fills up the entire screen
screen_height, screen_width = get_screen_size()
dpg.create_viewport(
    title='EphysViz',
    x_pos=0, y_pos=0, 
    height=screen_height,  
    width=screen_width,
    vsync=True
)
dpg.set_viewport_vsync(False)

# setup dearpygui and show the viewport
dpg.setup_dearpygui()
dpg.show_viewport()

# get the maximum allowed viewport size
viewport_height, viewport_width = get_max_viewport_size()
cfg_set('viewport_height', viewport_height)
cfg_set('viewport_width', viewport_width)

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
cfg_set('num_ticks', 11)
cfg_set('buffer_mult', 0.5) # axis range * this mult = unseen buffer
cfg_set('menu_bar_height', 26)
cfg_set('tab_bar_height', 51)
cfg_set('x_axis_height', 60)
cfg_set('imp_plot_height', 350)
cfg_set('time_controls_height', 70)
cfg_set('channel_labels_width', 115)
cfg_set('plot_cntrl_bar_height', 50)
cfg_set('visible_range', (0, 20000)) # 30kHz samples (0.66s)
cfg_set('spike_panel_range', (-100, 100)) # ms
cfg_set('paused', True)
cfg_set('should_fit', False)
cfg_set('skip_left_enabled', False)
cfg_set('skip_right_enabled', True)
cfg_set('plots_window_width', viewport_width * 0.75)
cfg_set('tabs_window_width', viewport_width * 0.25)
cfg_set('bar_heights', (
    cfg_get('menu_bar_height') +
    cfg_get('x_axis_height') +
    cfg_get('time_controls_height') +
    cfg_get('plot_cntrl_bar_height')
))
cfg_set('subplots_height', viewport_height - cfg_get('bar_heights'))
cfg_set('amplif_plots_height', cfg_get('subplots_height') * 0.9)
cfg_set('analog_plots_height', cfg_get('subplots_height') * 0.1)
cfg_set('subplots_width', cfg_get('plots_window_width') - cfg_get('channel_labels_width'))
cfg_set('amplif_plot_heights', max(
    cfg_get('amplif_plots_height') / cfg_get('max_amplif_channels'),
    cfg_get('amplif_plot_heights') 
))

# set the default font
with dpg.font_registry():
    default_font = dpg.add_font(resource_path('SF-Mono-Light.otf'), 21)
    small_font = dpg.add_font(resource_path('SF-Mono-Light.otf'), 16.5)

# dpg.bind_font(small_font)
dpg.bind_font(default_font)


# ------ THEMES ------ #

# Tab10 (no grey)
cfg_set('plot_colors', [
    [31, 119, 180],  # Blue
    [255, 127, 14],  # Orange
    [44, 160, 44],   # Green
    [214, 39, 40],   # Red
    [148, 103, 189], # Purple
    [140, 86, 75],   # Brown
    [227, 119, 194], # Pink
    [188, 189, 34],  # Olive
    [23, 190, 207]   # Cyan
])
cfg_set('electode_mapping', [
    [13, 10, 7, 3],
    [19, 23, 26, 29],
    [18, 21, 24, 28],
    [12, 8, 5, 2],
    [14, 9, 0, 4],
    [20, 16, 25, 30],
    [17, 22, 31, 27],
    [11, 15, 6, 1]
])


# Create a custom colormap
custom_cmap = mcolors.LinearSegmentedColormap.from_list("custom_cmap", [
    [44/255, 160/255, 44/255],   # Green
    [214/255, 39/255, 40/255]    # Red
])
custom_cmap = plt.get_cmap(custom_cmap, 256)
custom_colors = custom_cmap(np.linspace(0, 1, 256))
for idx, color in enumerate(custom_colors):
    print(idx, color)
    with dpg.theme(tag=f'custom_color_{idx}'):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(
                dpg.mvPlotCol_Line, 
                [int(color[0]*255), int(color[1]*255), int(color[2]*255)],
                category=dpg.mvThemeCat_Plots
            )
        

jet_colormap = plt.get_cmap('jet', 256)
jet_colors = jet_colormap(np.linspace(0, 1, 256))
# Apply the adjustment with a brightness factor and saturation factor
brightness_factor = 0.85
saturation_factor = 0.7
jet_colors_adjusted = adjust_color_brightness_saturation(
    jet_colors[:, :3], brightness_factor, saturation_factor
)
with dpg.colormap_registry():
    dpg.add_colormap(jet_colors_adjusted, False, tag='jet_colormap')

# TODO: create a default theme with the style editor!

with dpg.theme(tag=f"disabled_chan"):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 0, 0])

with dpg.theme(tag=f"enabled_chan"):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255])

for i in range(1, int(cfg_get('subplots_width') - 194)):
    with dpg.theme(tag=f'grab_{i}'):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize, i)

with dpg.theme() as disabled_theme:
    with dpg.theme_component(dpg.mvImageButton, enabled_state=False):
        dpg.add_theme_color(dpg.mvThemeCol_Button, [40, 40, 41])
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [40, 40, 41])
dpg.bind_theme(disabled_theme)

with dpg.theme(tag='bar_theme'):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvPlotCol_FrameBg, [45, 45, 46])
        dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, [45, 45, 46])

with dpg.theme(tag='black_text'):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Text, [0,0,0])
        dpg.add_theme_color(dpg.mvPlotCol_InlayText, [0,0,0], category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvPlotCol_LegendText, [0,0,0], category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvPlotCol_Line, [0,0,0], category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvPlotCol_Fill, [0,0,0], category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvThemeCol_PlotLines, [0,0,0])

for idx, color in enumerate(cfg_get('plot_colors')):
    with dpg.theme(tag=f'color_{idx}'):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
        
        with dpg.theme_component(dpg.mvScatterSeries):
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Up, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 4, category=dpg.mvThemeCat_Plots)

with dpg.theme(tag='white_bar'):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_Line, [255, 255, 255], category=dpg.mvThemeCat_Plots)
            
with dpg.theme(tag='test'):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 1, 1)
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding, 0, 0, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize, 0, category=dpg.mvThemeCat_Plots)

for tag in ['max_t', 'min_t']:
    with dpg.theme(tag=tag):    
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, [37, 37, 38], category=dpg.mvThemeCat_Plots)

# ------ TEXTURE LOADING ------ #

icon_names = [
    'play', 'play_disabled', 
    'pause', 'pause_disabled',
    'skip_left', 'skip_left_disabled', 
    'skip_right', 'skip_right_disabled', 
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
    dpg.add_spacer(height=100)


#   -- DIR SELECTION
# create a directory selection dialog
dpg.add_file_dialog(
    tag='dir_dialog',
    label='Select default directory...',
    show=False, modal=True,
    directory_selector=True,
    height=cfg_get('viewport_height') * 0.65,
    width=cfg_get('viewport_width') * 0.5,
    callback=dir_dialog_cb,
    default_path=read_settings('defaults', 'path', os.path.expanduser('~')),
)


#   -- FILE SELECTION
# create a .RHS file selection dialog (visisble by default)
with dpg.file_dialog(
    tag='file_dialog', 
    label='Select file to open...', 
    show=True, modal=True,
    directory_selector=False, 
    height=cfg_get('viewport_height') * 0.65, 
    width=cfg_get('viewport_width') * 0.5,
    callback=file_dialog_cb, 
    default_path=read_settings('defaults', 'path', os.path.expanduser('~'))
):
    dpg.add_file_extension('.rhs', color=(0, 255, 0, 255))
    dpg.add_file_extension('.RHS', color=(0, 255, 0, 255))


#   -- LOADING INDICATOR
pos = [cfg_get('viewport_width') / 2 - 140, cfg_get('viewport_height') / 2 - 110,]
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


#   -- SPIKE PANEL
with dpg.window(
    tag='spike_panels', 
    modal=True, 
    show=False,
):
    with dpg.subplots(
        8, 
        4, 
        label="Spike Panel", 
        width=cfg_get('subplots_width')*1.25, 
        height=cfg_get('subplots_height'), 
        no_title=True, 
        no_menus=True, 
        no_resize=True,
        link_columns=True,
    ):
        for row in range(8):
            for col in range(4):
                plot_size = 50
                with dpg.plot(
                    tag=f'spike_panel_row{row}_col{col}',
                    height=plot_size, 
                    width=plot_size*1.25
                ):
                    dpg.add_plot_axis(
                        dpg.mvXAxis, 
                        no_gridlines=True, 
                        show=True, 
                        tag=f'panel_xaxis_row{row}_col{col}',
                        no_tick_labels=True if row != 7 else False,
                    )
                    dpg.add_plot_axis(
                        dpg.mvYAxis, 
                        label=f'Ch {i}', 
                        no_gridlines=True, 
                        show=True, 
                        tag=f'panel_yaxis_row{row}_col{col}', 
                        no_tick_marks=True, 
                        no_tick_labels=True
                    )
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=cfg_get('subplots_width')*1.25/2-100)
        dpg.add_text("Time relative to crossing (ms)")
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=cfg_get('subplots_width')*1.25/2-400)
        dpg.add_text("Plot Crossings within Range:")
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=cfg_get('subplots_width')*1.25/2-350)
        with dpg.plot(
            height=75, width=cfg_get('subplots_width')*0.5, tag='spike_range_plot_panel', no_mouse_pos=True
        ):
            dpg.add_plot_axis(
                dpg.mvXAxis, 
                tag='xaxis_spk_label_tag_panel',
                no_gridlines=True,
                lock_max=True,
                lock_min=True,
            )
            dpg.add_plot_axis(
                dpg.mvYAxis, 
                tag='yaxis_spk_label_tag_panel',
                no_gridlines=True,
                lock_max=True,
                lock_min=True,
                no_tick_labels=True,
                no_tick_marks=True,
            )
            dpg.add_drag_line(
                label="Start", 
                color=[44, 160, 44, 255], 
                show_label=True,
                thickness=3,
                vertical=True, 
                default_value=0, 
                tag='start_drag_panel',
                callback=start_drag_callback
            )
            dpg.add_drag_line(
                label="End", 
                color=[214, 39, 40, 255], 
                thickness=3,
                vertical=True, 
                default_value=600, 
                tag='end_drag_panel',
                callback=end_drag_callback
            )
        dpg.bind_item_font('spike_range_plot_panel', small_font)
dpg.bind_item_font('spike_panels', small_font)


#   -- PLOTS WINDOW
cfg_set('locs', {i:None for i in range(cfg_get('max_amplif_channels'))})
with dpg.window(
    tag='plots_window',
    pos=[0, cfg_get('menu_bar_height')], 
    show=False,
    width=cfg_get('viewport_width'), 
    height=cfg_get('viewport_height') - cfg_get('menu_bar_height'),
    no_move=True, 
    no_close=True, 
    no_collapse=True, 
    no_title_bar=True, 
    no_bring_to_front_on_focus=True,
) as testtt:
    #   -- PLOT CONTROLS BAR
    dpg.add_spacer(height=5)
    with dpg.table(
        tag='plot_cntrl_bar', 
        header_row=False, 
        policy=dpg.mvTable_SizingFixedFit,
        width=cfg_get('plots_window_width')
    ):
        dpg.add_table_column(width_stretch=True, init_width_or_weight=0.095)
        dpg.add_table_column(width_stretch=True, init_width_or_weight=0.055)
        dpg.add_table_column(width_stretch=True, init_width_or_weight=0.08)
        dpg.add_table_column(width_stretch=True, init_width_or_weight=0.1)
        dpg.add_table_column(width_stretch=True, init_width_or_weight=0.1)

        with dpg.table_row():
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=5)
                dpg.add_text("Plot Type:")
                dpg.add_combo( # dropdown
                    items=["Raw", "Re-Referenced", "Filtered"], 
                    enabled=True, 
                    callback=plot_type_cb,
                    default_value="Filtered", 
                    width=140, 
                )
            with dpg.group(horizontal=True):
                dpg.add_text('Show Spikes:')
                dpg.add_checkbox(
                    callback=toggle_spikes_cb, 
                    default_value=cfg_get('show_spikes'),
                )
            with dpg.group(horizontal=True):
                dpg.add_text('Playback Speed:')
                dpg.add_combo( # dropdown
                    items=["0.05x", "0.1x", "0.5x", "1x", "2x"], 
                    enabled=True, 
                    callback=lambda s, a, u: cfg_set('play_speed', a),
                    default_value=cfg_get('play_speed'), 
                    width=70, 
                )
            with dpg.group(horizontal=True):
                dpg.add_text('Amp. Plot Heights:')
                dpg.add_input_int(
                    tag='amplif_heights_input',
                    callback=amplif_height_cb, 
                    default_value=cfg_get('amplif_plot_heights'), 
                    width=100
                )
            with dpg.group(horizontal=True):   
                dpg.add_text('Analog Plot Heights:')
                dpg.add_input_int(
                    callback=analog_height_cb, 
                    default_value=cfg_get('analog_plot_heights'), 
                    width=100
                )
                dpg.add_spacer(width=5)
    dpg.bind_item_font('plot_cntrl_bar', small_font)
    dpg.add_spacer(height=10)

    #   -- AMPLIFIER CHANNELS
    with dpg.child_window(
        tag='amplif_plots_child',
        height=cfg_get('amplif_plots_height'),
        width=cfg_get('plots_window_width'),
        # no_scrollbar=True,
    ):
        with dpg.group(horizontal=True):
            #   -- CHANNEL LABELS
            # dpg.add_spacer(width=10)
            with dpg.group():
                for chan in range(cfg_get('max_amplif_channels')):
                    dpg.add_spacer(height=cfg_get('subplots_height') / cfg_get('max_amplif_channels') * 0.3)
                    # chan = visible_chans[i]
                    dpg.add_text(f'  Ch {chan:02d}', tag=f'ch{chan}')
                    dpg.bind_item_theme(f'ch{chan}', f'color_{chan % len(cfg_get("plot_colors"))}')

            #   -- SUBPLOTS
            with dpg.group(tag='amplif_plots_group'):
                show_spikes = read_settings('defaults', 'show_spikes', False)
                with dpg.subplots(
                    tag='amplif_plots',
                    rows=cfg_get('max_amplif_channels')*2,
                    columns=1,
                    width=cfg_get('subplots_width'),
                    height=(
                        cfg_get('amplif_plot_heights') * \
                        cfg_get('max_amplif_channels') * \
                        (1 + show_spikes)
                    ),
                    row_ratios=(
                        [1, 0.1 if show_spikes else 0] * \
                        cfg_get('max_amplif_channels')
                    ),
                    no_resize=True,
                    link_columns=True,
                ):
                    for i in range(cfg_get('max_amplif_channels')):
                        with dpg.plot(
                            anti_aliased=False, 
                            no_mouse_pos=True, 
                            tag=f'plot{i}',
                            query=True,
                            callback=query_cb,
                            no_menus=True,
                            query_toggle_mod=dpg.mvKey_Shift
                            # query_toggle_mod=dpg.mvKey_LShift
                        ):
                            dpg.add_plot_axis(
                                dpg.mvXAxis, 
                                tag=f'xaxis_tag{i}', 
                                no_gridlines=True, 
                                no_tick_marks=True, 
                                no_tick_labels=True
                            )
                            with dpg.plot_axis(
                                dpg.mvYAxis, 
                                tag=f'yaxis_tag{i}', 
                                no_gridlines=True,
                                no_tick_marks=True, 
                                no_tick_labels=True,  
                            ):
                                # add dummy raw data
                                dpg.add_line_series(
                                    tag=f'raw_data_{i}',
                                    x=[0,0], y=[0,0],
                                    show=False,
                                )
                            
                                # add dummy car data
                                dpg.add_line_series(
                                    tag=f're-referenced_data_{i}',
                                    x=[0,0], y=[0,0],
                                    show=False,
                                )

                                # add dummy filtered data
                                dpg.add_line_series(
                                    tag=f'filtered_data_{i}',
                                    x=[0,0], y=[0,0],
                                    show=False,
                                )


                            # add dummy query text (time ruler label)
                            dpg.add_plot_annotation(

                                tag=f'query_text{i}',
                                label="100 ms", 
                                default_value=(1, 0), 
                                show=False,
                                offset=(15, 15), 
                                color=[0,0,0,255],
                            )
                            dpg.bind_item_font(f'query_text{i}', small_font)
                        dpg.bind_item_theme(f'plot{i}', 'test', )

                        with dpg.plot(
                            anti_aliased=False, 
                            no_mouse_pos=True, 
                            tag=f'spk_plot{i}',
                            no_menus=True,
                        ):
                            dpg.add_plot_axis(
                                dpg.mvXAxis, 
                                tag=f'spk_xaxis_tag{i}', 
                                no_gridlines=True, 
                                no_tick_marks=True, 
                                no_tick_labels=True
                            )
                            with dpg.plot_axis(
                                dpg.mvYAxis, 
                                tag=f'spk_yaxis_tag{i}', 
                                no_gridlines=True,
                                no_tick_marks=True, 
                                no_tick_labels=True,  
                                lock_min=True,
                                lock_max=True,
                            ):
                                # add dummy spikes
                                dpg.add_scatter_series(
                                    tag=f'spikes_{i}',
                                    x=[0,0], y=[0,0],
                                    show=True,
                                )
                            dpg.set_axis_limits(f'spk_yaxis_tag{i}', 0.75, 1.25)
                        dpg.bind_item_theme(f'spk_plot{i}', 'test', )

                # dpg.bind_item_theme('amplif_plots', 'subplots_theme')

    #   -- ANALOG CHANNELS
    with dpg.child_window(
        tag='analog_plots_child',
        height=cfg_get('analog_plots_height'),
        width=cfg_get('plots_window_width'),
        # no_scrollbar=True,
    ):
        with dpg.group(horizontal=True):
            #   -- CHANNEL LABELS
            # dpg.add_spacer(width=10)
            with dpg.group():
                for chan in range(cfg_get('max_analog_channels')):
                    dpg.add_text(f'Ch A-{chan:02d}', tag=f'a_ch{chan}')
                    dpg.bind_item_theme(f'a_ch{chan}', f'color_{chan % len(cfg_get("plot_colors"))}')

            #  -- SUBPLOTS
            with dpg.group(tag='analog_plots_group'):
                with dpg.subplots(
                    tag='analog_plots',
                    rows=cfg_get('max_analog_channels'),
                    columns=1,
                    width=cfg_get('subplots_width'),
                    height=cfg_get('analog_plot_heights') * cfg_get('max_analog_channels'),
                    link_columns=True,
                    no_resize=True,
                ):
                    for i in range(cfg_get('max_analog_channels')):
                        with dpg.plot(
                            tag=f'a_plot{i}',
                            height=cfg_get('analog_plot_heights'), 
                            anti_aliased=False, 
                            no_mouse_pos=True, 
                            query=True,
                            callback=query_cb,
                        ):
                            dpg.add_plot_axis(
                                dpg.mvXAxis, 
                                tag=f'a_xaxis_tag{i}', 
                                show=True, 
                                no_gridlines=True, 
                                no_tick_marks=True, 
                                no_tick_labels=True
                            )
                            with dpg.plot_axis(
                                dpg.mvYAxis, 
                                tag=f'a_yaxis_tag{i}', 
                                no_gridlines=True,  
                                no_tick_marks=True, 
                                no_tick_labels=True,  
                            ):
                                # add dummy analog data
                                dpg.add_line_series(
                                    tag=f'analog_data_{i}',
                                    x=[0,0], y=[0,0],
                                    show=True,
                                )
                            # add dummy query text (time ruler label)
                            dpg.add_plot_annotation(
                                tag=f'a_query_text{i}',
                                label="100ms", 
                                default_value=(1, 0), 
                                show=False,
                                offset=(15, 15), 
                                color=[0,0,0,255],
                            )
                            dpg.bind_item_font(f'a_query_text{i}', small_font)
                        dpg.bind_item_theme(f'a_plot{i}', 'test', )
    #  -- X-AXIS TICKS
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=82)
        with dpg.plot(height=40, width=cfg_get('subplots_width') + 15, tag='label_plot'):
            dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, show=True, tag='xaxis_label_tag')
            x_min, x_max = cfg_get('visible_range')
            dpg.set_axis_limits(dpg.last_item(), int(x_min/30), int(x_max/30))
            dpg.add_plot_axis(dpg.mvYAxis, no_gridlines=True, no_tick_marks=True, tag=f'xaxis_label_yaxis_tag', no_tick_labels=True, lock_min=True, lock_max=True)

    #  -- X-AXIS LABEL
    with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit):
        dpg.add_table_column(width_stretch=True, init_width_or_weight=0.21)
        dpg.add_table_column(width_stretch=False, init_width_or_weight=100)
        dpg.add_table_column(width_stretch=True, init_width_or_weight=0.3)
        with dpg.table_row():
            dpg.add_text('')
            dpg.add_text('Time (ms)', tag='x_label')
            dpg.add_text('')

    dpg.bind_item_font('x_label', small_font)
    dpg.bind_item_font('label_plot', small_font)

    #   -- TIME CONTROL BAR
    with dpg.group(horizontal=True):
        dpg.add_image_button(
            "skip_left_disabled_texture", 
            callback=skip_reverse, 
            enabled=False, 
            tag='skip_left_bt'
        )
        dpg.add_image_button("play_texture", callback=play, tag='play_bt')
        dpg.add_image_button(
            "pause_disabled_texture", 
            callback=pause, 
            enabled=False, 
            tag='pause_bt'
        )

        with dpg.group():
            dpg.add_text('00:00 / ??:??', tag='time_text')
        with dpg.group():
            dpg.add_slider_int(
                tag='time_slider', 
                default_value=cfg_get('visible_range')[0], 
                min_value=0, 
                max_value=999, 
                format='', 
                callback=time_slider_drag, 
                width=cfg_get('subplots_width') - 195)
            dpg.bind_item_theme('time_slider', 'bar_theme')
        
        dpg.add_image_button(
            'skip_right_texture', 
            callback=skip_forward, 
            tag='skip_right_bt'
        )


#   -- TABS WINDOW
with dpg.window(
    tag='tabs_window',
    pos=[cfg_get('plots_window_width'), cfg_get('menu_bar_height')], 
    show=False,
    width=cfg_get('tabs_window_width'), 
    height=cfg_get('viewport_height') - cfg_get('menu_bar_height'),
    no_move=True, 
    no_close=True, 
    no_collapse=True, 
    no_title_bar=True, 
):
    with dpg.tab_bar(tag='tab_bar') as tb:
        tabsize = cfg_get('tabs_window_width') / 3
        letter_width = 11.5  

        # CHANNELS TAB
        with dpg.tab(label="Channels", tag='channels_tab'):
            n_chans = cfg_get('max_amplif_channels')

            dpg.add_spacer(height=10)
            dpg.add_input_int(
                label=" Impedance Limit (kOhms)", 
                default_value=cfg_get('impedance_threshold'), 
                tag='imp_thresh', 
                width=125, 
                on_enter=True,
                callback=imp_thresh_callback
            )
            dpg.add_spacer(height=10)

            with dpg.group(horizontal=True):
                with dpg.child(
                    height=(
                        cfg_get('viewport_height') - \
                        cfg_get('menu_bar_height') - \
                        cfg_get('imp_plot_height') - \
                        cfg_get('tab_bar_height') - \
                        60
                    ),
                    width=-1
                ):  # Set desired height and width
                    with dpg.table(
                        header_row=True, 
                        policy=dpg.mvTable_SizingFixedFit, 
                    ):
                        dpg.add_table_column(
                            label="Channel #", 
                            width_stretch=True, 
                            init_width_or_weight=0.35
                        )
                        dpg.add_table_column(
                            label="Impedance", 
                            width_stretch=True, 
                            init_width_or_weight=0.5
                        )
                        dpg.add_table_column(
                            label="Plot", 
                            width_stretch=True, 
                            init_width_or_weight=0.2
                        )
                        dpg.add_table_column(
                            label="Incl. in CAR",
                            width_stretch=True, 
                            init_width_or_weight=0.35
                        )
                        for chan in range(n_chans):
                            with dpg.table_row():
                                dpg.add_text(
                                    f"Ch {chan:02d}", tag=f'tab_ch{chan}'
                                )
                                dpg.add_text(
                                    "799.9 kOhm", tag=f'impedance_ch{chan}'
                                )
                                dpg.add_checkbox(
                                    label="", 
                                    default_value=True, 
                                    tag=f'plot_{chan}',
                                    callback=plot_bt_callback
                                )
                                dpg.add_checkbox(
                                    label="", 
                                    default_value=True, 
                                    tag=f'include_{chan}',
                                    callback=include_bt_callback,
                                )

            with dpg.group(horizontal=True):
                dpg.add_colormap_scale(
                    tag='colormap_scale',
                    height=cfg_get('imp_plot_height'),
                    width=65,
                    colormap='jet_colormap',
                )
                with dpg.plot(
                    tag='imp_heatmap', 
                    label="Electrode Impedances (kOhms)", 
                    no_mouse_pos=True,  
                    height=cfg_get('imp_plot_height'),  
                    width=-1
                ):
                    dpg.add_plot_axis(
                        dpg.mvXAxis, 
                        lock_min=True, 
                        lock_max=True, 
                        no_gridlines=True, 
                        no_tick_marks=True,
                        no_tick_labels=True,
                    )
                    dpg.add_plot_axis(
                        dpg.mvYAxis, 
                        tag='imp_plot_yaxis',
                        no_gridlines=True, 
                        no_tick_marks=True, 
                        no_tick_labels=True,
                        lock_min=True, 
                        lock_max=True
                    )

        # FILTERING TAB
        with dpg.tab(label='Filtering', tag='filtering_tab'):
            dpg.add_spacer(height=10)
            with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_stretch=False, init_width_or_weight=200)
                dpg.add_table_column(width_stretch=True, init_width_or_weight=0.3)

                with dpg.table_row():
                    dpg.add_text('Filter Type:')
                    dpg.add_combo(
                        items=["Butterworth", "Bessel"], 
                        default_value=cfg_get('filter_type'), 
                        enabled=True, 
                        width=160,
                        callback=update_filt_type
                    )
                with dpg.table_row():
                    dpg.add_text("Filter Order:")
                    dpg.add_input_int(
                        enabled=True, 
                        default_value=cfg_get('filter_order'), 
                        width=100,
                        on_enter=True,
                        callback=update_filt_order, 
                    )
                with dpg.table_row():
                    dpg.add_text('Band Type:')
                    dpg.add_combo(
                        items=['Bandpass', 'Lowpass', 'Highpass'], 
                        default_value=cfg_get('band_type'), 
                        enabled=True, 
                        width=140,
                        callback=update_band_type
                    )
                with dpg.table_row():
                    dpg.add_text("Low:")
                    dpg.add_input_int(
                        enabled=True, 
                        default_value=cfg_get('filter_range')[0], 
                        width=130, 
                        on_enter=True,
                        callback=update_low_filter,
                    )
                with dpg.table_row():
                    dpg.add_text("High:")
                    dpg.add_input_int(
                        enabled=True, 
                        default_value=cfg_get('filter_range')[1], 
                        width=130,
                        on_enter=True,
                        callback=update_high_filter, 
                    )
                with dpg.table_row():
                    dpg.add_text('Notch Filter:')
                    dpg.add_combo(
                        items=['None', '60 Hz'], 
                        default_value='60 Hz' if cfg_get('notch_filter') else 'None', 
                        enabled=True, 
                        width=100,
                        callback=update_notch
                    )
            dpg.add_spacer(height=40)

            with dpg.plot(
                height=500, width=-1, no_mouse_pos=True, tag='psd_plot'
            ):
                dpg.add_plot_axis(
                    dpg.mvXAxis, tag='psd_xaxis_tag',label="Frequency (Hz)"
                )
                with dpg.plot_axis(
                    dpg.mvYAxis, 
                    label="Power", 
                    tag='psd_yaxis_tag', 
                    log_scale=True,
                    lock_min=True,
                    lock_max=True,
                ):
                    for l in ['Raw', 'CAR', 'Filtered']:
                        dpg.add_line_series(
                            [0,0], [0,0],
                            tag=f'psd_{l}',
                            label=l, 
                        )

                dpg.add_plot_legend(
                    location=dpg.mvPlot_Location_South, 
                    outside=True, 
                    horizontal=True
                )
            dpg.bind_item_font('psd_plot', small_font)

        # SPIKES TAB
        with dpg.tab(label='Spikes', tag='spikes_tab'):
            dpg.add_spacer(height=10)

            with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_stretch=False, init_width_or_weight=240)
                dpg.add_table_column(width_stretch=True, init_width_or_weight=0.3)

                with dpg.table_row():
                    dpg.add_text('Threshold Multiplier:')
                    dpg.add_input_float(
                        default_value=cfg_get('threshold_mult'),
                        format='%.1f',
                        tag='thresh_mult', 
                        width=125,
                        on_enter=True,
                        callback=thresh_mult_callback
                    )
            
            dpg.add_spacer(height=10)

            with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_stretch=True, init_width_or_weight=0.45)
                dpg.add_table_column(width_stretch=False, init_width_or_weight=240)
                dpg.add_table_column(width_stretch=True, init_width_or_weight=0.3)

                with dpg.table_row():
                    dpg.add_text('')
                    dpg.add_button(
                        label="View All Channels", 
                        width=200, 
                        tag='view_all_chans',
                        callback=view_all_chans_callback
                    )
                    dpg.add_text('')

            dpg.add_spacer(height=10)
            
            with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_stretch=False, init_width_or_weight=175)
                dpg.add_table_column(width_stretch=True, init_width_or_weight=0.3)

                with dpg.table_row():
                    dpg.add_text('Channel to Plot:')
                    dpg.add_combo(
                        items=[f'Ch {i}' for i in range(cfg_get('max_amplif_channels'))], 
                        default_value='Ch 00', 
                        enabled=True, 
                        width=100, 
                        tag='spk_sco_ch', 
                        callback=spike_chan_callback
                    )

            with dpg.plot(height=500, width=-1, tag='spike_panel_plot'):
                dpg.add_plot_axis(dpg.mvXAxis, label="Time relative to crossing (ms)",  tag='spike_xaxis_tag')
                dpg.add_plot_axis(dpg.mvYAxis, label="Voltage (uV)", tag='spike_yaxis_tag')
            
            dpg.bind_colormap('spike_panel_plot', jet_colormap)

            dpg.bind_item_font('spike_panel_plot', small_font)

            dpg.add_text("Plot Crossings within Range:")
            with dpg.plot(
                height=75, width=-1, tag='spike_range_plot', no_mouse_pos=True
            ):
                dpg.add_plot_axis(
                    dpg.mvXAxis, 
                    tag='xaxis_spk_label_tag',
                    no_gridlines=True,
                    lock_max=True,
                    lock_min=True,
                )
                dpg.add_plot_axis(
                    dpg.mvYAxis, 
                    no_gridlines=True,
                    lock_max=True,
                    lock_min=True,
                    no_tick_labels=True,
                    no_tick_marks=True,
                )
                dpg.add_drag_line(
                    label="Start", 
                    color=[44, 160, 44, 255], 
                    show_label=True,
                    thickness=3,
                    vertical=True, 
                    default_value=0, 
                    tag='start_drag',
                    callback=start_drag_callback
                )
                dpg.add_drag_line(
                    label="End", 
                    color=[214, 39, 40, 255], 
                    thickness=3,
                    vertical=True, 
                    default_value=600, 
                    tag='end_drag',
                    callback=end_drag_callback
                )
            dpg.bind_item_font('spike_range_plot', small_font)
    
dpg.bind_colormap('imp_heatmap', 'jet_colormap')
dpg.bind_item_font('imp_heatmap', small_font)
dpg.bind_item_font('colormap_scale', small_font)

with dpg.handler_registry():
    dpg.add_mouse_drag_handler(
        button=dpg.mvMouseButton_Left, callback=plot_drag_callback
    )
    dpg.add_mouse_wheel_handler(callback=plot_zoom_callback)


for i in range(cfg_get('max_amplif_channels')):
    with dpg.item_handler_registry(tag=f'plot{i}_handler') as handler_reg:
        dpg.add_item_clicked_handler(
            button=dpg.mvMouseButton_Middle, 
            callback=remove_query_cb, 
            tag=f'plot{i}_clicked_handler', 
        )
    dpg.bind_item_handler_registry(f'plot{i}', f'plot{i}_handler', ) 

for i in range(cfg_get('max_analog_channels')):
    with dpg.item_handler_registry(tag=f'a_plot{i}_handler') as handler_reg:
        dpg.add_item_clicked_handler(
            button=dpg.mvMouseButton_Middle, 
            callback=remove_query_cb, 
            tag=f'a_plot{i}_clicked_handler', 
        )
    dpg.bind_item_handler_registry(f'a_plot{i}', f'a_plot{i}_handler', ) 

dpg.show_style_editor()
# dpg.show_metrics()

# ------ RENDER LOOP ------ #

# start the rendering loop
while dpg.is_dearpygui_running():
    if cfg_get('paused'):
        last_update_time = timeit.default_timer()
    else:
        print(f'no_pause - where segfault01')
        with dpg.mutex():
            print(f'no_pause - where segfault02')
            current_time = timeit.default_timer()
            print(f'no_pause - where segfault03')
            new_limits = get_play_limits(last_update_time, current_time)
            print(f'no_pause - where segfault04')
            last_update_time = current_time
            print(f'no_pause - where segfault05')
            plot_data_play(new_limits)
            print(f'no_pause - where segfault06')
            pre_fit_y_axes()
            print(f'no_pause - where segfault07')


    dpg.render_dearpygui_frame()

    if not cfg_get('paused'):
        print(f'no_pause - where segfault08')
        with dpg.mutex():
            print(f'no_pause - where segfault09')
            post_fit_y_axes()
            print(f'no_pause - where segfault10')

dpg.destroy_context()