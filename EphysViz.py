import dearpygui.dearpygui as dpg
from util_funcs import *

# define constants
APP_NAME = 'EphysViz'
SCREEN_HEIGHT, SCREEN_WIDTH = get_screen_size()
PLOTS_WINDOW_WIDTH = SCREEN_WIDTH * 0.75
TABS_WINDOW_WIDTH = SCREEN_WIDTH * 0.25
MENU_BAR_HEIGHT = 26

# create a dearpygui context
dpg.create_context()

# create a viewport (base window) that fills up the entire screen
dpg.create_viewport(
    title='EphysViz', 
    x_pos=0, y_pos=0, 
    height=SCREEN_HEIGHT, 
    width=SCREEN_WIDTH,
)

# setup dearpygui and show the viewport
dpg.setup_dearpygui()
dpg.show_viewport()

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


# ------ TEXTURE LOADING ------ #

icon_names = [
    'play', 'play_disabled', 
    'pause', 'pause_disabled',
    'skip_left', 'skip_left_disabled',
    'skip_right', 'skip_right_disabled', 
    'up_channel', 'down_channel'
]

for name in icon_names:
    _, _, _, data = dpg.load_image(resource_path(f"{name}.png"))
    with dpg.texture_registry(show=False):
        size = 15 if name in ['up_channel', 'down_channel'] else 20
        dpg.add_static_texture(
            height=size, width=size, 
            default_value=data, 
            tag=f"{name}_texture"
        )

# ------ WINDOWS ------ #

#   -- MENU BAR
with dpg.viewport_menu_bar(tag='menu_bar', show=False):
    with dpg.menu(label="File"):
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
    height=SCREEN_HEIGHT * 0.5,
    width=SCREEN_WIDTH * 0.5,
    callback=dir_dialog_cb,
    default_path=read_settings('defaults', 'path', os.path.expanduser('~')),
)


#   -- FILE SELECTION
# callback for the file dialog
def file_dialog_cb(sender, app_data, user_data):
    dpg.hide_item("plots_window")
    dpg.hide_item("tabs_window")
    dpg.show_item("loading_indicator")
    import time
    time.sleep(1)
    dpg.hide_item("loading_indicator")
    dpg.show_item("plots_window")
    dpg.show_item("tabs_window")
    # test_func(list(app_data['selections'].values())[0])

# create a .RHS file selection dialog (visisble by default)
with dpg.file_dialog(
    tag='file_dialog', 
    label='Select file to open...', 
    show=True, modal=True,
    directory_selector=False, 
    height=SCREEN_HEIGHT * 0.5, 
    width=SCREEN_WIDTH * 0.5,
    callback=file_dialog_cb, 
    default_path=read_settings('defaults', 'path', os.path.expanduser('~'))
):
    dpg.add_file_extension('.rhs', color=(0, 255, 0, 255))
    dpg.add_file_extension('.RHS', color=(0, 255, 0, 255))


#   -- LOADING INDICATOR
pos = [SCREEN_WIDTH / 2 - 140, SCREEN_HEIGHT / 2 - 110,]
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
with dpg.window(
    tag='plots_window',
    pos=[0, MENU_BAR_HEIGHT], 
    show=False,
    width=SCREEN_WIDTH, 
    height=SCREEN_HEIGHT - MENU_BAR_HEIGHT,
    no_move=True, 
    no_close=True, 
    no_collapse=True, 
    no_title_bar=True, 
    no_bring_to_front_on_focus=True,
):
    #   -- PLOT CONTROLS BAR
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=30)
        dpg.add_combo( # dropdown
            items=["Raw", "Re-Referenced", "Filtered"], 
            default_value="Filtered", 
            enabled=True, 
            width=100, 
            # callback=change_w_type
        )
        dpg.add_spacer(width=30)
        dpg.add_checkbox(
            label="Show Spikes", 
            # callback=toggle_spikes, 
            default_value=read_settings(
                'defaults', 
                'show_spikes', 
                False
            )
        )
        dpg.add_spacer(width=PLOTS_WINDOW_WIDTH - 200)
        dpg.add_input_int(
            label="Plot Height", 
            default_value=100, 
            width=100
        )


#   -- TABS WINDOW
with dpg.window(
    tag='tabs_window',
    pos=[PLOTS_WINDOW_WIDTH, MENU_BAR_HEIGHT], 
    show=False,
    width=TABS_WINDOW_WIDTH, 
    height=SCREEN_HEIGHT - MENU_BAR_HEIGHT,
    no_move=True, 
    no_close=True, 
    no_collapse=True, 
    no_title_bar=True, 
):
    with dpg.tab_bar(tag='tab_bar') as tb:
        tabsize = TABS_WINDOW_WIDTH / 3
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