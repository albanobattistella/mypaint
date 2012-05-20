# This file is part of MyPaint.
# Copyright (C) 2012 by Andrew Chadwick <andrewc-git@piffle.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


"""Palette: a list of swatch colours.
"""


import re
import os
from copy import copy

import gtk
from gtk import gdk
from gettext import gettext as _

from uicolor import RGBColor
from adjbases import ColorAdjusterWidget



class Palette:
    """A flat list of colour swatches.

    As a (sideways-compatible) extension to the GIMP's format, MyPaint supports
    empty slots in the palette. These slots are represented by pure black
    swatches with the name ``__NONE__``.

    Palette objects can be serialized in the GIMP's file format (the regular
    `unicode()` function on a Palette will do this too), or converted to and
    from a simpler JSON-ready representation for storing in the MyPaint prefs.
    Support for loading and saving via modal dialogs is defined here too.

    """

    # Class-level constants
    __EMPTY_SLOT_ITEM = RGBColor(-1, -1, -1)
    __EMPTY_SLOT_NAME = "__NONE__"

    # Instance vars
    __columns = 0   #: Number of columns. 0 means "natural flow".
    __colors = None  #: List of named colours.
    __name = None   #: Name of the palette, as a Unicode string.


    def __init__(self, filehandle=None, filename=None):
        """Instantiate, possibly from a file.

          >>> Palette()
          <Palette colors=0, columns=0, name=None>
        """
        self.clear()
        if filehandle:
            self.load(filehandle)
        elif filename:
            fp = open(filename, "r")
            self.load(fp)
            fp.close()


    def clear(self):
        """Resets the palette to its initial state."""
        self.__colors = []
        self.__columns = 0
        self.__name = None


    def load(self, filehandle):
        """Load contents from a file handle containing a GIMP palette.

        If the format is incorrect, a `RuntimeError` will be raised.
        """
        comment_line_re = re.compile(r'^#')
        field_line_re = re.compile(r'^(\w+)\s*:\s*(.*)$')
        color_line_re = re.compile(r'^(\d+)\s+(\d+)\s+(\d+)\s*(?:\b(.*))$')
        fp = filehandle
        self.clear()
        line = fp.readline()
        if line.strip() != "GIMP Palette":
            raise RuntimeError, "Not a valid GIMP Palette"
        header_done = False
        line_num = 0
        for line in fp:
            line = line.strip()
            line_num += 1
            if line == '':
                continue
            if comment_line_re.match(line):
                continue
            if not header_done:
                match = field_line_re.match(line)
                if match:
                    key, value = match.groups()
                    key = key.lower()
                    if key == 'name':
                        self.__name = value
                    elif key == 'columns':
                        self.__columns = int(value)
                    else:
                        print "warning: unknown 'key: value' pair '%s'" % line
                    continue
                else:
                    header_done = True
            match = color_line_re.match(line)
            if not match:
                print "warning: expected R G B [Name]"
                continue
            r, g, b, col_name = match.groups()
            r = float(r)/256
            g = float(g)/256
            b = float(b)/256
            if r == g == b == 0 and col_name == self.__EMPTY_SLOT_NAME:
                self.append(None)
            else:
                col = RGBColor(r, g, b)
                self.append(col, col_name)


    def get_columns(self):
        """Get the number of columns (0 means unspecified)."""
        return self.__columns


    def set_columns(self, n):
        """Set the number of columns (0 means unspecified)."""
        self.__columns = int(n)


    def set_name(self, name):
        """Sets the palette's name.
        """
        if name is not None:
            name = unicode(name)
        self.__name = name


    def get_name(self):
        """Gets the palette's name.
        """
        return self.__name


    def __copy_color_out(self, col):
        if col is self.__EMPTY_SLOT_ITEM:
            return None
        result = RGBColor(color=col)
        result.__name = col.__name
        return result


    def __copy_color_in(self, col, name=None):
        if col is None:
            result = self.__EMPTY_SLOT_ITEM
        else:
            if name is None:
                try:
                    name = col.__name
                except AttributeError:
                    pass
            if name is not None:
                name = unicode(name)
            result = RGBColor(color=col)
            result.__name = name
        return result


    def append(self, col, name=None):
        """Appends a colour, setting an optional name for it.
        """
        col = self.__copy_color_in(col, name)
        self.__colors.append(col)



    def insert(self, i, col, name=None):
        """Inserts a colour, setting an optional name for it.

        Empty slots can be inserted by setting `col` to `None`.

        """
        col = self.__copy_color_in(col, name)
        if i is None:
            self.__colors.append(col)
        else:
            self.__colors.insert(i, col)


    def move(self, src_i, targ_i):
        if src_i == targ_i:
            return
        try:
            col = self.__colors[src_i]
            assert col is not None  # just in case we change the internal repr
        except IndexError:
            return

        if targ_i is not None:
            targ = self.__colors[targ_i]
            if targ is self.__EMPTY_SLOT_ITEM:
                self.__colors[targ_i] = self.__copy_color_in(col)
                return

        self.__colors.pop(src_i)
        if targ_i is None:
            self.__colors.append(col)
        else:
            self.__colors.insert(targ_i, col)


    def pop(self, i):
        """Removes a colour, returning it
        """
        try:
            col = self.__colors.pop(i)
            return self.__copy_color_out(col)
        except IndexError:
            return None


    def get_color(self, i):
        """Looks up a colour by its list index.
        """
        if i is None:
            return None
        try:
            col = self.__colors[i]
            return self.__copy_color_out(col)
        except IndexError:
            return None


    def __getitem__(self, i):
        return self.get_color(i)


    def __setitem__(self, i, col):
        self.__colors[i] = self.__copy_color_in(col, None)


    def get_color_name(self, i):
        """Looks up a colour's name by its list index.
        """
        try:
            col = self.__colors[i]
            if col is self.__EMPTY_SLOT_ITEM:
                return None
            return col.__name
        except IndexError:
            return None


    def set_color_name(self, i, name):
        """Sets a colour's name by its list index.
        """
        try:
            col = self.__colors[i]
            if col is self.__EMPTY_SLOT_ITEM:
                return
            col.__name = name
        except IndexError:
            pass


    def get_color_by_name(self, name):
        """Looks up the first colour with the given name.

          >>> pltt = Palette()
          >>> pltt.append(RGBColor(1,0,1), "Magenta")
          >>> pltt.get_color_by_name("Magenta")
          <RGBColor r=1.0000, g=0.0000, b=1.0000>

        """
        for col in self:
            if col.__name == name:
                return RGBColor(color=col)


    def save(self, filehandle):
        """Saves the palette to an open file handle.

        The file handle is not flushed, and is left open after the write.

        """
        filehandle.write(unicode(self))


    def __len__(self):
        return len(self.__colors)


    def __unicode__(self):
        result = u"GIMP Palette\n"
        if self.__name is not None:
            result += u"Name: %s\n" % self.__name
        if self.__columns > 0:
            result += u"Columns: %d\n" % self.__columns
        result += u"#\n"
        for col in self.__colors:
            if col is self.__EMPTY_SLOT_ITEM:
                col_name = self.__EMPTY_SLOT_NAME
                r = g = b = 0
            else:
                col_name = col.__name
                r, g, b = [int(c*256) for c in col.get_rgb()]
            result += u"%d %d %d    %s\n" % (r, g, b, col_name)
        return result


    def __iter__(self):
        return self.iter_colors()


    def iter_colors(self):
        for col in self.__colors:
            if col is self.__EMPTY_SLOT_ITEM:
                yield None
            else:
                yield col


    def __copy__(self):
        clone = Palette()
        clone.set_name(self.get_name())
        clone.set_columns(self.get_columns())
        for col in self.__colors:
            if col is self.__EMPTY_SLOT_ITEM:
                clone.append(None)
            else:
                clone.append(copy(col), col.__name)
        return clone


    def __deepcopy__(self, memo):
        return self.__copy__()


    def __repr__(self):
        return u"<Palette colors=%d, columns=%d, name=%s>" \
          % (len(self.__colors), self.__columns, repr(self.__name))


    def to_simple_dict(self):
        """Converts the palette to a simple dict form used in the prefs.
        """
        simple = {}
        simple["name"] = self.get_name()
        simple["columns"] = self.get_columns()
        entries = []
        for col in self.iter_colors():
            if col is None:
                entries.append(None)
            else:
                name = col.__name
                entries.append((col.to_hex_str(), name))
        simple["entries"] = entries
        return simple


    @classmethod
    def new_from_simple_dict(class_, simple):
        """Constructs and returns a palette from the simple dict form.
        """
        pal = class_()
        pal.set_name(simple.get("name", None))
        pal.set_columns(simple.get("columns", None))
        for entry in simple.get("entries", []):
            if entry is None:
                pal.append(None)
            else:
                s, name = entry
                col = RGBColor.new_from_hex_str(s)
                pal.append(col, name)
        return pal


    @classmethod
    def load_via_dialog(class_, title, parent=None):
        """Runs a file chooser dialog, returning a palette or `None`.

        The dialog is both modal and blocking. Set `parent` to provide a parent
        window, and `title` for the dialog title.

        """
        dialog = gtk.FileChooserDialog(
          title=title,
          parent=parent,
          action=gtk.FILE_CHOOSER_ACTION_OPEN,
          buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                   gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT),
          )
        dialog.set_do_overwrite_confirmation(True)
        filter = gtk.FileFilter()
        filter.add_pattern("*.gpl")
        filter.set_name(_("GIMP palette file (*.gpl)"))
        dialog.add_filter(filter)
        filter = gtk.FileFilter()
        filter.add_pattern("*")
        filter.set_name(_("All files (*)"))
        dialog.add_filter(filter)
        response_id = dialog.run()
        palette = None
        if response_id == gtk.RESPONSE_ACCEPT:
            filename = dialog.get_filename()
            palette = Palette(filename=filename)
        dialog.destroy()
        return palette


    def save_via_dialog(self, title, parent=None):
        """Runs a file chooser dialog for saving.

        The dialog is both modal and blocking. Set `parent` to provide a parent
        window, and `title` for the dialog title. This function returns True if
        the file was saved successfully.

        """
        dialog = gtk.FileChooserDialog(
          title=title,
          parent=parent,
          action=gtk.FILE_CHOOSER_ACTION_SAVE,
          buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                   gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT),
          )
        dialog.set_do_overwrite_confirmation(True)
        filter = gtk.FileFilter()
        filter.add_pattern("*.gpl")
        filter.set_name(_("GIMP palette file (*.gpl)"))
        dialog.add_filter(filter)
        filter = gtk.FileFilter()
        filter.add_pattern("*")
        filter.set_name(_("All files (*)"))
        dialog.add_filter(filter)
        response_id = dialog.run()
        result = False
        if response_id == gtk.RESPONSE_ACCEPT:
            filename = dialog.get_filename()
            filename = re.sub(r'[.]?(?:[Gg][Pp][Ll])?$', "", filename)
            palette_name = os.path.basename(filename)
            filename += ".gpl"
            fp = open(filename, 'w')
            self.save(fp)
            fp.flush()
            fp.close()
            result = True
        dialog.destroy()
        return result


if __name__ == '__main__':
    import doctest
    doctest.testmod()


