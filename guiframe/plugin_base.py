################################################################################
#This software was developed by the University of Tennessee as part of the
#Distributed Data Analysis of Neutron Scattering Experiments (DANSE)
#project funded by the US National Science Foundation. 
#
#See the license text in license.txt
#
#copyright 2008, University of Tennessee
################################################################################
 
class PluginBase:
    """
    This class defines the interface for a Plugin class
    that can be used by the gui_manager.
    
    Plug-ins should be placed in a sub-directory called "perspectives".
    For example, a plug-in called Foo should be place in "perspectives/Foo".
    That directory contains at least two files:
        perspectives/Foo/__init__.py contains two lines:
        
            PLUGIN_ID = "Foo plug-in 1.0"
            from Foo import *
            
        perspectives/Foo/Foo.py contains the definition of the Plugin
        class for the Foo plug-in. The interface of that Plugin class
        should follow the interface of the class you are looking at.
        
    See dummyapp.py for a plugin example.
    """
    
    def __init__(self, name="Test_plugin", standalone=True):
        """
            Abstract class for gui_manager Plugins.
        """
        # Define if the plugin is local to Viewerframe  and always active
        self._always_active = False
        ## Plug-in name. It will appear on the application menu.
        self.sub_menu = name     
        #standalone flag
        self.standalone = standalone
        ## Reference to the parent window. Filled by get_panels() below.
        self.parent = None
        #plugin state reader
        self.state_reader = None 
        self._extensions = ''
        ## List of panels that you would like to open in AUI windows
        #  for your plug-in. This defines your plug-in "perspective"
        self.perspective = []
        
    def clear_panel(self):
        """
        clear all related panels
        """
    def get_extensions(self):
        """
        return state reader and its extensions
        """
        return self.state_reader, self._extensions
    
    def can_load_data(self):
        """
        if return True, then call handler to laod data
        """
        return False
    
    def use_data(self):
        """
        return True if these plugin use data
        """
        return True
    
    def is_in_use(self, data_id):
        """
        get a  data id and return true or false if the data 
        is currently in use the current plugin
        """
        return False
    
    def delete_data(self, data_id):
        """
        Delete all references of data which id are in data_list. 
        """
        
    def load_data(self, event):
        """
        Load  data
        """
        raise NotImplemented
 
    def load_folder(self, event):
        """
        Load entire folder
        """
        raise NotImplemented 
    
    def set_is_active(self, active=False):
        """
        """
        self._always_active = active
        
    def is_always_active(self):
        """
        return True is this plugin is always active and it is local to guiframe
        even if the user is switching between perspectives
        """
        return self._always_active

    def populate_menu(self, parent):
        """
        Create and return the list of application menu
        items for the plug-in. 
        
        :param parent: parent window
        
        :return: plug-in menu
        
        """
        return []
    
    def get_panels(self, parent):
        """
        Create and return the list of wx.Panels for your plug-in.
        Define the plug-in perspective.
        
        Panels should inherit from DefaultPanel defined below,
        or should present the same interface. They must define
        "window_caption" and "window_name".
        
        :param parent: parent window
        
        :return: list of panels
        
        """
        ## Save a reference to the parent
        self.parent = parent
        
        # Return the list of panels
        return []
    
 
    def get_tools(self):
        """
        Returns a set of menu entries for tools
        """
        return []
        
    
    def get_context_menu(self, plotpanel=None):
        """
        This method is optional.
    
        When the context menu of a plot is rendered, the 
        get_context_menu method will be called to give you a 
        chance to add a menu item to the context menu.
        
        A ref to a plotpanel object is passed so that you can
        investigate the plot content and decide whether you
        need to add items to the context menu.  
        
        This method returns a list of menu items.
        Each item is itself a list defining the text to 
        appear in the menu, a tool-tip help text, and a
        call-back method.
        
        :param graph: the Graph object to which we attach the context menu
        
        :return: a list of menu items with call-back function
        
        """
        return []
    
    def get_perspective(self):
        """
        Get the list of panel names for this perspective
        """
        return self.perspective
    
    def on_perspective(self, event=None):
        """
        Call back function for the perspective menu item.
        We notify the parent window that the perspective
        has changed.
        
        :param event: menu event
        
        """
        self.parent.set_current_perspective(self)
        self.parent.set_perspective(self.perspective)
    
    def post_init(self):
        """
        Post initialization call back to close the loose ends
        """
        pass
    
    def set_default_perspective(self):
        """
       Call back method that True to notify the parent that the current plug-in
       can be set as default  perspective.
       when returning False, the plug-in is not candidate for an automatic 
       default perspective setting
        """
        if self.standalone:
            return True
        return False
    
    def set_state(self, state=None, datainfo=None):    
        """
        update state
        """
    def set_data(self, data_list=None):
        """
        receive a list of data and use it in the current perspective
       
        """
    def set_theory(self, theory_list=None):
        """
        :param theory_list: list of information 
            related to available theory state
        """
        msg = "%s plugin: does not support import theory" % str(self.sub_menu)
        raise ValueError, msg 
    
    def on_set_state_helper(self, event):
        """
        update state
        """
    
