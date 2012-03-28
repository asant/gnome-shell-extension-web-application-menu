/* -*- mode: js2 - indent-tabs-mode: nil - js2-basic-offset: 4 -*- */
/*
 * GNOME Shell extension that aims at showing web applications from many
 * Epiphany profiles, in a drop-down menu located on the Shell's top panel.
 * Copyright (C) 2012  Andrea Santilli <andresantilli gmx com>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
 * USA.
 */

const Gio       = imports.gi.Gio; 
const GLib      = imports.gi.GLib;
const Lang      = imports.lang;
const Main      = imports.ui.main;
const PanelMenu = imports.ui.panelMenu;
const PopupMenu = imports.ui.popupMenu;
const Shell     = imports.gi.Shell;
const St        = imports.gi.St;

/* from epiphany (which took it from libgnome in its turn) */
const GNOME_DOT_GNOME       = '.gnome2';
const APP_NAME              = 'epiphany';
const APP_PREFIX            = 'app-';
const DIR_PREFIX            = APP_PREFIX + APP_NAME + '-';
const ENTRY_EXT             = '.desktop';
const GNOME_ENV             = 'GNOME';
const LOCALE_SUBDIR         = 'locale';
const LOCALE_EXT            = '.mo';
const MSG_SUBDIR            = 'LC_MESSAGES';
const SETTINGS_FILENAME     = 'settings.json';
const SETUP                 = 'webappmenu-setup.py';
const EXT_STATUS_AREA_ID    = 'webapps';
const MENU_ALIGNMENT        = 0.5;
const XDG_APP_DIR_PERMS     = 750;
const FIELD_SIZE            = 1;
const NEW_API_VERSION       = '3.3.5';

/* default values */
const DEFAULT_ICON_SIZE                     = 16;
const DEFAULT_SHOW_ICONS                    = true;
const DEFAULT_USE_DEFAULT_PROFILE           = true;
const DEFAULT_SPLIT_PROFILE_VIEW            = true;
const DEFAULT_HIDE_ENTRIES_NOT_IN_XDG_DIR   = true;

/* text */
const BROWSE_TEXT       = "Browse your Web Applications"
const CONFIGURE_TEXT    = "Advanced settings";

/* warning messages */
const WARNING_CHANGED_FILE      = "Configuration file changed!!!";
const WARNING_UNEXISTING_FILE   = "WARNING: file \"%s\" does not exist.";

/* error messages */
const ERROR_MKDIR_FAILED    = "ERROR: could not make directory \"%s\".";
const ERROR_MONITOR         = "ERROR: can't monitor configuration file.";
const ERROR_NOT_A_DIRECTORY = "ERROR: \"%s\" is not a directory.";
const ERROR_SPAWN           = "ERROR: could not run \"%s\"";
const ERROR_UNPARSABLE_FILE = "ERROR: could not parse \"%s\".";
const ERROR_UNREADABLE_FILE = "ERROR: could not read contents for file \"%s\".";

/* divide and conquer search function for menu item insertion in
 * alphabetical order, with submenus at the top */
function ab_insert(entry, split) {
    let children = this._getMenuItems();
    let is_submenu = (entry instanceof PopupMenu.PopupSubMenuMenuItem);

    if ((!children) || (children[0] == undefined)) {
        this._submenus = this._entries = 0;
        (is_submenu)?this._submenus++:this._entries++;
        this.addMenuItem(entry);
        return;
    }

    /* if we aren't splitting the menu, consider it all */
    let start = 0, end = this._submenus + this._entries - 1;
    /* otherwise, consider only the part we need to arrange */
    if (split) {
        if (is_submenu) {
            if (!this._submenus) {
                this.addMenuItem(entry, 0);
                this._submenus++;
                return;
            }
            start = 0;
            end = (!this._submenus)?0:this._submenus - 1;
        } else {
            if (!this._entries) {
                this.addMenuItem(entry, this._submenus);
                this._entries++;
                return;
            }
            start = this._submenus;
            end = this._submenus + this._entries - 1;
        }
    }

    /* case insensitive sorting */
    let cmp_text = entry.label.text.toLowerCase();

    if (cmp_text < children[start].label.text.toLowerCase()) {
        (is_submenu)?this._submenus++:this._entries++;
        this.addMenuItem(entry, start);
        return;
    }

    if (cmp_text > children[end].label.text.toLowerCase()) {
        (is_submenu)?this._submenus++:this._entries++;
        this.addMenuItem(entry, end + 1);
        return;
    }

    let mid = start;
    while ((start < end) && (end - start > 1)) {
        /* fetch the entry in the middle */
        mid = Math.floor((start + end) / 2);

        if (cmp_text < children[mid].label.text.toLowerCase()) {
            end = mid;
        } else {
            start = mid;
        }
    }

    /* at this point we have a subarray containing 2 elements */
    mid = start;
    if (cmp_text > children[mid].label.text.toLowerCase()) {
        mid++;
    }
    (is_submenu)?this._submenus++:this._entries++;
    this.addMenuItem(entry, mid);
}

/* slip the insertion function into these classes */
PopupMenu.PopupMenu.prototype.ab_insert = ab_insert;
PopupMenu.PopupSubMenu.prototype.ab_insert = ab_insert;

function WebAppMenuItem() {
    this._init.apply(this, arguments);
}

/* define the web app menu item class */
WebAppMenuItem.prototype = {
    __proto__: PopupMenu.PopupBaseMenuItem.prototype,

    _init: function(app, show_icons, icon_size, params) {
        PopupMenu.PopupBaseMenuItem.prototype._init.call(this, params);

        this.app = app;
        this.box = new St.BoxLayout({ style_class: 'popup-combobox-item' });
        if (show_icons) {
            this.icon = St.TextureCache.get_default().load_gicon(null,
                    app.get_icon(), icon_size);
            this.box.add(this.icon, {expand: true, x_fill: false,
                    y_fill: false, x_align: St.Align.END,
                    y_align: St.Align.MIDDLE });
        }
        this.label = new St.Label({ text: app.get_name() });
        this.box.add(this.label, {expand: true, x_fill: false, y_fill: false,
                x_align: St.Align.START, y_align: St.Align.MIDDLE });
        this.addActor(this.box);

        this.connect('activate', Lang.bind(this, function() {
            this.app.launch([], global.create_app_launch_context())
        }));
    }
};

function ConfiguratorItem() {
    this._init.apply(this, arguments);
}

/* define a new class for the configurator entry to easily detect its presence
 * later */
ConfiguratorItem.prototype = {
    __proto__: PopupMenu.PopupBaseMenuItem.prototype,

    _init: function(text, show_icons, icon_size, command, params) {
        PopupMenu.PopupBaseMenuItem.prototype._init.call(this, params);

        this.box = new St.BoxLayout({ style_class: 'popup-combobox-item' });
        if (show_icons) {
            this.icon = new St.Icon({
                icon_name: 'preferences-system',
                icon_type: St.IconType.FULLCOLOR,
                icon_size: icon_size
            });
            this.box.add(this.icon, {expand: true, x_fill: false,
                    y_fill: false, x_align: St.Align.END,
                    y_align: St.Align.MIDDLE });
        }
        this.label = new St.Label({ text: text });
        this.box.add(this.label, {expand: true, x_fill: false, y_fill: false,
                x_align: St.Align.START, y_align: St.Align.MIDDLE });
        this.addActor(this.box);

        this.connect('activate', Lang.bind(this, function() {
            if (!GLib.spawn_command_line_async(command, null)) {
                global.log(_(ERROR_SPAWN).format(command));
            }
        }));
    }
};

function WebAppExtension() {
    this._init.apply(this, arguments);
}

/* define our panel extension */
WebAppExtension.prototype = {
    __proto__: PanelMenu.Button.prototype,

    _init: function(metadata, params)
    {
        PanelMenu.Button.prototype._init.call(this, MENU_ALIGNMENT);

        /* setup according to the configuration file and monitor it for
         * changes */
        this.path = metadata.path;
        this.uuid = metadata.uuid;
        this.config_file_path = GLib.build_filenamev([metadata.path,
                SETTINGS_FILENAME]);
        this.config_file = Gio.file_new_for_path(this.config_file_path);
        this._setup_values();
        this.monitor = this.config_file.monitor_file(
                Gio.FileMonitorFlags.NONE, null, null);
        if (!this.monitor) {
            global.log(_(ERROR_MONITOR));
        } else {
            this.monitor.connect('changed', Lang.bind(this,
                function(monitor, file, other_file, event_type, data) {
                    global.log(_(WARNING_CHANGED_FILE));
                    this._setup_values();
                    this._redisplay(); 
                }));
        }

        this._icon = new St.Icon({ icon_name: 'user-bookmarks',
                                   icon_type: St.IconType.SYMBOLIC,
                                   style_class: 'system-status-icon' });
        this.actor.add_actor(this._icon);

        this._appSystem = Shell.AppSystem.get_default();
        this._display();

        this.sigcon = this._appSystem.connect('installed-changed',
                Lang.bind(this, this._redisplay));

        Main.panel.addToStatusArea(EXT_STATUS_AREA_ID, this);
        this.set_tooltip(_(BROWSE_TEXT));
        this.menu.connect('open-state-changed', Lang.bind(this,
                this._on_open_state_changed));
    },

    _on_open_state_changed: function() {
        /* if all the root menu contains is just a submenu, unroll it */
        if ((this.menu.isOpen) && (this.options['split-profile-view'])) {
            let children = this.menu._getMenuItems();

            if ((children.length == 3) && (children[0] instanceof
                    PopupMenu.PopupSubMenuMenuItem) && (children[1] instanceof
                    PopupMenu.PopupSeparatorMenuItem) && (children[2]
                    instanceof ConfiguratorItem)) {
                children[0].menu.open(true);
                children[0].setSensitive(false);
            }
        }
    },

    set_tooltip: function(text) {
        if (text != null) {
            this.tooltip = text;
            this.actor.has_tooltip = true;
            this.actor.tooltip_text = text;
        } else {
            this.actor.has_tooltip = false;
            this.tooltip = null;
        }
    },

    _setup_values: function() {
        let ret;
        let data;
        let i = 0;

        this.options = undefined;

        /* store settings in a JSON file until users can install gsettings
         * keys */
        if (!(this.config_file.query_exists(null))) {
            global.log(_(WARNING_UNEXISTING_FILE).format(this.path));
        } else {
            [ ret, data ] = this.config_file.load_contents(null);
            if (!ret) {
                global.log(_(ERROR_UNREADABLE_FILE).format(this.path));
            } else {
                try {
                    this.options = JSON.parse(data);
                } catch(e) {
                    global.log(_(ERROR_UNPARSABLE_FILE).format(this.path));
                }
            }
        }

        /* at this point we can't know how parsing went... */
        if (this.options == undefined) {
            this.options = {
                'use-default-profile': DEFAULT_USE_DEFAULT_PROFILE,
                'split-profile-view': DEFAULT_SPLIT_PROFILE_VIEW,
                'show-icons': DEFAULT_SHOW_ICONS,
                'icon-size': DEFAULT_ICON_SIZE,
                'profiles': []
            };
        }
        
        /* check and fix wrong values and data types taking care not to
         * overwrite the eventually already retrieved settings */
        if ((this.options['use-default-profile'] == undefined) ||
                (this.options['use-default-profile'].constructor != Boolean)) {
            this.options['use-default-profile'] = DEFAULT_USE_DEFAULT_PROFILE;
        }

        if ((this.options['split-profile-view'] == undefined) ||
                (this.options['split-profile-view'].constructor != Boolean)) {
            this.options['split-profile-view'] = DEFAULT_SPLIT_PROFILE_VIEW;
        }

        if ((this.options['show-icons'] == undefined) ||
                (this.options['show-icons'].constructor != Boolean)) {
            this.options['show-icons'] = DEFAULT_SHOW_ICONS;
        }

        if ((this.options['hide-entries-not-in-xdg-dir'] == undefined) ||
                (this.options['hide-entries-not-in-xdg-dir'].constructor !=
                Boolean)) {
            this.options['hide-entries-not-in-xdg-dir'] =
                    DEFAULT_HIDE_ENTRIES_NOT_IN_XDG_DIR;
        }

        if ((this.options['icon-size'] == undefined) ||
                (this.options['icon-size'].constructor != Number)) {
            this.options['icon-size'] = DEFAULT_ICON_SIZE;
        }

        if ((this.options['profiles'] == undefined) ||
                (this.options['profiles'].constructor != Array)) {
            this.options['profiles'] = [];
        }

        /* destroy the invalid array entries */
        while (i < this.options['profiles'].length) {
            if ((this.options['profiles'][i]['name'] == undefined) ||
                    (this.options['profiles'][i]['name'].constructor
                    != String) ||
                    (this.options['profiles'][i]['directory'] == undefined) ||
                    (this.options['profiles'][i]['directory'].constructor
                    != String)) {
                this.options['profiles'].splice(i, FIELD_SIZE);
            } else {
                i++;
            }
        }
    },

    _display: function() {
        /* handle the default profile */
        if ((this.options['use-default-profile'] != undefined) &&
                (this.options['use-default-profile'])) {
            this._build_entries_for_profile_dir(this.menu,
                    GLib.build_filenamev([ GLib.get_home_dir(),
                    GNOME_DOT_GNOME, APP_NAME ]));
        }

        for (let i = 0; i < this.options['profiles'].length; i++) {
            if (this.options['split-profile-view']) {
                let name = this.options['profiles'][i]['name'];
                let dir = this.options['profiles'][i]['directory'];
                let submenu = new PopupMenu.PopupSubMenuMenuItem(name);

                this._build_entries_for_profile_dir(submenu.menu, dir);
                if (submenu.menu._getMenuItems().length) {
                    this.menu.ab_insert(submenu, true);
                }
            } else {
                this._build_entries_for_profile_dir(this.menu,
                        this.options['profiles'][i]['directory']);

            }
        }

        /* no separator if there are no entries */
        if (this.menu._getMenuItems().length) {
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        }

        /* add entry for setup app */
        this.menu.addMenuItem(new ConfiguratorItem(_(CONFIGURE_TEXT),
                this.options['show-icons'], this.options['icon-size'],
                'python ' + GLib.build_filenamev([ this.path, SETUP ]) +
                ' -f ' + this.config_file_path));
    },

    _build_entries_for_profile_dir: function(submenu, config_path) {
        let path = Gio.file_new_for_path(config_path);
        let enumerator = null;
        let info = null;

        if (!(GLib.file_test(config_path, GLib.FileTest.IS_DIR))) {
            global.log(_(ERROR_NOT_A_DIRECTORY).format(config_path));
            return;
        }

	    enumerator = path.enumerate_children(Gio.FILE_ATTRIBUTE_STANDARD_NAME,
                Gio.FileQueryInfoFlags.NONE, null);

        while ((info = enumerator.next_file(null))) {
            let element = info.get_name();
            let full_path;
            let entry_name;
            let entry_path;
            let app;
            let menuitem;

            /* check whether the file name begins by app-epiphany- */
            if (!(GLib.str_has_prefix(element, DIR_PREFIX))) {
                continue;
            }

            full_path = GLib.build_filenamev([ config_path, element ]);
            /* check whether the file is a directory */
            if (!(GLib.file_test(full_path, GLib.FileTest.IS_DIR))) {
                continue;
            }

            /* try to build a valid entry for the desktop file
             * the full path name for the entry file is:
             *
             * [PDIR]/app-epiphany-[NAME]-[DIG]/epiphany-[NAME]-[DIG].desktop
             *
             * where:
             * PDIR is the profile directory;
             * NAME is the desktop entry name (Name key);
             * DIG is the wm_class-entry_name digest.
             * */
            entry_name = element.substring(APP_PREFIX.length) + ENTRY_EXT;
            entry_path =  GLib.build_filenamev([ full_path, entry_name ]);
            app = Gio.DesktopAppInfo.new_from_filename(entry_path);
            if (!app) {
                continue;
            }

            /* ditch the entry if hidden or not visible in gnome */
            if ((app.get_is_hidden()) || (!app.get_show_in(GNOME_ENV))) {
                continue;
            }

            if (this.options['hide-entries-not-in-xdg-dir']) {
                let xdg_path = GLib.build_filenamev([GLib.get_user_data_dir(),
                    'applications'])
                let xdgfile_path = GLib.build_filenamev([xdg_path, entry_name])
                let xdgfile = Gio.file_new_for_path(xdgfile_path);
                let xdgfile_info;

                if (GLib.mkdir_with_parents(xdg_path, XDG_APP_DIR_PERMS)) {
                    global.log(_(ERROR_MKDIR_FAILED).format(xdg_path));
                    continue;
                }

                if (!(GLib.file_test(xdgfile_path,
                        GLib.FileTest.IS_SYMLINK))) {
                    continue;
                }

                xdgfile_info = xdgfile.query_info('*',
                        Gio.FileQueryInfoFlags.NONE, null, null);

                if (xdgfile_info == null) {
                    continue;
                }

                if (xdgfile_info.get_symlink_target() != entry_path) {
                    continue;
                }
            }

            /* insert the entry in alphabetical order */
            menuitem = new WebAppMenuItem(app, this.options['show-icons'],
                    this.options['icon-size'], {});

            submenu.ab_insert(menuitem, this.options['split-profile-view']);
        }
    },

    _redisplay: function() {
        this.menu.removeAll();
        this.actor.show();
        this._display();
    },

    destroy: function()
    {
        this._appSystem.disconnect(this.sigcon);
        this.monitor.cancel();
        this.actor._delegate = null;
        this.menu.destroy();
        this.actor.destroy();
        this.emit('destroy');
    }
};

let webapps;
let md;
let _;

function init_localizations(metadata) {
    let langs = GLib.get_language_names();
    let locale_dirs = new Array(GLib.build_filenamev([metadata.path,
            LOCALE_SUBDIR]));
    let domain;

    /* check whether we're using the right shell version before trying to fetch 
     * its locale directory and other info */
    if (imports.misc.config.PACKAGE_VERSION < NEW_API_VERSION) {
        domain = metadata['gettext-domain'];
        locale_dirs = locale_dirs.concat([ metadata['system-locale-dir'] ]);
    } else {
        domain = metadata.metadata['gettext-domain'];
        locale_dirs = locale_dirs.concat([ imports.misc.config.LOCALEDIR ]);
    }

    _ = imports.gettext.domain(domain).gettext;

    for (let i = 0; i < locale_dirs.length; i++) {
        dir = Gio.file_new_for_path(locale_dirs[i]);

        if (dir.query_file_type(Gio.FileQueryInfoFlags.NONE, null) ==
                Gio.FileType.DIRECTORY) {
            imports.gettext.bindtextdomain(domain, locale_dirs[i]);
            return;
        }
    }
}

function init(metadata) {
    md = metadata;
    init_localizations(metadata);
}

function enable() {
    webapps = new WebAppExtension(md);
}

function disable() {
    webapps.destroy();
}

