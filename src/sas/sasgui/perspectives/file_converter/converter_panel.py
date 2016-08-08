"""
This module provides a GUI for the file converter
"""

import wx
import sys
import os
import numpy as np
from wx.lib.scrolledpanel import ScrolledPanel
from sas.sasgui.guiframe.panel_base import PanelBase
from sas.sasgui.perspectives.calculator import calculator_widgets as widget
from sas.sasgui.perspectives.file_converter.converter_widgets import VectorInput
from sas.sasgui.perspectives.file_converter.meta_panels import MetadataWindow
from sas.sasgui.perspectives.file_converter.meta_panels import DetectorPanel
from sas.sasgui.perspectives.file_converter.meta_panels import SamplePanel
from sas.sasgui.perspectives.file_converter.meta_panels import SourcePanel
from sas.sasgui.perspectives.file_converter.frame_select_dialog import FrameSelectDialog
from sas.sasgui.guiframe.events import StatusEvent
from sas.sasgui.guiframe.documentation_window import DocumentationWindow
from sas.sasgui.guiframe.dataFitting import Data1D
from sas.sascalc.dataloader.data_info import Data2D
from sas.sasgui.guiframe.utils import check_float
from sas.sasgui.perspectives.file_converter.cansas_writer import CansasWriter
from sas.sascalc.dataloader.readers.red2d_reader import Reader as Red2DWriter
from sas.sasgui.perspectives.file_converter.otoko_loader import OTOKOLoader
from sas.sascalc.file_converter.bsl_loader import BSLLoader
from sas.sascalc.dataloader.data_info import Detector
from sas.sascalc.dataloader.data_info import Sample
from sas.sascalc.dataloader.data_info import Source
from sas.sascalc.dataloader.data_info import Vector

# Panel size
if sys.platform.count("win32") > 0:
    PANEL_TOP = 0
    _STATICBOX_WIDTH = 410
    _BOX_WIDTH = 200
    PANEL_SIZE = 480
    FONT_VARIANT = 0
else:
    PANEL_TOP = 60
    _STATICBOX_WIDTH = 430
    _BOX_WIDTH = 200
    PANEL_SIZE = 500
    FONT_VARIANT = 1

class ConverterPanel(ScrolledPanel, PanelBase):
    """
    This class provides the File Converter GUI
    """

    def __init__(self, parent, base=None, *args, **kwargs):
        ScrolledPanel.__init__(self, parent, *args, **kwargs)
        PanelBase.__init__(self)
        self.SetupScrolling()
        self.SetWindowVariant(variant=FONT_VARIANT)

        self.base = base
        self.parent = parent
        self.meta_frames = []

        # GUI inputs
        self.q_input = None
        self.iq_input = None
        self.output = None
        self.radiation_input = None
        self.metadata_section = None

        self.data_type = "ascii"

        # Metadata values
        self.title = None
        self.run = None
        self.run_name = None
        self.instrument = None
        self.detector = Detector()
        self.sample = Sample()
        self.source = Source()
        self.properties = ['title', 'run', 'run_name', 'instrument']

        self.detector.name = ''
        self.source.radiation = 'neutron'

        self._do_layout()
        self.SetAutoLayout(True)
        self.Layout()

    def convert_to_cansas(self, frame_data, filename, single_file):
        """
        Saves an array of Data1D objects to a single CanSAS file with multiple
        <SasData> elements, or to multiple CanSAS files, each with one
        <SasData> element.

        :param frame_data: The Data1D object to save
        :param filename: Where to save the CanSAS file
        :param single_file: If true, array is saved as a single file, if false,
        each item in the array is saved to it's own file
        """
        writer = CansasWriter()
        entry_attrs = None
        if self.run_name is not None:
            entry_attrs = { 'name': self.run_name }
        if single_file:
            writer.write(filename, frame_data,
                sasentry_attrs=entry_attrs)
        else:
            # strip extension from filename
            ext = "." + filename.split('.')[-1]
            name = filename.replace(ext, '')
            for i in range(len(frame_data)):
                # TODO: Change i to actual frame number, not consecutive numbers
                # (maybe use info in params from frame select dialog, ie
                # increment. Alternatively, change frame_data to a dictionary
                # with the frame number as key and use frame_data.iteritems()
                # (would need to update CansasWriter to deal with this)
                f_name = name + str(i) + ext
                writer.write(f_name, [frame_data[i]],
                    sasentry_attrs=entry_attrs)

    def extract_ascii_data(self, filename):
        """
        Extracts data from a single-column ASCII file

        :param filename: The file to load data from
        :return: A numpy array containing the extracted data
        """
        data = np.loadtxt(filename, dtype=str)

        if len(data.shape) != 1:
            msg = "Error reading {}: Only one column of data is allowed"
            raise Exception(msg.format(filename.split('\\')[-1]))

        is_float = True
        try:
            float(data[0])
        except:
            is_float = False

        if not is_float:
            end_char = data[0][-1]
            # If lines end with comma or semi-colon, trim the last character
            if end_char == ',' or end_char == ';':
                data = map(lambda s: s[0:-1], data)
            else:
                msg = ("Error reading {}: Lines must end with a digit, comma "
                    "or semi-colon").format(filename.split('\\')[-1])
                raise Exception(msg)

        return np.array(data, dtype=np.float32)

    def extract_otoko_data(self, filename):
        """
        Extracts data from a 1D OTOKO file

        :param filename: The OTOKO file to load the data from
        :return: A numpy array containing the extracted data
        """
        loader = OTOKOLoader(self.q_input.GetPath(),
            self.iq_input.GetPath())
        bsl_data = loader.load_bsl_data()
        qdata = bsl_data.q_axis.data
        iqdata = bsl_data.data_axis.data
        if len(qdata) > 1:
            msg = ("Q-Axis file has multiple frames. Only 1 frame is "
                "allowed for the Q-Axis")
            wx.PostEvent(self.parent.manager.parent,
                StatusEvent(status=msg, info="error"))
            return
        else:
            qdata = qdata[0]

        return qdata, iqdata

    def ask_frame_range(self, n_frames):
        """
        Display a dialog asking the user to input the range of frames they
        would like to export

        :param n_frames: How many frames the loaded data file has
        :return: A dictionary containing the parameters input by the user
        """
        valid_input = False
        is_bsl = (self.data_type == 'bsl')
        dlg = FrameSelectDialog(n_frames, is_bsl)
        frames = None
        increment = None
        single_file = True
        while not valid_input:
            if dlg.ShowModal() == wx.ID_OK:
                msg = ""
                try:
                    first_frame = int(dlg.first_input.GetValue())
                    last_frame = int(dlg.last_input.GetValue())
                    increment = int(dlg.increment_input.GetValue())
                    if not is_bsl:
                        single_file = dlg.single_btn.GetValue()

                    if last_frame < 0 or first_frame < 0:
                        msg = "Frame values must be positive"
                    elif increment < 1:
                        msg = "Increment must be greater than or equal to 1"
                    elif first_frame > last_frame:
                        msg = "First frame must be less than last frame"
                    elif last_frame >= n_frames:
                        msg = "Last frame must be less than {}".format(n_frames)
                    else:
                        valid_input = True
                except:
                    valid_input = False
                    msg = "Please enter valid integer values"

                if not valid_input:
                    wx.PostEvent(self.parent.manager.parent,
                        StatusEvent(status=msg))
            else:
                return { 'frames': [], 'inc': None, 'file': single_file }
        frames = range(first_frame, last_frame + increment,
            increment)
        return { 'frames': frames, 'inc': increment, 'file': single_file }

    def on_convert(self, event):
        """Called when the Convert button is clicked"""
        if not self.validate_inputs():
            return

        self.sample.ID = self.title

        try:
            if self.data_type == 'ascii':
                qdata = self.extract_ascii_data(self.q_input.GetPath())
                iqdata = np.array([self.extract_ascii_data(self.iq_input.GetPath())])
            elif self.data_type == 'otoko':
                qdata, iqdata = self.extract_otoko_data(self.q_input.GetPath())
            else: # self.data_type == 'bsl'
                # TODO: Refactor this into an extract_bsl_data method
                loader = BSLLoader(self.iq_input.GetPath())
                frames = [0]
                if loader.n_frames > 1:
                    params = self.ask_frame_range(loader.n_frames)
                    frames = params['frames']
                data = {}

                for frame in frames:
                    loader.frame = frame
                    data[frame] = loader.load_data()

                # TODO: Tidy this up
                # Prepare axes values (arbitrary scale)
                data_x = []
                data_y = range(loader.n_pixels) * loader.n_rasters
                for i in range(loader.n_rasters):
                    data_x += [i] * loader.n_pixels

                file_path = self.output.GetPath()
                filename = os.path.split(file_path)[-1]
                file_path = os.path.split(file_path)[0]
                for i, frame in data.iteritems():
                    # If more than 1 frame is being exported, append the frame
                    # number to the filename
                    if len(data) > 1:
                        frame_filename = filename.split('.')
                        frame_filename[0] += str(i+1)
                        frame_filename = '.'.join(frame_filename)
                    else:
                        frame_filename = filename

                    data_i = frame.reshape((loader.n_pixels*loader.n_rasters,1))
                    data_info = Data2D(data=data_i, qx_data=data_x, qy_data=data_y)
                    writer = Red2DWriter()
                    writer.write(os.path.join(file_path, frame_filename), data_info)

                wx.PostEvent(self.parent.manager.parent,
                    StatusEvent(status="Conversion completed."))
                return

        except Exception as ex:
            msg = str(ex)
            wx.PostEvent(self.parent.manager.parent,
                StatusEvent(status=msg, info='error'))
            return

        frames = []
        increment = 1
        single_file = True
        n_frames = iqdata.shape[0]
        # Standard file has 3 frames: SAS, calibration and WAS
        if n_frames > 3:
            # File has multiple frames - ask the user which ones they want to
            # export
            params = self.ask_frame_range(n_frames)
            frames = params['frames']
            increment = params['inc']
            single_file = params['file']
            if frames == []: return
        else: # Only interested in SAS data
            frames = [0]

        output_path = self.output.GetPath()

        # Prepare the metadata for writing to a file
        if self.run is None:
            self.run = []
        elif not isinstance(self.run, list):
            self.run = [self.run]

        if self.title is None:
            self.title = ''

        metadata = {
            'title': self.title,
            'run': self.run,
            'intrument': self.instrument,
            'detector': [self.detector],
            'sample': self.sample,
            'source': self.source
        }

        frame_data = []
        for i in frames:
            data = Data1D(x=qdata, y=iqdata[i])
            frame_data.append(data)
        if single_file:
            # Only need to set metadata on first Data1D object
            frame_data[0].filename = output_path.split('\\')[-1]
            for key, value in metadata.iteritems():
                setattr(frame_data[0], key, value)
        else:
            # Need to set metadata for all Data1D objects
            for datainfo in frame_data:
                datainfo.filename = output_path.split('\\')[-1]
                for key, value in metadata.iteritems():
                    setattr(datainfo, key, value)


        self.convert_to_cansas(frame_data, output_path, single_file)
        wx.PostEvent(self.parent.manager.parent,
            StatusEvent(status="Conversion completed."))

    def on_help(self, event):
        """
        Show the File Converter documentation
        """
        tree_location = ("user/sasgui/perspectives/file_converter/"
            "file_converter_help.html")
        doc_viewer = DocumentationWindow(self, -1, tree_location,
            "", "File Converter Help")

    def validate_inputs(self):
        msg = "You must select a"
        if self.q_input.GetPath() == '' and self.data_type != 'bsl':
            msg += " Q Axis input file."
        elif self.iq_input.GetPath() == '':
            msg += "n Intensity input file."
        elif self.output.GetPath() == '':
            msg += "destination for the converted file."
        if msg != "You must select a":
            wx.PostEvent(self.parent.manager.parent,
                StatusEvent(status=msg, info='error'))
            return

        return True

    def show_detector_window(self, event):
        """
        Show the window for inputting :class:`~sas.sascalc.dataloader.data_info.Detector~` metadata
        """
        if self.meta_frames != []:
            for frame in self.meta_frames:
                frame.panel.on_close()
        detector_frame = MetadataWindow(DetectorPanel,
            parent=self.parent.manager.parent, manager=self,
            metadata=self.detector, title='Detector Metadata')
        self.meta_frames.append(detector_frame)
        self.parent.manager.put_icon(detector_frame)
        detector_frame.Show(True)

    def show_sample_window(self, event):
        """
        Show the window for inputting :class:`~sas.sascalc.dataloader.data_info.Sample~` metadata
        """
        if self.meta_frames != []:
            for frame in self.meta_frames:
                frame.panel.on_close()
        sample_frame = MetadataWindow(SamplePanel,
            parent=self.parent.manager.parent, manager=self,
            metadata=self.sample, title='Sample Metadata')
        self.meta_frames.append(sample_frame)
        self.parent.manager.put_icon(sample_frame)
        sample_frame.Show(True)

    def show_source_window(self, event):
        """
        Show the window for inputting :class:`~sas.sascalc.dataloader.data_info.Source~` metadata
        """
        if self.meta_frames != []:
            for frame in self.meta_frames:
                frame.panel.on_close()
        source_frame = MetadataWindow(SourcePanel,
            parent=self.parent.manager.parent, manager=self,
            metadata=self.source, title="Source Metadata")
        self.meta_frames.append(source_frame)
        self.parent.manager.put_icon(source_frame)
        source_frame.Show(True)

    def on_collapsible_pane(self, event):
        """
        Resize the scrollable area to fit the metadata pane when it's
        collapsed or expanded
        """
        self.Freeze()
        self.SetupScrolling()
        self.parent.Layout()
        self.Thaw()

    def datatype_changed(self, event):
        """
        Update the UI and self.data_type when a data type radio button is
        pressed
        """
        event.Skip()
        dtype = event.GetEventObject().GetName()
        self.data_type = dtype
        if dtype == 'bsl':
            self.q_input.SetPath("")
            self.q_input.Disable()
            self.radiation_input.Disable()
            self.metadata_section.Collapse()
            self.on_collapsible_pane(None)
            self.metadata_section.Disable()
        else:
            self.q_input.Enable()
            self.radiation_input.Enable()
            self.metadata_section.Enable()

    def radiationtype_changed(self, event):
        event.Skip()
        rtype = event.GetEventObject().GetValue().lower()
        self.source.radiation = rtype

    def metadata_changed(self, event):
        event.Skip()
        textbox = event.GetEventObject()
        attr = textbox.GetName()
        value = textbox.GetValue().strip()

        if value == '': value = None

        setattr(self, attr, value)


    def _do_layout(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        instructions = ("Select either single column ASCII files or BSL/OTOKO"
            " files containing the Q-Axis and Intensity-axis data, chose where"
            " to save the converted file, then click Convert to convert them "
            "to CanSAS XML format. If required, metadata can also be input "
            "below.")
        instruction_label = wx.StaticText(self, -1, instructions,
            size=(_STATICBOX_WIDTH+40, -1))
        instruction_label.Wrap(_STATICBOX_WIDTH+40)
        vbox.Add(instruction_label, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=5)

        section = wx.StaticBox(self, -1)
        section_sizer = wx.StaticBoxSizer(section, wx.VERTICAL)
        section_sizer.SetMinSize((_STATICBOX_WIDTH, -1))

        input_grid = wx.GridBagSizer(5, 5)

        y = 0

        data_type_label = wx.StaticText(self, -1, "Input Format: ")
        input_grid.Add(data_type_label, (y,0), (1,1),
            wx.ALIGN_CENTER_VERTICAL, 5)
        radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ascii_btn = wx.RadioButton(self, -1, "ASCII", name="ascii",
            style=wx.RB_GROUP)
        ascii_btn.Bind(wx.EVT_RADIOBUTTON, self.datatype_changed)
        radio_sizer.Add(ascii_btn)
        otoko_btn = wx.RadioButton(self, -1, "OTOKO 1D", name="otoko")
        otoko_btn.Bind(wx.EVT_RADIOBUTTON, self.datatype_changed)
        radio_sizer.Add(otoko_btn)
        input_grid.Add(radio_sizer, (y,1), (1,1), wx.ALL, 5)
        bsl_btn = wx.RadioButton(self, -1, "BSL 2D", name="bsl")
        bsl_btn.Bind(wx.EVT_RADIOBUTTON, self.datatype_changed)
        radio_sizer.Add(bsl_btn)
        y += 1

        q_label = wx.StaticText(self, -1, "Q-Axis Data: ")
        input_grid.Add(q_label, (y,0), (1,1), wx.ALIGN_CENTER_VERTICAL, 5)

        self.q_input = wx.FilePickerCtrl(self, -1,
            size=(_STATICBOX_WIDTH-80, -1),
            message="Chose the Q-Axis data file.")
        input_grid.Add(self.q_input, (y,1), (1,1), wx.ALL, 5)
        y += 1

        iq_label = wx.StaticText(self, -1, "Intensity-Axis Data: ")
        input_grid.Add(iq_label, (y,0), (1,1), wx.ALIGN_CENTER_VERTICAL, 5)

        self.iq_input = wx.FilePickerCtrl(self, -1,
            size=(_STATICBOX_WIDTH-80, -1),
            message="Chose the Intensity-Axis data file.")
        input_grid.Add(self.iq_input, (y,1), (1,1), wx.ALL, 5)
        y += 1

        radiation_label = wx.StaticText(self, -1, "Radiation Type: ")
        input_grid.Add(radiation_label, (y,0), (1,1), wx.ALIGN_CENTER_VERTICAL, 5)
        self.radiation_input = wx.ComboBox(self, -1,
            choices=["Neutron", "X-Ray", "Muon", "Electron"],
            name="radiation", style=wx.CB_READONLY, value="Neutron")
        self.radiation_input.Bind(wx.EVT_COMBOBOX, self.radiationtype_changed)
        input_grid.Add(self.radiation_input, (y,1), (1,1), wx.ALL, 5)
        y += 1

        output_label = wx.StaticText(self, -1, "Output File: ")
        input_grid.Add(output_label, (y,0), (1,1), wx.ALIGN_CENTER_VERTICAL, 5)

        self.output = wx.FilePickerCtrl(self, -1,
            size=(_STATICBOX_WIDTH-80, -1),
            message="Chose where to save the output file.",
            style=wx.FLP_SAVE | wx.FLP_OVERWRITE_PROMPT | wx.FLP_USE_TEXTCTRL,
            wildcard="CanSAS 1D (*.xml)|*.xml|Red2D (*.dat)|*.dat")
        input_grid.Add(self.output, (y,1), (1,1), wx.ALL, 5)
        y += 1

        convert_btn = wx.Button(self, wx.ID_OK, "Convert")
        input_grid.Add(convert_btn, (y,0), (1,1), wx.ALL, 5)
        convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)

        help_btn = wx.Button(self, -1, "HELP")
        input_grid.Add(help_btn, (y,1), (1,1), wx.ALL, 5)
        help_btn.Bind(wx.EVT_BUTTON, self.on_help)

        section_sizer.Add(input_grid)

        vbox.Add(section_sizer, flag=wx.ALL, border=5)

        self.metadata_section = wx.CollapsiblePane(self, -1, "Metadata",
            size=(_STATICBOX_WIDTH+40, -1), style=wx.WS_EX_VALIDATE_RECURSIVELY)
        metadata_pane = self.metadata_section.GetPane()
        metadata_grid = wx.GridBagSizer(5, 5)

        self.metadata_section.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED,
            self.on_collapsible_pane)

        y = 0
        for item in self.properties:
            # Capitalise each word
            label_txt = " ".join(
                [s.capitalize() for s in item.replace('_', ' ').split(' ')])
            if item == 'run':
                label_txt = "Run Number"
            label = wx.StaticText(metadata_pane, -1, label_txt,
                style=wx.ALIGN_CENTER_VERTICAL)
            input_box = wx.TextCtrl(metadata_pane, name=item,
                size=(_STATICBOX_WIDTH-80, -1))
            input_box.Bind(wx.EVT_TEXT, self.metadata_changed)
            metadata_grid.Add(label, (y,0), (1,1),
                wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            metadata_grid.Add(input_box, (y,1), (1,2), wx.EXPAND)
            y += 1

        detector_label = wx.StaticText(metadata_pane, -1,
            "Detector:")
        metadata_grid.Add(detector_label, (y, 0), (1,1), wx.ALL | wx.EXPAND, 5)
        detector_btn = wx.Button(metadata_pane, -1, "Enter Detector Metadata")
        metadata_grid.Add(detector_btn, (y, 1), (1,1), wx.ALL | wx.EXPAND, 5)
        detector_btn.Bind(wx.EVT_BUTTON, self.show_detector_window)
        y += 1

        sample_label = wx.StaticText(metadata_pane, -1, "Sample: ")
        metadata_grid.Add(sample_label, (y,0), (1,1), wx.ALL | wx.EXPAND, 5)
        sample_btn = wx.Button(metadata_pane, -1, "Enter Sample Metadata")
        metadata_grid.Add(sample_btn, (y,1), (1,1), wx.ALL | wx.EXPAND, 5)
        sample_btn.Bind(wx.EVT_BUTTON, self.show_sample_window)
        y += 1

        source_label = wx.StaticText(metadata_pane, -1, "Source: ")
        metadata_grid.Add(source_label, (y,0), (1,1), wx.ALL | wx.EXPAND, 5)
        source_btn = wx.Button(metadata_pane, -1, "Enter Source Metadata")
        source_btn.Bind(wx.EVT_BUTTON, self.show_source_window)
        metadata_grid.Add(source_btn, (y,1), (1,1), wx.ALL | wx.EXPAND, 5)
        y += 1

        metadata_pane.SetSizer(metadata_grid)

        vbox.Add(self.metadata_section, proportion=0, flag=wx.ALL, border=5)

        vbox.Fit(self)
        self.SetSizer(vbox)

class ConverterWindow(widget.CHILD_FRAME):
    """Displays ConverterPanel"""

    def __init__(self, parent=None, title='File Converter', base=None,
        manager=None, size=(PANEL_SIZE * 1.05, PANEL_SIZE / 1.25),
        *args, **kwargs):
        kwargs['title'] = title
        kwargs['size'] = size
        widget.CHILD_FRAME.__init__(self, parent, *args, **kwargs)

        self.manager = manager
        self.panel = ConverterPanel(self, base=None)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.SetPosition((wx.LEFT, PANEL_TOP))
        self.Show(True)

    def on_close(self, event):
        if self.manager is not None:
            self.manager.converter_frame = None
        self.Destroy()