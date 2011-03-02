################################################################################
#This software was developed by the University of Tennessee as part of the
#Distributed Data Analysis of Neutron Scattering Experiments (DANSE)
#project funded by the US National Science Foundation. 
#
#See the license text in license.txt
#
#copyright 2010, University of Tennessee
################################################################################
"""
This module manages all data loaded into the application. Data_manager makes 
available all data loaded  for the current perspective. 

All modules "creating Data" posts their data to data_manager . 
Data_manager  make these new data available for all other perspectives.
"""
import logging
import os
from sans.guiframe.data_state import DataState
from sans.guiframe.utils import parse_name
import DataLoader.data_info as DataInfo
from sans.guiframe.dataFitting import Data1D
from sans.guiframe.dataFitting import Data2D
  
import wx

class DataManager(object):
    """
    Manage a list of data
    """
    def __init__(self):
        """
        Store opened path and data object created at the loading time
        :param auto_plot: if True the datamanager sends data to plotting 
                            plugin. 
        :param auto_set_data: if True the datamanager sends to the current
        perspective
        """
        self._selected_data = {}
        self.stored_data = {}
        self.message = ""
        self.data_name_dict = {}
      
    def create_gui_data(self, data, path=None):
        """
        Receive data from loader and create a data to use for guiframe
        """
        
        if issubclass(DataInfo.Data2D, data.__class__):
            new_plot = Data2D(image=None, err_image=None) 
        else: 
            new_plot = Data1D(x=[], y=[], dx=None, dy=None)
           
        new_plot.copy_from_datainfo(data) 
        data.clone_without_data(clone=new_plot)  
        #creating a name for data
        name = ""
        title = ""
        file_name = ""
        if path is not None:
            file_name = os.path.basename(path)
        if data.run:
            name = data.run[0]
        if name == "":
            name = file_name
        name = self.rename(name)
        #find title
        if data.title.strip():
            title = data.title
        if title.strip() == "":
            title = file_name
        
        if new_plot.filename.strip() == "":
            new_plot.filename = file_name
        
        new_plot.name = name
        new_plot.title = title
        ## allow to highlight data when plotted
        new_plot.interactive = True
        ## when 2 data have the same id override the 1 st plotted
        new_plot.id = wx.NewId()
        ##group_id specify on which panel to plot this data
        new_plot.group_id = [wx.NewId()]
        new_plot.is_data = True
        new_plot.path = path
        ##post data to plot
        # plot data
        return new_plot
 
    def rename(self, name):
        """
        rename data
        """
        ## name of the data allow to differentiate data when plotted
        name = parse_name(name=name, expression="_")
        
        max_char = name.find("[")
        if max_char < 0:
            max_char = len(name)
        name = name[0:max_char]
        
        if name not in self.data_name_dict:
            self.data_name_dict[name] = 0
        else:
            self.data_name_dict[name] += 1
            name = name + " [" + str(self.data_name_dict[name]) + "]"
        return name
    
    def add_data(self, data_list):
        """
        receive a list of 
        """
        self._selected_data = {}
        for data in data_list:
            if data.id  in self.stored_data:
                msg = "Data manager already stores %s" % str(data.name)
                msg += ""
                logging.info(msg)
                self.stored_data[data.id].data = data
                data_state = self.stored_data[data.id]
            else:
                data_state = DataState(data)
                self.stored_data[data.id] = data_state
            self._selected_data[data.id] = data_state
      
    def set_auto_plot(self, flag=False):
        """
        When flag is true the data is plotted automatically
        """
        self._auto_set_data = flag
        
    def set_auto_set_data(self, flag=False):
        """
        When flag is true the data is send to the current perspective
        automatically
        """
        self._auto_set_data = flag
        
    def get_message(self):
        """
        return message
        """
        return self.message
    
    def get_by_id(self, id_list=None):
        """
        get a list of data given a list of id
        """
        self._selected_data = {}
        for id in id_list:
            if id in self.stored_data:
                self._selected_data[id] = self.stored_data[id]
        return self._selected_data
    
    def append_theory(self, data_id, theory):
        """
        """
        if data_id in self.stored_data:
            data_state = self.stored_data[data_id]
            data_state.set_theory(theory)
            
    def delete_data(self, data_id, theory_id, delete_all):
        """
        """
        if data_id in self.stored_data:
            del self.stored_data[data_id]
        if data_id in self._selected_data:
            del self._selected_data
            
    def delete_by_id(self, id_list=None):
        """
        save data and path
        """
        for id in id_list:
            if id in self.stored_data:
                del self.stored_data[id]
            if id  in self._selected_data:
                del self._selected_data[id]
    
    def get_by_name(self, name_list=None):
        """
        return a list of data given a list of data names
        """
        self._selected_data = {}
        for selected_name in name_list:
            for id, data_state in self.stored_data.iteritems():
                if data_state.data.name == selected_name:
                    self._selected_data[id] = data_state
        return self._selected_data
    
    def delete_by_name(self, name_list=None):
        """
        save data and path
        """
        for selected_name in name_list:
            for id, data_state in self.stored_data.iteritems():
                if data_state.data.name == selected_name:
                    del self._selected_data[id]
                    del self.stored_data[data.id]

    def get_selected_data(self):
        """
        Send list of selected data
        """
        return self._selected_data
    
    def get_all_data(self):
        """
        return list of all available data
        """
        return self.stored_data
    

        