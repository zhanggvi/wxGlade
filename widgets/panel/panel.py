"""\
wxPanel objects

@copyright: 2002-2007 Alberto Griggio
@copyright: 2014-2016 Carsten Grohmann
@license: MIT (see LICENSE.txt) - THIS PROGRAM COMES WITH NO WARRANTY
"""

import logging
import wx
import clipboard
import common
import compat
import config
import misc
from tree import Tree
from gui_mixins import ExecAfterMixin
from widget_properties import *
from edit_windows import ManagedBase, TopLevelBase, EditStylesMixin


class PanelBase(EditStylesMixin):
    "Class PanelBase"
    _custom_base_classes = True

    def __init__(self, style='wxTAB_TRAVERSAL'):
        "Class to handle wxPanel objects"
        # initialise instance logger
        self._logger = logging.getLogger(self.__class__.__name__)

        # initialise instance
        EditStylesMixin.__init__(self, 'wxPanel')

        self.top_sizer = None  # sizer to handle the layout of children
        self.no_custom_class = False
        self.access_functions['no_custom_class'] = (self.get_no_custom_class, self.set_no_custom_class)
        self.properties['no_custom_class'] = CheckBoxProperty( self, 'no_custom_class',
                                                               label=_("Don't generate code for this class"))

        self.set_style(style)
        self.access_functions['style'] = (self.get_style, self.set_style)
        self.properties['style'] = CheckListProperty(self, 'style', self.widget_writer)
        self.access_functions['scrollable'] = (self.get_scrollable, self.set_scrollable)
        self.scrollable = False
        self.properties['scrollable'] = CheckBoxProperty( self, 'scrollable', label=_("scrollable") )
        self.scroll_rate = (10, 10)
        self.access_functions['scroll_rate'] = (self.get_scroll_rate, self.set_scroll_rate)
        self.properties['scroll_rate'] = TextProperty( self, 'scroll_rate', can_disable=True, label=_("Scroll rate"))

    def finish_widget_creation(self):
        super(PanelBase, self).finish_widget_creation(
            sel_marker_parent=self.widget)
        if not self.scrollable:
            self.widget.SetScrollRate(0, 0)
        else:
            self.widget.SetScrollRate(*self.scroll_rate)
        # this must be done here since ManagedBase.finish_widget_creation
        # normally sets EVT_LEFT_DOWN to update_view
        if not self.widget.Disconnect(-1, -1, wx.wxEVT_LEFT_DOWN):
            self._logger.warning( _("EditPanel: Unable to disconnect the event handler") )
        wx.EVT_LEFT_DOWN(self.widget, self.drop_sizer)

    def _update_markers(self, event):
        def get_pos():
            x, y = self.widget.GetPosition()
            xx, yy = self.widget.GetViewStart()
            return x+xx, y+yy
        old = self.widget.GetPosition
        self.widget.GetPosition = get_pos
        #self._logger.debug("%s, %s", self.widget, self.sel_marker.owner)
        self.sel_marker.update()
        self.widget.GetPosition = old
        event.Skip()

    def create_properties(self):
        super(PanelBase, self).create_properties()
        panel = wx.ScrolledWindow(self.notebook, -1, style=wx.TAB_TRAVERSAL)
        panel.SetScrollRate(5, 5)
        szr = wx.BoxSizer(wx.VERTICAL)
        self.properties['no_custom_class'].display(panel)
        szr.Add(self.properties['no_custom_class'].panel, 0, wx.EXPAND)
        label = self.properties['no_custom_class'].cb
        label.SetToolTip( wx.ToolTip(_('If this is a custom class, setting this property prevents wxGlade\n'
                                       'from generating the class definition code')) )
        self.properties['style'].display(panel)
        szr.Add(self.properties['style'].panel, 0, wx.EXPAND)
        self.properties['scrollable'].display(panel)
        szr.Add(self.properties['scrollable'].panel, 0, wx.EXPAND)
        self.properties['scroll_rate'].display(panel)
        szr.Add(self.properties['scroll_rate'].panel, 0, wx.EXPAND)
        panel.SetAutoLayout(True)
        compat.SizerItem_SetSizer(panel, szr)
        szr.Fit(panel)
        self.notebook.AddPage(panel, 'Widget')

    def on_enter(self, event):
        if not self.top_sizer and common.adding_sizer:
            self.widget.SetCursor(wx.CROSS_CURSOR)
        else:
            self.widget.SetCursor(wx.STANDARD_CURSOR)

    def set_sizer(self, sizer):
        self.top_sizer = sizer
        if self.top_sizer and self.top_sizer.widget and self.widget:
            self.widget.SetAutoLayout(True)
            self.widget.SetSizer(self.top_sizer.widget)
            self.widget.Layout()
        elif self.top_sizer is None and self.widget:
            self.widget.SetSizer(None)

    def drop_sizer(self, event):
        if self.top_sizer or not common.adding_sizer:
            self.on_set_focus(event)  # default behaviour: call show_properties
            return
        self.widget.SetCursor(wx.NullCursor)
        common.widgets[common.widget_to_add](self, None, None)
        common.adding_widget = common.adding_sizer = False
        common.widget_to_add = None
        common.app_tree.app.saved = False

    def get_widget_best_size(self):
        if self.top_sizer and self.widget.GetSizer():
            self.top_sizer.fit_parent()
            return self.widget.GetSize()
        return wx.ScrolledWindow.GetBestSize(self.widget)

    def get_scrollable(self):
        return self.scrollable

    def set_scrollable(self, value):
        self.scrollable = bool(int(value))
        if self.scrollable:
            if self.klass == 'wxPanel':
                self.klass = 'wxScrolledWindow'
                self.klass_prop.set_value(self.klass)
        else:
            if self.klass == 'wxScrolledWindow':
                self.klass = 'wxPanel'
                self.klass_prop.set_value(self.klass)
        if not self.widget:
            return
        if self.scrollable:
            self.properties['scroll_rate'].toggle_active(True)
            self.widget.SetScrollRate(*self.scroll_rate)
        else:
            self.properties['scroll_rate'].toggle_active(False)
            self.widget.SetScrollRate(0, 0)

    def get_scroll_rate(self):
        return '%d, %d' % self.scroll_rate

    def set_scroll_rate(self, value):
        invalid = False
        try:
            srx, sry = [int(t) for t in value.split(',', 1)]
            if srx < 0 or sry < 0:
                invalid = True
        except:
            invalid = True
        if invalid:
            self.properties['scroll_rate'].set_value(self.get_scroll_rate())
            return
        self.scroll_rate = srx, sry
        if self.widget:
            self.widget.SetScrollRate(srx, sry)

    def get_no_custom_class(self):
        return self.no_custom_class

    def set_no_custom_class(self, value):
        self.no_custom_class = bool(int(value))

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_logger']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

        # re-initialise logger instance deleted from __getstate__
        self._logger = logging.getLogger(self.__class__.__name__)

# end of class PanelBase


class EditPanel(PanelBase, ManagedBase, ExecAfterMixin):
    "Class to handle wxPanel objects"
    def __init__(self, name, parent, id, sizer, pos, property_window, show=True, style='wxTAB_TRAVERSAL'):
        ManagedBase.__init__(self, name, 'wxPanel', parent, id, sizer, pos, property_window, show=show)
        PanelBase.__init__(self, style)

    def create_widget(self):
        self.widget = wx.ScrolledWindow(self.parent.widget, self.id, style=0)
        wx.EVT_ENTER_WINDOW(self.widget, self.on_enter)
        self.widget.GetBestSize = self.get_widget_best_size
        if self.sizer.is_virtual():
            def GetBestSize():
                if self.widget and self.widget.GetSizer():
                    return self.widget.GetSizer().GetMinSize()
                #return wx.Panel.GetBestSize(self.widget)
                return wx.ScrolledWindow.GetBestSize(self.widget)
            self.widget.GetBestSize = GetBestSize

    def set_sizer(self, sizer):
        super(EditPanel, self).set_sizer(sizer)
        if self.top_sizer and self.top_sizer.widget and self.widget:
            self.sizer.set_item(self.pos, size=self.widget.GetBestSize())

    def set_scrollable(self, value):
        super(EditPanel, self).set_scrollable(value)
        if self.scrollable:
            # 2003-06-26 ALB: change the "class name", to allow code generation
            # for a wxScrolledWindow (see Node.write and
            # common.class_names usage in xml_parse.py)
            self._classname = 'EditScrolledWindow'
        else:
            self._classname = self.__class__.__name__

    def _create_popup_menu(self):
        COPY_ID, REMOVE_ID, CUT_ID = [wx.NewId() for i in range(3)]
        self._rmenu = misc.wxGladePopupMenu(self.name)
        misc.append_item(self._rmenu, REMOVE_ID, _('Remove\tDel'),
                         wx.ART_DELETE)
        misc.append_item(self._rmenu, COPY_ID, _('Copy\tCtrl+C'),
                         wx.ART_COPY)
        misc.append_item(self._rmenu, CUT_ID, _('Cut\tCtrl+X'),
                         wx.ART_CUT)

        wx.EVT_MENU(self.widget, REMOVE_ID, self.exec_after(self.remove))
        wx.EVT_MENU(self.widget, COPY_ID, self.exec_after(self.clipboard_copy))
        wx.EVT_MENU(self.widget, CUT_ID, self.exec_after(self.clipboard_cut))

        PASTE_ID = wx.NewId()
        misc.append_item(self._rmenu, PASTE_ID, _('Paste\tCtrl+V'),
                         wx.ART_PASTE)
        wx.EVT_MENU(self.widget, PASTE_ID, self.exec_after(self.clipboard_paste))

        PREVIEW_ID = wx.NewId()
        self._rmenu.AppendSeparator()
        misc.append_item(self._rmenu, PREVIEW_ID, _('Preview'))
        wx.EVT_MENU(self.widget, PREVIEW_ID, self.exec_after(self.preview_parent))

    def clipboard_paste(self, event=None):
        """\
        Insert a widget from the clipboard to the current destination.

        @see: L{clipboard.paste()}
        """
        import xml_parse
        size = self.widget.GetSize()
        try:
            if clipboard.paste(self, None, 0):
                common.app_tree.app.saved = False
                self.widget.SetSize(size)
        except xml_parse.XmlParsingError:
            self._logger.warning(_('Only sizers can be pasted here'))

# end of class EditPanel


class EditTopLevelPanel(PanelBase, TopLevelBase):
    _is_toplevel = False  # used to avoid to appear in the "Top Window" property of the app

    def __init__(self, name, parent, id, property_window, klass='wxPanel', show=True, style='wxTAB_TRAVERSAL'):
        TopLevelBase.__init__(self, name, klass, parent, id, property_window, show=show, has_title=False)
        PanelBase.__init__(self, style)
        self.base = 'wxPanel'
        self.skip_on_size = False

    def create_widget(self):
        win = wx.Frame( common.palette, -1, misc.design_title(self.name), size=(400, 300) )
        import os
        icon = wx.EmptyIcon()
        xpm = os.path.join(config.icons_path, 'panel.xpm')
        icon.CopyFromBitmap(misc.get_xpm_bitmap(xpm))
        win.SetIcon(icon)
        #self.widget = wx.Panel(win, self.id, style=0)
        self.widget = wx.ScrolledWindow(win, self.id, style=0)
        wx.EVT_ENTER_WINDOW(self.widget, self.on_enter)
        self.widget.GetBestSize = self.get_widget_best_size
        #self.widget.SetSize = win.SetSize
        wx.EVT_CLOSE(win, self.hide_widget)
        if wx.Platform == '__WXMSW__':
            win.CentreOnScreen()

    def show_widget(self, yes):
        oldval = self.get_size()
        super(EditTopLevelPanel, self).show_widget(yes)
        if self.widget:
            if yes and not self.properties['size'].is_active() and self.top_sizer:
                self.top_sizer.fit_parent()
            self.widget.GetParent().Show(yes)
        self.set_size(oldval)

    def hide_widget(self, *args):
        super(EditTopLevelPanel, self).hide_widget(*args)
        self.widget.GetParent().Hide()

    def set_name(self, name):
        super(EditTopLevelPanel, self).set_name(name)
        if self.widget:
            self.widget.GetParent().SetTitle(misc.design_title(self.name))

    def delete(self):
        win = None
        if self.widget:
            win = self.widget.GetParent()
        super(EditTopLevelPanel, self).delete()
        if win is not None:
            win.Destroy()

    def on_size(self, event):
        w, h = event.GetSize()
        if self.skip_on_size:
            self.skip_on_size = False
            return
        super(EditTopLevelPanel, self).on_size(event)
        self.skip_on_size = True
        if self.widget.GetParent().GetClientSize() != (w, h):
            self.widget.GetParent().SetClientSize((w+2, h+2))

    def set_scrollable(self, value):
        super(EditTopLevelPanel, self).set_scrollable(value)
        if self.scrollable:
            # 2003-06-26 ALB: change the "class name", to allow code generation
            # for a wxScrolledWindow (see Tree.Node.write and
            # common.class_names usage in xml_parse.py)
            self._classname = 'EditTopLevelScrolledWindow'
        else:
            self._classname = self.__class__.__name__

# end of class EditTopLevelPanel


def builder(parent, sizer, pos, number=[1]):
    "factory function for EditPanel objects"
    name = 'panel_%d' % number[0]
    while common.app_tree.has_name(name):
        number[0] += 1
        name = 'panel_%d' % number[0]
    panel = EditPanel(name, parent, wx.NewId(), sizer, pos,
                      common.property_panel, style='')
    node = Tree.Node(panel)
    panel.node = node

    panel.set_option(1)
    panel.set_style("wxEXPAND")

    panel.show_widget(True)

    common.app_tree.insert(node, sizer.node, pos - 1)
    sizer.set_item(panel.pos, 1, wx.EXPAND)


def xml_builder(attrs, parent, sizer, sizeritem, pos=None):
    "factory to build EditPanel objects from a XML file"
    from xml_parse import XmlParsingError
    try:
        name = attrs['name']
    except KeyError:
        raise XmlParsingError(_("'name' attribute missing"))
    if not sizer or not sizeritem:
        raise XmlParsingError(_("sizer or sizeritem object cannot be None"))
    panel = EditPanel(name, parent, wx.NewId(), sizer, pos, common.property_panel, True, style='')
    sizer.set_item(panel.pos, option=sizeritem.option, flag=sizeritem.flag, border=sizeritem.border)
    node = Tree.Node(panel)
    panel.node = node
    if pos is None:
        common.app_tree.add(node, sizer.node)
    else:
        common.app_tree.insert(node, sizer.node, pos - 1)
    return panel


def xml_toplevel_builder(attrs, parent, sizer, sizeritem, pos=None):
    from xml_parse import XmlParsingError
    try:
        label = attrs['name']
    except KeyError:
        raise XmlParsingError(_("'name' attribute missing"))
    panel = EditTopLevelPanel( label, parent, wx.NewId(), common.property_panel, show=False, style='' )
    node = Tree.Node(panel)
    panel.node = node
    common.app_tree.add(node)
    return panel


def initialize():
    """\
    initialization function for the module: returns a wxBitmapButton to be
    added to the main palette.
    """
    common.widgets['EditPanel'] = builder
    common.widgets_from_xml['EditPanel'] = xml_builder

    #common.widgets['EditScrolledWindow'] = builder
    common.widgets_from_xml['EditScrolledWindow'] = xml_builder

    common.widgets_from_xml['EditTopLevelPanel'] = xml_toplevel_builder
    common.widgets_from_xml['EditTopLevelScrolledWindow'] = xml_toplevel_builder
    from tree import WidgetTree
    import os.path
    icon = os.path.join(config.icons_path, 'panel.xpm')
    WidgetTree.images['EditTopLevelPanel'] = icon
    WidgetTree.images['EditScrolledWindow'] = icon
    WidgetTree.images['EditTopLevelScrolledWindow'] = icon

    # these are for backwards compatibility (may be removed someday...)
    common.widgets_from_xml['SplitterPane'] = xml_builder
    WidgetTree.images['SplitterPane'] = os.path.join( config.icons_path, 'panel.xpm' )
    common.widgets_from_xml['NotebookPane'] = xml_builder
    WidgetTree.images['NotebookPane'] = os.path.join( config.icons_path, 'panel.xpm' )
    return common.make_object_button('EditPanel', 'panel.xpm', tip='Add a Panel/ScrolledWindow')

