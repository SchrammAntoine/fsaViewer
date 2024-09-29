
from ABIFReader import ABIFReader
import sys
import math
import itertools
import functools
import numpy as np
import argparse
import matplotlib.pyplot as plt
from matplotlib.backend_tools import ToolBase, ToolToggleBase
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont

class FsaData :

    def __init__(self, file_name) :
        self.file_name = file_name
        self.parser = ABIFReader(file_name)

    def get_fluorescence_intensities(self, channel) :
        assert channel in [1,2,3,4]
        return self.parser.getData("DATA",channel)
    def get_voltage(self) :
        return self.parser.getData("DATA",5)
    def get_current(self) :
        return self.parser.getData("DATA",6)
    def get_power(self) :
        return self.parser.getData("DATA",7)
    def get_temperature(self) :
        return self.parser.getData("DATA",8)
    def get_scan_number(self) :
        return self.parser.getData("SCAN",1)
    def get_saturated_frames(self) :
        try :
            satd = self.parser.getData("Satd",1)
        except SystemExit as e :
            satd = []
        return satd

    def get_dye_name(self, channel) :
        assert channel in [1,2,3,4]
        return self.parser.getData("DyeN",channel)
    def get_dye_wavelength(self, channel) :
        assert channel in [1,2,3,4]
        return self.parser.getData("DyeW",channel)

    def get_dates(self) :
        dates = {
            "run_start"        : self.parser.getData("RUND",1),
            "run_end"          : self.parser.getData("RUND",2),
            "collection_start" : self.parser.getData("RUND",3),
            "collection_end"   : self.parser.getData("RUND",4)
        }
        return dates

    def get_tube(self) :
        return self.parser.getData("TUBE",1)
    def get_user_name(self) :
        return self.parser.getData("User",1)

class MatplotlibCustomToolbar(QtWidgets.QMainWindow):
    def __init__(self, capillary_plot, winsize):
        super().__init__()
        self.setWindowTitle('FSA Viewer')
        self.resize(winsize[0], winsize[1])

        self.main_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main_widget)

        self.capillary_plot = capillary_plot
        self.fig, self.ax = capillary_plot.fig, capillary_plot.axs

        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.custom_toolbar = QtWidgets.QToolBar("Custom Toolbar", self)

        self.custom_toolbar.addAction('1', self.on_1_button_click)
        self.custom_toolbar.addAction('2', self.on_2_button_click)
        self.custom_toolbar.addAction('3', self.on_3_button_click)
        self.custom_toolbar.addAction('4', self.on_4_button_click)
        self.custom_toolbar.addAction('Satd', self.on_Satd_button_click)
        self.custom_toolbar.addAction('Legend', self.on_legend_button_click)

        self.layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.layout.addWidget(self.custom_toolbar)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

    def on_legend_button_click(self) :
        if self.capillary_plot.is_legend_visible :
            for ax in self.ax :
                legend = ax.legend()
                legend.remove()
            self.capillary_plot.is_legend_visible = False
        else :
            for ax in self.ax :
                ax.legend()
            self.capillary_plot.is_legend_visible = True
        self.capillary_plot.refresh()

    def switch_channel_linestyle(self, channel_index) :
        self.capillary_plot.switch_channel_visibility(channel_index)
        self.capillary_plot.update_channels_graphics()
        self.capillary_plot.refresh()

    on_1_button_click = functools.partialmethod(switch_channel_linestyle, 0)
    on_2_button_click = functools.partialmethod(switch_channel_linestyle, 1)
    on_3_button_click = functools.partialmethod(switch_channel_linestyle, 2)
    on_4_button_click = functools.partialmethod(switch_channel_linestyle, 3)

    def on_Satd_button_click(self) :
        self.capillary_plot.switch_saturation_visibility()
        self.capillary_plot.update_channels_graphics()
        self.capillary_plot.refresh()

class CapillaryDataPlot :
    def __init__(self, files, plt_theme="dark_background", channels=[1,2,3,4], show_satd=True) :

        plt.style.use(plt_theme)
        self.colors =  plt.rcParams['axes.prop_cycle'].by_key()['color']
        data = [ FsaData(file_name) for file_name in files ]
        data_length = len(data)
        ncol = (data_length > 4)+1
        nrow = math.ceil( data_length / ncol )
        self.fig, axs = plt.subplots( nrow, ncol, sharex = True )

        if data_length == 0 : return
        elif data_length == 1 : self.axs = [axs]
        elif data_length <= 4 :  self.axs = axs
        else :
            self.axs = [ ax for ax in itertools.chain(*axs) ]
            if data_length%2 :
                self.axs[-1].remove()
                del self.axs[-1]

        self.fluorescence_intensities_lines = []
        self.saturation_path_collections = []

        for capillary_data, ax in zip(data, self.axs) :
            data_length = capillary_data.get_scan_number()
            frames = np.arange(data_length)
            satd = capillary_data.get_saturated_frames()
            satd = np.array(satd, dtype=int)

            intensities_lines = list()
            satd_scattered = list()

            for channel_id in [1,2,3,4] :
                dye_name = capillary_data.get_dye_name(channel=channel_id)
                intensities = capillary_data.get_fluorescence_intensities(channel=channel_id)
                intensities = np.array(intensities, dtype=float)
                line, = ax.plot(frames, intensities, label=f"[{channel_id}]_{dye_name}")
                intensities_lines.append(line)
                scat = ax.scatter(satd, intensities[satd], label=f"")
                satd_scattered.append(scat)
            ax.set_xlabel("Frames (#)")
            ax.set_ylabel("Fluorescence Intensity (RFU)")

            self.fluorescence_intensities_lines.append(intensities_lines)
            self.saturation_path_collections.append(satd_scattered)

            ax.set_title( capillary_data.file_name )

        self.is_saturation_visible = show_satd
        self.is_channel_visible = [False, False, False, False]
        for index in channels :
            self.is_channel_visible[index-1] = True
        self.is_legend_visible = False
        self.update_channels_graphics()

    def refresh(self) :
        self.fig.canvas.draw()

    def set_channel_visibility(self, channel, is_visible) :
        self.is_channel_visible[channel] = is_visible
    def set_saturation_visibility(self, is_visible) :
        self.is_saturation_visible = is_visible
    def switch_channel_visibility(self, channel) :
        self.is_channel_visible[channel] = self.is_channel_visible[channel] == False
    def switch_saturation_visibility(self) :
        self.is_saturation_visible = self.is_saturation_visible == False

    def update_channels_graphics(self) :
        fluo_lines = self.fluorescence_intensities_lines
        satd_scats = self.saturation_path_collections

        for fluo_group, satd_group in zip( fluo_lines, satd_scats ) :
            for channel_id in [0,1,2,3] :
                fluo_line = fluo_group[channel_id]
                satd_scat = satd_group[channel_id]
                if self.is_channel_visible[channel_id] :
                    fluo_line.set_linestyle("-")
                    satd_scat.set_alpha(1)
                else :
                    fluo_line.set_linestyle("")
                    satd_scat.set_alpha(0)
                if not self.is_saturation_visible :
                    satd_scat.set_alpha(0)

def parse_commandline_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files",
        nargs="+",
        help="path to fsa files"
    )
    parser.add_argument(
        "--plt_theme",
        type=str,
        default="default",
        help="name of the matplotlib style to use" #https://matplotlib.org/stable/gallery/style_sheets/style_sheets_reference.html
    )
    parser.add_argument(
        "--channels",
        type=int,
        nargs="+",
        default=[1,2,3,4],
        help="channels to show at initialization"
    )
    parser.add_argument(
        "--no_satd",
        action="store_false",
        help="hide Satd markers"
    )
    parser.add_argument(
        "--window_size",
        nargs=2,
        type=int,
        help="width x height pixels size",
        default=[800,600]
    )
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    params = parse_commandline_arguments()
    files = params.files

    capillary_plot = CapillaryDataPlot(files,
        plt_theme=params.plt_theme,
        channels=params.channels,
        show_satd=params.no_satd
    )

    window = MatplotlibCustomToolbar(capillary_plot, params.window_size)
    window.show()
    app.exec_()
