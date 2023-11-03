import dearpygui.dearpygui as dpg
from util_funcs import *

# define constants
APP_NAME = 'EphysViz'
SCREEN_HEIGHT, SCREEN_WIDTH = get_screen_size()

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

# function to be called when a file is selected in the file dialog
def f_select_callback(sender, app_data, user_data):
    dpg.show_item("loading_indicator")
    # test_func(list(app_data['selections'].values())[0])

# ------ WINDOWS ------ #

# create a .RHS file selection dialog
with dpg.file_dialog(
    id='file_dialog', show=True, 
    directory_selector=False, 
    callback=f_select_callback, 
    height=SCREEN_HEIGHT * 0.5, 
    width=SCREEN_WIDTH * 0.5,
    default_path='/Users/domenick_mifsud/Desktop'
):
    dpg.add_file_extension('.rhs', color=(0, 255, 0, 255))
    dpg.add_file_extension('.RHS', color=(0, 255, 0, 255))


# create a loading indicator
pos = [screen_width/2 - 90, screen_height/2 - 110,]
with dpg.window(pos=pos, show=False, tag='loading_indicator'):
    dpg.add_spacer(height=5)
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=20)
        dpg.add_loading_indicator()
        with dpg.group():
            dpg.add_spacer(height=5)
            dpg.add_text('Loading...')
        dpg.add_spacer(width=20)
    dpg.add_spacer(height=5)

# --------------------- #

# start the rendering loop
while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

# clean up
dpg.destroy_context()