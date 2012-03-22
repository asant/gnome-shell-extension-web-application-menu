#!/usr/bin/python
#
# Setup application for the Web Application Menu extension for the GNOME Shell.
# Copyright (C) 2012  Andrea Santilli <andresantilli gmx com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.

from gi.repository import Gio, GLib, GObject, Gtk
from glib.option import OptionParser, make_option
from collections import deque
import gettext
import json
import sys

# general strings
ADD_PROFILE_DIALOG      = "Add profile"
DEF_PROFILE_TEXT        = "Use the default profile"
DELETE_PROFILE_DIALOG   = "Row deletion"
DELETE_PROFILE_TEXT     = "Delete the currently selected profile?"
DIR_CHOOSER_TITLE       = "Browse directories"
HIDE_NON_XDG_TEXT       = "Hide entries not in user's application path"
ICON_SIZE_TEXT          = "Icon size"
PROFILE_NAME            = "Profile name"
PROFILE_DIR             = "Directory"
QUIT_DIALOG             = "Really quit?"
QUIT_TEXT               = "Quit without saving your changes?"
RELOAD_DIALOG           = "Really reload?"
RELOAD_TEXT             = "Your changes will be lost! Continue?"
SHOW_ICONS_TEXT         = "Show entry icons"
SPLIT_VIEW_TEXT         = "Share the view out among profiles"
TAB_1_LABEL             = "General"
TAB_2_LABEL             = "Other profiles"
WINDOW_TITLE            = "Web App Menu Extension Options"

# actions
BROWSE_PROFILE_TEXT     = "Choose directory"
DELETE_PROFILE_BTN_TEXT = "Delete"
EDIT_PROFILE_TEXT       = "Edit"
MANAGE_DEFAULT          = "Manage default profile"
MANAGE_PROFILE_TEXT     = "Manage applications"
NEW_PROFILE_TEXT        = "New"
RELOAD_BTN_TEXT         = "Reload"

# errors
ERR_BAD_PROFILE     = "Error reading profile #%d\n"
ERR_BAD_FORMAT      = "WARNING: file \"%s\" is badly formatted.\nOptions \
initialized to their default values."
ERR_BASE_NOT_DIR    = "The base path is not a directory!"
ERR_CANT_MKDIR      = "Could not create the base directory!"
ERR_ENTRY_START     = "Problems detecting the following entries:\n%s"
ERR_FILE_HELP       = "use data from the json file for reading and writing"
ERR_FILE_NOT_FOUND  = "WARNING: file \"%s\" not found!\nOptions initialized \
to their default values."
ERR_FILE_WRITE      = "Error writing to file \"%s\":\n%s"
ERR_FILE_UNREADABLE = "WARNING: could not read file \"%s\"!\nOptions \
initialized to their default values."
ERR_KEYS_START      = "Problems retrieving values for the following keys:\n"
ERR_SPAWN           = "Spawning failure for command: %s"
ERR_TITLE           = "Error"
ERR_USAGE           = "- configurator for the web application menu"
ERR_WRONG_ARGS      = "Wrong arguments"
WARN_DEF_OPT_FILE   = "File name not specified, using %s by default.\n"

# default option values
DEFAULT_OPTIONS = {
    'icon-size'                     : 16,
    'show-icons'                    : True,
    'use-default-profile'           : True,
    'split-profile-view'            : True,
    'hide-entries-not-in-xdg-dir'   : True,
    'profiles'                      : []
}

EXTENSION_UUID              = 'web-application-menu@atomant'
HANDLE_MAIN_PROFILE_CMD     = 'epiphany about:applications'
HANDLE_PROFILE_CMD          = 'epiphany -p --profile=\"%s\" about:applications'
LOCALE_SUBDIR               = 'locale'

DEFAULT_OPTION_FILE_PARTS = [ GLib.get_user_data_dir(), 'gnome-shell',
        'extensions', EXTENSION_UUID, 'settings.json' ]

gettext.textdomain(EXTENSION_UUID)
# please don't use _() as it clashes with python's built-in _ symbol
g = gettext.gettext

# other constants
APP_ID      = 'apps.gnome-shell.extensions.web-app-menu.configurator.file-'
COLUMN      = { 'name': 0, 'dir': 1, 'num' : 2 }
ERR_SIZE    = { 'x': 420, 'y': 150 }
PADDING     = 3
SPACING     = 3
SIZE        = { 'x': 500, 'y': 400 }
SPIN_END    = 1024.0
SPIN_START  = 4.0
SPIN_STEP   = 1.0

# enums wannabe
class ColumnIds:
    LEFT    = 0
    RIGHT   = 1
    NUM     = 2

class ColumnAttach:
    LEFT = 0
    CENTER = 1
    RIGHT = 2

class TableSize:
    ROWS = 6
    COLUMNS = 2

class MiscAlignment:
    LEFT = 0.0
    CENTER = 0.5
    RIGHT = 1.0

class MouseButtons:
    LEFT = 1
    CENTER = 2
    RIGHT = 3

class Configurator(Gtk.Application):
    def __init__(self, filename, locale_dir):
        self.filename = filename
        self.file = Gio.file_new_for_path(self.filename)
        self.id = deque()

        if locale_dir != None:
            gettext.bindtextdomain(EXTENSION_UUID, locale_dir)

        # only an unique instance of this app is runnable for each json file.
        # now hash by using GQuark
        Gtk.Application.__init__(self, application_id="%s%ld" % (APP_ID,
                GLib.quark_from_string(self.file.get_path())),
                flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect('activate', self.on_activate)

    def on_activate(self, data=None):
        wins = self.get_windows()
        if wins.__len__() == 0:
            # build window
            self.win = self.__build_main_window()
            self.win.show_all()

            # retrieve options from json file
            self.__load_config_from_file(self.file)

            self.__connect_all()
            self.add_window(self.win)
        else:
            wins[0].present()

    # show error messages in a dialog with scrollable text
    def __show_error(self, error_title, error_text):
        dialog = Gtk.Dialog()
        dialog.set_title(error_title)
        dialog.set_modal(True)
        dialog.set_destroy_with_parent(True)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_size_request(ERR_SIZE['x'], ERR_SIZE['y'])
        dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        label = Gtk.Label(error_text)
        label.set_justify(Gtk.Justification.LEFT)
        scrolled_win = Gtk.ScrolledWindow(None, None)
        viewport = Gtk.Viewport()
        viewport.add(label)
        scrolled_win.add(viewport)
        dialog.get_content_area().add(scrolled_win)        
        dialog.get_content_area().child_set_property(scrolled_win,
                'expand', True)
        dialog.get_action_area().set_layout(Gtk.ButtonBoxStyle.CENTER)
        dialog.set_transient_for(self.win)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # dialog for entering a new profile
    def __on_new_cb(self):
        new_name = Gtk.Entry()
        new_dir = Gtk.Entry()
        hbox = Gtk.HBox(homogeneous = True, spacing = SPACING)
        
        dialog = Gtk.Dialog()
        dialog.set_title(g(ADD_PROFILE_DIALOG))
        dialog.set_modal(True)
        dialog.set_destroy_with_parent(True)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

        new_name.set_placeholder_text(g(PROFILE_NAME))
        new_dir.set_placeholder_text(g(PROFILE_DIR))
        new_dir.set_icon_from_stock(Gtk.EntryIconPosition.PRIMARY,
                Gtk.STOCK_OPEN)
        new_dir.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY,
                g(BROWSE_PROFILE_TEXT))
        hbox.pack_start(new_name, True, True, PADDING)
        hbox.pack_start(new_dir, True, True, PADDING)
        dialog.get_content_area().add(hbox)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_transient_for(self.win)
        dialog.get_widget_for_response(Gtk.ResponseType.OK).set_sensitive(
                False)
        dialog.get_widget_for_response(Gtk.ResponseType.CANCEL).grab_focus()

        def on_entry_text_changed(entry1, button, entry2):
            button.set_sensitive(entry1.get_text().strip() != '' and
                    entry2.get_text().strip() != '')
        def on_icon_press(entry, pos, event):
            # left button pressed
            if event.button != MouseButtons.LEFT:
                return
            chooser = Gtk.FileChooserDialog()
            chooser.set_title(g(DIR_CHOOSER_TITLE))
            chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
            chooser.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            chooser.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            chooser.set_transient_for(dialog)
            if chooser.run() == Gtk.ResponseType.OK:
                dir = Gio.File.new_for_uri(chooser.get_uri())
                entry.set_text(dir.get_path())
            chooser.destroy()

        new_name.connect('changed', on_entry_text_changed,
                dialog.get_widget_for_response(Gtk.ResponseType.OK),
                new_dir)

        new_dir.connect('changed', on_entry_text_changed,
                dialog.get_widget_for_response(Gtk.ResponseType.OK),
                new_name)
        new_dir.connect('icon-press', on_icon_press)

        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.CANCEL:
            dialog.destroy()
        else:
            self.__set_changed(True)
            i = self.profile_store.append()
            self.profile_store.set(i, COLUMN['name'],
                    new_name.get_text().strip(),
                    COLUMN['dir'], new_dir.get_text().strip())
            dialog.destroy()

    # edit the currently selected cell
    def __on_edit_cb(self):
        [path, col] = self.profile_view.get_cursor()
        if (not(col is None)) and (not(path is None)):
            self.profile_view.set_cursor(path, col, True)

    # accept the changes on the treeview
    def __on_edit_done_cb(self, path, new_text, col):
        i = self.profile_store.get_iter_from_string(path)
        # changes are stripped first, then accepted if the string is not empty
        if not(i is None):
            stripped = new_text.strip()

            # compare the old string with the newer one
            val = self.profile_store.get_value(i, col)

            val_str = ''.join(val)
            if (stripped != '') and (val_str.strip() != stripped):
                self.__set_changed(True)
                self.profile_store.set(i, col, stripped)

    # browse directory for the currently selected row
    def __on_browse_cb(self):
        res, i = self.selection.get_selected()
        if not(i is None):
            chooser = Gtk.FileChooserDialog()
            chooser.set_title(g(DIR_CHOOSER_TITLE))
            chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
            chooser.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            chooser.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            chooser.set_transient_for(self.win)
            if chooser.run() == Gtk.ResponseType.OK:
                self.__set_changed(True)
                dir = Gio.File.new_for_uri(chooser.get_uri())
                self.profile_store.set(i, COLUMN['dir'], dir.get_path())
            chooser.destroy()

    # delete the currently selected row with confirm dialog
    def __on_delete_cb(self):
        res, i = self.selection.get_selected()
        if not(i is None):
            # emulating gtk_dialog_new_with_buttons()
            dialog = Gtk.Dialog()
            dialog.set_title(g(DELETE_PROFILE_DIALOG))
            dialog.set_modal(True)
            dialog.set_destroy_with_parent(True)
            dialog.add_button(Gtk.STOCK_YES, Gtk.ResponseType.YES)
            dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

            dialog.set_default_response(Gtk.ResponseType.CANCEL)
            dialog.get_content_area().add(Gtk.Label(g(DELETE_PROFILE_TEXT)))
            dialog.set_transient_for(self.win)
            dialog.show_all()

            if dialog.run() == Gtk.ResponseType.CANCEL:
                dialog.destroy()
            else:
                self.__set_changed(True)
                self.profile_store.remove(i)
                dialog.destroy()

    def __on_manage_cb(self):
        res, i = self.selection.get_selected()
        if not(i is None):
            val = self.profile_store.get_value(i, COLUMN['dir'])
            command = (HANDLE_PROFILE_CMD) % val
            print(command)
            try:
                GLib.spawn_command_line_async(command)
            except Exception as e:
                print(g(ERR_SPAWN) % command)
                print(e)

    # show a context menu for the treeview on right-click
    def __on_button_pressed_cb(self, e):
        # right mouse button
        if e.button == MouseButtons.RIGHT:
            self.popup_menu.popup(None, None, None, None, e.button, e.time)
            return True
        return False

    # collect options and write them into the json file
    def __apply_cb(self):
        cfgdir = Gio.file_new_for_path(GLib.path_get_dirname(
                self.file.get_path()))

        if cfgdir.query_exists(None):
            if (cfgdir.query_file_type(Gio.FileQueryInfoFlags.NONE, None) !=
                    Gio.FileType.DIRECTORY):
                self.__show_error(g(ERR_TITLE), g(ERR_BASE_NOT_DIR))
                return
        else:
            try:
                cfgdir.make_directory_with_parents(None)
            except GObject.GError as e:
                self.__show_error(g(ERR_TITLE), g(ERR_CANT_MKDIR))
                return

        # collect new data from the status of the widgets. in this way we
        # can also ditch eventual unnecessary data previously read
        self.options = {}
        self.options['use-default-profile'] = self.def_profile.get_active()
        self.options['split-profile-view'] = self.split_view.get_active()
        self.options['show-icons'] = self.show_icons.get_active()
        self.options['hide-entries-not-in-xdg-dir'
                ] = self.hide_non_xdg.get_active()
        self.options['icon-size'] = int(
                round(self.icon_size_spin.get_value()))
        self.options['profiles'] = []
        def collect_profiles(model, path, i, rows=None):
            indices = path.get_indices()
            index = indices[0]
            # we need to add a new empty dict to the list
            self.options['profiles'].append({})
            self.options['profiles'][index][
                    'name'] = model.get_value(i, COLUMN['name'])
            self.options['profiles'][index][
                    'directory'] = model.get_value(i, COLUMN['dir'])
            return False
        args = []
        self.profile_store.foreach(collect_profiles, args)

        write_error = None
        try:
            encoded = str.encode(json.dumps(self.options))
            GLib.file_set_contents(self.file.get_path(), encoded)
        except GObject.GError as write_error:
            text = (g(ERR_FILE_WRITE) % (self.file.get_path(), write_error))
            self.__show_error(g(ERR_TITLE), text)
            return
        self.__set_changed(False)

    # reload options from the json file ditching changes
    def __reload_cb(self):
        dialog = Gtk.Dialog()
        dialog.set_title(g(RELOAD_DIALOG))
        dialog.set_modal(True)
        dialog.set_destroy_with_parent(True)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        dialog.get_content_area().add(Gtk.Label(g(RELOAD_TEXT)))
        dialog.set_transient_for(self.win)
        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.CANCEL:
            dialog.destroy()
        else:
            dialog.destroy()
            self.__disconnect_all()
            self.profile_store.clear()
            self.__set_changed(False)
            self.__load_config_from_file(self.file)
            self.__connect_all()
            self.selection.emit('changed')

    # quit the app or show a confirm dialog in case of changes
    def __quit_cb(self):
        if self.config_changed:
            # emulating gtk_dialog_new_with_buttons()
            dialog = Gtk.Dialog()
            dialog.set_title(g(QUIT_DIALOG))
            dialog.set_modal(True)
            dialog.set_destroy_with_parent(True)
            dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

            dialog.set_default_response(Gtk.ResponseType.CANCEL)
            dialog.get_content_area().add(Gtk.Label(g(QUIT_TEXT)))
            dialog.set_transient_for(self.win)
            dialog.show_all()

            if dialog.run() == Gtk.ResponseType.CANCEL:
                dialog.destroy()
                return True
            
            self.win.destroy()
            return False

        self.win.destroy()
        return False

    def __on_select_cb(self):
        val = self.selection.count_selected_rows()
        self.item_edit.set_sensitive(val)
        self.item_browse.set_sensitive(val)
        self.item_delete.set_sensitive(val)
        self.item_manage.set_sensitive(val)
        self.tbtn_edit.set_sensitive(val)
        self.tbtn_browse.set_sensitive(val)
        self.tbtn_del.set_sensitive(val)
        self.tbtn_manage.set_sensitive(val)

    def __on_default_profile_toggle_cb(self):
        self.__set_changed(True)
        self.manage_default.set_sensitive(self.def_profile.get_active())

    # connect widgets to signals
    def __connect_all(self):
        self.id.append(self.def_profile.connect('notify::active', lambda t, d:
                self.__on_default_profile_toggle_cb()))
        self.id.append(self.split_view.connect('notify::active', lambda t, d:
                self.__set_changed(True)))
        self.id.append(self.show_icons.connect('notify::active', lambda t, d:
                self.__set_changed(True)))
        self.id.append(self.icon_size_spin.connect('value-changed', lambda s:
                self.__set_changed(True)))
        self.id.append(self.name_column.connect('edited', lambda c, p, n:
                self.__on_edit_done_cb(p, n, COLUMN['name'])))
        self.id.append(self.dir_column.connect('edited', lambda c, p, n:
                self.__on_edit_done_cb(p, n, COLUMN['dir'])))
        self.id.append(self.button_reload.connect('clicked', lambda w:
                self.__reload_cb()))
        self.id.append(self.button_apply.connect('clicked', lambda w:
                self.__apply_cb()))
        self.id.append(self.hide_non_xdg.connect('notify::active', lambda t, d:
                self.__set_changed(True)))
        self.id.append(self.selection.connect('changed', lambda d:
                self.__on_select_cb()))

    # disconnect widgets from signals. needed in case of file reloading
    def __disconnect_all(self):
        self.def_profile.disconnect(self.id.popleft())
        self.split_view.disconnect(self.id.popleft())
        self.show_icons.disconnect(self.id.popleft())
        self.icon_size_spin.disconnect(self.id.popleft())
        self.name_column.disconnect(self.id.popleft())
        self.dir_column.disconnect(self.id.popleft())
        self.button_reload.disconnect(self.id.popleft())
        self.button_apply.disconnect(self.id.popleft())
        self.hide_non_xdg.disconnect(self.id.popleft())
        self.selection.disconnect(self.id.popleft())

    # change option status
    def __set_changed(self, val):
        self.config_changed = val
        self.button_reload.set_sensitive(val)
        self.button_apply.set_sensitive(val)

    # this does exactly what it says, except connecting the widget signals
    def __build_main_window(self):
        self.__build_popup()

        notebook = Gtk.Notebook()
        notebook.append_page(self.__build_controls(),
                Gtk.Label(g(TAB_1_LABEL)))
        notebook.append_page(self.__build_profile_section(),
                Gtk.Label(g(TAB_2_LABEL)))

        # the whole window contents in a box
        win_vbox = Gtk.VBox(homogeneous = False, spacing = SPACING)
        win_vbox.pack_start(notebook, True, True, PADDING)
        win_vbox.pack_start(self.__build_button_row(), False, True, PADDING)
        self.button_close.grab_focus()

        win = Gtk.Window(type = Gtk.WindowType.TOPLEVEL)
        win.set_title(g(WINDOW_TITLE))
        win.set_size_request(SIZE['x'], SIZE['y'])
        win.add(win_vbox)
        
        win.set_border_width(PADDING)
        win.set_position(Gtk.WindowPosition.CENTER)
        pixbuf = win.render_icon(Gtk.STOCK_PREFERENCES, Gtk.IconSize.DIALOG)
        win.set_icon(pixbuf)
        win.connect('delete-event', lambda w, e: self.__quit_cb())
        return win

    # build a popup menu for the tree view
    def __build_popup(self):
        self.popup_menu = Gtk.Menu()
        self.item_new = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_NEW, None)
        self.item_new.set_label(g(NEW_PROFILE_TEXT))
        self.item_new.connect('activate', lambda d:
                self.__on_new_cb())
        self.popup_menu.add(self.item_new)
        self.item_edit = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_EDIT, None)
        self.item_edit.set_label(g(EDIT_PROFILE_TEXT))
        self.item_edit.set_sensitive(False)
        self.item_edit.connect('activate', lambda d:
                self.__on_edit_cb())
        self.popup_menu.add(self.item_edit)
        self.item_browse = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_OPEN,
                None)
        self.item_browse.set_label(g(BROWSE_PROFILE_TEXT))
        self.item_browse.set_sensitive(False)
        self.item_browse.connect('activate', lambda d:
                self.__on_browse_cb())
        self.popup_menu.add(self.item_browse)
        self.item_delete = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_DELETE,
                None)
        self.item_delete.set_label(g(DELETE_PROFILE_BTN_TEXT))
        self.item_delete.set_sensitive(False)
        self.item_delete.connect('activate', lambda d:
                self.__on_delete_cb())
        self.popup_menu.add(self.item_delete)
        self.item_manage = Gtk.ImageMenuItem.new_from_stock(
            Gtk.STOCK_PREFERENCES, None)
        self.item_manage.set_label(g(MANAGE_PROFILE_TEXT))
        self.item_manage.set_sensitive(False)
        self.popup_menu.add(self.item_manage)
        self.popup_menu.show_all()

    # create and place the widgets for the upper part of the dialog
    def __build_controls(self):
        icon_size_label = Gtk.Label(g(ICON_SIZE_TEXT))
        self.icon_size_spin = Gtk.SpinButton.new_with_range(SPIN_START,
            SPIN_END, SPIN_STEP)
        
        def_profile_label = Gtk.Label(g(DEF_PROFILE_TEXT))
        self.def_profile = Gtk.Switch()
        
        split_view_label = Gtk.Label(g(SPLIT_VIEW_TEXT))
        self.split_view = Gtk.Switch()
        
        show_icons_label = Gtk.Label(g(SHOW_ICONS_TEXT))
        self.show_icons = Gtk.Switch()
        
        hide_non_xdg_label = Gtk.Label(g(HIDE_NON_XDG_TEXT))
        self.hide_non_xdg = Gtk.Switch()
        
        self.manage_default = Gtk.Button(g(MANAGE_DEFAULT))
        
        manage_default_label = Gtk.Label(g(MANAGE_DEFAULT))
        self.manage_default = Gtk.Button.new_from_stock(Gtk.STOCK_OPEN)
        self.manage_default.connect('clicked', lambda w:
                GLib.spawn_command_line_async(HANDLE_MAIN_PROFILE_CMD))
        
        table = Gtk.Table(TableSize.ROWS, TableSize.COLUMNS, False)

        top_attach = 0
        bottom_attach = 1

        def add_row(label, control, y1, y2):
            table.attach(label, ColumnAttach.LEFT, ColumnAttach.CENTER, y1, y2,
                Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND,
                Gtk.AttachOptions.SHRINK, PADDING, PADDING)
            table.attach(control, ColumnAttach.CENTER, ColumnAttach.RIGHT,
                y1, y2, Gtk.AttachOptions.FILL, Gtk.AttachOptions.SHRINK,
                PADDING, PADDING)
            label.set_alignment(MiscAlignment.LEFT, MiscAlignment.CENTER)
            return [ y1 + 1, y2 + 1]
        
        [ top_attach, bottom_attach ] = add_row(def_profile_label,
            self.def_profile, top_attach, bottom_attach)
        [ top_attach, bottom_attach ] = add_row(split_view_label,
            self.split_view, top_attach, bottom_attach)
        [ top_attach, bottom_attach ] = add_row(show_icons_label,
            self.show_icons, top_attach, bottom_attach)
        [ top_attach, bottom_attach ] = add_row(hide_non_xdg_label,
            self.hide_non_xdg, top_attach, bottom_attach)
        [ top_attach, bottom_attach ] = add_row(icon_size_label,
            self.icon_size_spin, top_attach, bottom_attach)
        [ top_attach, bottom_attach ] = add_row(manage_default_label,
            self.manage_default, top_attach, bottom_attach)

        table.set_property('row-spacing', SPACING)
        table.set_property('column-spacing', SPACING)
        table.set_property('border-width', 2 * PADDING)
        
        return table

    # create and place the buttons for the bottom part of the dialog
    def __build_button_row(self):
        # leftward button
        self.button_reload = Gtk.Button.new_with_label(g(RELOAD_BTN_TEXT))
        image = Gtk.Image.new_from_stock(Gtk.STOCK_REFRESH, Gtk.IconSize.BUTTON)
        self.button_reload.set_image(image)

        button_box1 = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
        button_box1.pack_start(self.button_reload, False, True, PADDING)
        button_box1.set_layout(Gtk.ButtonBoxStyle.START)
        button_box1.set_spacing(SPACING)
        self.button_reload.set_sensitive(False)

        # rightward buttons
        self.button_apply = Gtk.Button.new_from_stock(Gtk.STOCK_APPLY)
        self.button_close = Gtk.Button.new_from_stock(Gtk.STOCK_CLOSE)
        self.button_close.connect('clicked', lambda w:
                self.__quit_cb())
        button_box2 = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
        button_box2.pack_start(self.button_apply, False, True, PADDING)
        button_box2.pack_start(self.button_close, False, True, PADDING)
        button_box2.set_layout(Gtk.ButtonBoxStyle.END)
        button_box2.set_spacing(SPACING)
        self.button_apply.set_sensitive(False)

        # put the whole row in a box
        button_hbox = Gtk.HBox(True, SPACING)
        button_hbox.pack_start(button_box1, False, True, PADDING)
        button_hbox.pack_start(button_box2, False, True, PADDING)

        return button_hbox

    # create and setup the tree view
    def __build_profile_section(self):
        self.profile_store = Gtk.ListStore(
                GObject.type_from_name('gchararray'),
                GObject.type_from_name('gchararray'))

        self.profile_view = Gtk.TreeView();
        self.profile_view.set_model(self.profile_store)
        self.name_column = Gtk.CellRendererText()
        self.name_column.set_property('editable', True)
        
        # emulating gtk_tree_view_insert_column_with_attributes()
        column1 = Gtk.TreeViewColumn()
        column1.set_title(g(PROFILE_NAME))
        column1.pack_start(self.name_column, True)
        column1.add_attribute(self.name_column, 'text', COLUMN['name'])
        self.profile_view.insert_column(column1, ColumnIds.LEFT)
        column1.set_sort_column_id(ColumnIds.LEFT)

        self.dir_column = Gtk.CellRendererText()
        self.dir_column.set_property('editable', True)

        # emulating gtk_tree_view_insert_column_with_attributes()
        column2 = Gtk.TreeViewColumn()
        column2.set_title(g(PROFILE_DIR))
        column2.pack_start(self.dir_column, True)
        column2.add_attribute(self.dir_column, 'text', COLUMN['dir'])
        self.profile_view.insert_column(column2, ColumnIds.RIGHT)
        column2.set_sort_column_id(ColumnIds.RIGHT)

        column1.set_resizable(True)
        column2.set_resizable(True)

        sw = Gtk.ScrolledWindow(None, None)
        sw.add(self.profile_view)

        self.selection = self.profile_view.get_selection()
        self.profile_view.connect('button-press-event',
                lambda w, e: self.__on_button_pressed_cb(e))

        self.tbtn_new = Gtk.ToolButton.new_from_stock(Gtk.STOCK_NEW)
        self.tbtn_new.set_tooltip_text(g(NEW_PROFILE_TEXT))
        self.tbtn_edit = Gtk.ToolButton.new_from_stock(Gtk.STOCK_EDIT)
        self.tbtn_edit.set_tooltip_text(g(EDIT_PROFILE_TEXT))
        self.tbtn_browse = Gtk.ToolButton.new_from_stock(Gtk.STOCK_OPEN)
        self.tbtn_browse.set_tooltip_text(g(BROWSE_PROFILE_TEXT))
        self.tbtn_del = Gtk.ToolButton.new_from_stock(Gtk.STOCK_DELETE)
        self.tbtn_del.set_tooltip_text(g(DELETE_PROFILE_BTN_TEXT))
        self.tbtn_manage = Gtk.ToolButton.new_from_stock(Gtk.STOCK_PREFERENCES)
        self.tbtn_manage.set_tooltip_text(g(MANAGE_PROFILE_TEXT))
        self.tbtn_new.connect('clicked', lambda d:
                self.__on_new_cb())
        self.tbtn_edit.connect('clicked', lambda d:
                self.__on_edit_cb())
        self.tbtn_del.connect('clicked', lambda d:
                self.__on_delete_cb())
        self.tbtn_browse.connect('clicked', lambda d:
                self.__on_browse_cb())
        self.tbtn_manage.connect('clicked', lambda d:
                self.__on_manage_cb())
        self.item_manage.connect('activate', lambda d:
                self.__on_manage_cb())
        
        toolbar = Gtk.Toolbar()
        toolbar.set_orientation(Gtk.Orientation.HORIZONTAL)
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.add(self.tbtn_new)
        toolbar.add(self.tbtn_edit)
        toolbar.add(self.tbtn_browse)
        toolbar.add(self.tbtn_del)
        toolbar.add(self.tbtn_manage)
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        self.tbtn_edit.set_sensitive(False)
        self.tbtn_browse.set_sensitive(False)
        self.tbtn_del.set_sensitive(False)
        self.tbtn_manage.set_sensitive(False)

        hbox = Gtk.VBox(False, SPACING)
        hbox.pack_start(toolbar, False, False, 0)
        hbox.pack_start(sw, True, True, 0)

        return hbox

    # fetch data from the json file and eventually fix them in case of
    # inconsistencies
    def __load_config_from_file(self, file):
        file_name = file.get_path()

        self.options = {}
        self.__set_changed(False)

        if not (file.query_exists(None)):
            self.__show_error(g(ERR_TITLE),
                    (g(ERR_FILE_NOT_FOUND) % file_name))
            self.options = DEFAULT_OPTIONS
            self.__set_changed(True)
        else:
            try:
                ret, data, _ = file.load_contents(None)
            except GObject.GError as e:
                self.__show_error(g(ERR_TITLE),
                        (g(ERR_FILE_UNREADABLE) % file_name))
                self.__set_changed(True)
                self.options = DEFAULT_OPTIONS
            else:
                try:
                    self.options = json.loads(data.decode('utf-8'))
                except ValueError as e:
                    self.__show_error(g(ERR_TITLE), 
                            g(ERR_BAD_FORMAT) % file_name)
                    self.__set_changed(True)
                    self.options = DEFAULT_OPTIONS

        # check and fix wrong values and data types taking care not to
        # overwrite the eventually already retrieved settings
        def check_and_set(node, key, type_str, value):
            ret = False
            try:
                if type(node[key]).__name__ != type_str:
                    node[key] = value
                    self.__set_changed(True)
                    ret = True
            except KeyError as key_error:
                node[key] = value
                self.__set_changed(True)
                ret = True
            return ret

        error1_text = ''
        keys = []
        if check_and_set(self.options, 'use-default-profile', 'bool',
                DEFAULT_OPTIONS['use-default-profile']):
            keys.append('use-default-profile')
        if check_and_set(self.options, 'split-profile-view', 'bool',
                DEFAULT_OPTIONS['split-profile-view']):
            keys.append('split-profile-view')
        if check_and_set(self.options, 'show-icons', 'bool',
                DEFAULT_OPTIONS['show-icons']):
            keys.append('show-icons')
        if check_and_set(self.options, 'hide-entries-not-in-xdg-dir', 'bool',
                DEFAULT_OPTIONS['hide-entries-not-in-xdg-dir']):
            keys.append('hide-entries-not-in-xdg-dir')
        if check_and_set(self.options, 'icon-size', 'int',
                DEFAULT_OPTIONS['icon-size']):
            keys.append('icon-size')
        if check_and_set(self.options, 'profiles', 'list',
                DEFAULT_OPTIONS['profiles']):
            keys.append('profiles')
        if keys != []:
            error1_text = g(ERR_KEYS_START)
            for i in range(len(keys)):
                error1_text += keys[i] + '\n'
            error1_text += '\n'

        # destroy the invalid array entries
        i = 0
        j = 0
        error2_text = ''
        # python3 identifies all the strings as 'str'
        type_str = 'str' if sys.version_info.major >= 3 else 'unicode'
        while i < len(self.options['profiles']):
            if (check_and_set(self.options['profiles'][i], 'name', type_str,
                    '')) or (check_and_set(self.options['profiles'][i],
                    'directory', type_str, '')):
                del self.options['profiles'][i : i + 1]
                error2_text += (g(ERR_BAD_PROFILE) % (j + 1))
            else:
                i += 1
            j += 1
        if error2_text != '':
            error2_text = g(ERR_ENTRY_START) % error2_text

        error_text = error1_text + error2_text
        if error_text != '':
            self.__show_error(g(ERR_TITLE), error_text)

        # setup ui according to the options
        self.icon_size_spin.set_value(self.options['icon-size'])
        self.def_profile.set_active(self.options['use-default-profile'])
        self.manage_default.set_sensitive(self.options['use-default-profile'])
        self.split_view.set_active(self.options['split-profile-view'])
        self.show_icons.set_active(self.options['show-icons'])
        self.hide_non_xdg.set_active(
                self.options['hide-entries-not-in-xdg-dir'])
        for i in range(len(self.options['profiles'])):
            it = self.profile_store.append()
            self.profile_store.set_value(it, COLUMN['name'],
                    self.options['profiles'][i]['name'])
            self.profile_store.set_value(it, COLUMN['dir'],
                    self.options['profiles'][i]['directory'])

def main():
    default_path = GLib.build_filenamev(DEFAULT_OPTION_FILE_PARTS)

    # look for an existing locale directory
    data_dirs = [ GLib.path_get_dirname(default_path) ]
    data_dirs += GLib.get_system_data_dirs()
    locale_dir = None

    for i in range(len(data_dirs)):
        directory = GLib.build_filenamev([data_dirs[i], LOCALE_SUBDIR])

        if (gettext.find(EXTENSION_UUID, directory) != None):
            locale_dir = directory
            gettext.bindtextdomain(EXTENSION_UUID, directory)
            break

    parser = OptionParser(g(ERR_USAGE),
        description = "",
        option_list = [
            make_option('--file', '-f',
                type = 'filename',
                action = 'store',
                dest = 'filename',
                help=g(ERR_FILE_HELP)
            )
        ])
    try:
        parser.parse_args()
    except Exception as e:
        sys.stderr.write("%s\n" % g(ERR_WRONG_ARGS))
        return

    if parser.values.filename == None:
        filename = default_path
        sys.stderr.write(g(WARN_DEF_OPT_FILE) % filename)
    else:
        filename = parser.values.filename

    configurator = Configurator(filename, locale_dir)
    configurator.run(None)

if __name__ == '__main__':
    main()

