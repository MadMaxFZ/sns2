# -*- coding: utf-8 -*-

# import logging
# from typing import List
# import autologging
# import numpy as np
# from vispy.scene import SceneCanvas, visuals
# from vispy.app.timer import Timer
# from composite import Ui_frm_sns_controls

import sys
import logging.config
from vispy.app import use_app
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication
from poliastro.bodies import Body
from astropy.units.quantity import Quantity

from camera_dict import CameraSet
from starsys_model import SimSystem
from sim_canvas import CanvasWrapper
from sim_controls import Controls
from starsys_visual import StarSystemVisuals
from starsys_data import log_config, SystemDataStore

logging.config.dictConfig(log_config)
QT_NATIVE = False
STOP_IT = True


def round_off(val):
    n_digits = 3
    factor = pow(10, n_digits)
    try:
        data_unit = val / val.value
        res = (int(val.value * factor) / factor) * data_unit

    except:
        res = val

    return res


def to_bold_font(value=None):
    """

    Parameters
    ----------
    value :

    Returns
    -------
    <html><head/><body><p><span style=" font-weight:600;">10</span></p></body></html>
    """


class MainQtWindow(QtWidgets.QMainWindow):
    """     This module contains MainQtWindow class, the entry point into the application and
        where access to all simulation components can be utilized to provide control of the sim.
    """
    # Signals for communication between simulation components:
    update_panel = pyqtSignal(list, dict)
    # newActiveBody = pyqtSignal(int)
    # newActiveTab = pyqtSignal(int)
    # newActiveCam = pyqtSignal(int)

    """     A dictionary of labels to act as keys to reference the data stored in the SimSystem model:
        The first four data elements must be computed every cycle regardless, while the remaining elements will
        only require updating if they are modified by the user at runtime. (Maybe separate the two sets?)
    """

    def __init__(self, _body_names=None, *args, **kwargs):
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.model = SimSystem()
        self.model.load_from_names()
        [sb.set_field_dict() for sb in self.model.data.values() if not sb.is_primary]
        self.cameras = CameraSet()
        self.canvas = CanvasWrapper(self.cameras)
        self.controls = Controls()
        self.ui = self.controls.ui
        self.central_widget = QtWidgets.QWidget()

        # Here we define sets of keys that will correspond to data fields in the model, visuals and cameras.
        # The first two are fields that exist for each SimBody (exceptr primary)
        # self._model_fields2agg = ('rad0', 'pos', 'rot', 'radius', 'elem_', 'is_primary',
        #                           )
        self._vizz_fields2agg = ('radius', 'body_alpha', 'track_alpha', 'body_mark',
                                 'body_color', 'track_data', 'tex_data', 'is_primary',
                                 )
        # This key set refers to fields that are common to the cameras (only FlyCameras right now)
        # self._cams_fields2agg = ('center', 'rot1', 'rot2', 'scale', 'fov', 'zoom')

        self.vizz_agg_data = self.model.get_agg_fields(self._vizz_fields2agg)
        # `this body_agg_data is not correct somehow
        self.visuals = StarSystemVisuals(self.model.body_names)
        self.visuals.generate_visuals(self.canvas.view,
                                      self.vizz_agg_data)
        # self.color_agg_data = self._get_vizz_agg_fields(self._color_fields2agg)                ###
        # self.cam_agg_data = self._get_cam_agg_fields(self._cams_fields2agg)

        self._setup_layout()
        self.init_controls()
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self.blockSignals(True)
        self.connect_slots()
        self.blockSignals(False)
        # self.model.update_state()

    def _setup_layout(self):
        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        self.central_widget.setLayout(main_layout)
        self.setCentralWidget(self.central_widget)

    def init_controls(self):
        self.ui.bodyList.clear()
        self.ui.bodyBox.clear()
        self.ui.bodyList.addItems(self.model.body_names)
        self.ui.bodyBox.addItems(self.model.body_names)
        self.ui.camBox.addItems(self.cameras.cam_ids)
        self.ui.bodyBox.setCurrentIndex(3)
        # self.ui.tabWidget_Body.setCurrentIndex(0)
        self.ui.camBox.setCurrentIndex(0)
        print("Controls initialized...")

    def connect_slots(self):
        """
            Connects slots to signals.
        """
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentIndexChanged.connect(self.setActiveBody)
        self.ui.bodyBox.currentIndexChanged.connect(self.updateOrbitPanels)
        self.ui.camBox.currentIndexChanged.connect(self.setActiveCam)
        # self.update_panel.connect(self.send_panel_data)
        # self.model.panel_data.connect(self.controls.refresh_panel)
        print("Slots Connected...")

        # TODO:: Review the data sent versus data expected, and fix if necessary
        # self.update_panel.emit([self.ui.bodyBox.currentIndex(),
        #                         self.ui.tabWidget_Body.currentIndex(),
        #                         self.ui.camBox.currentIndex(),
        #                         ], {})
        # print("Panel data sent...")

    @pyqtSlot(int)
    def setActiveBody(self, new_bod_idx):
        self.controls.active_bod = new_bod_idx
        self.refresh_panel('attr_')
        self.refresh_panel('elem')

    @pyqtSlot(int)
    def updateOrbitPanels(self, new_bod_idx):
        self.refresh_panel('elem_')

    @pyqtSlot(int)
    def setActiveCam(self, new_cam_id):
        self.controls.active_cam = new_cam_id
        self.refresh_panel('cam_')

    def refresh_panel(self, panel_key):
        """
            This method will return the data block for the selected target given
        Parameters
        ----------
        panel_key : str

        Returns
        -------
            Has no return value, but emits the data_set via signal
        """
        #
        # model_agg_data = {}
        widg_grp = self.controls.with_prefix(panel_key)
        curr_sb = self.model.data[self.curr_body_name]
        curr_cam_id = self.controls.ui.camBox.currentText()

        match panel_key:

            case 'elem_':
                # TODO:     Fix this such that the RV state is a separate 'panel' in which
                #           the vector components are stacked vertically...
                widg_grp = self.controls.with_prefix('elem_')
                r_str = "X: " + str(curr_sb.r[0]) + "\nY: " + str(curr_sb.r[1]) + "\nZ: " + str(curr_sb.r[2])
                v_str = "X: " + str(curr_sb.v[0]) + "\nY: " + str(curr_sb.v[1]) + "\nZ: " + str(curr_sb.v[2])
                if curr_sb.is_primary:
                    [w.setText("") for w in widg_grp]
                    widg_grp[-2].setText(r_str)
                    widg_grp[-1].setText(v_str)

                else:
                    data_set = self.model.data_group(sb_name=self.curr_body_name, tgt_key=panel_key)
                    print(f'widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                    for i, w in enumerate(widg_grp):
                        print(f'widget #{i}: {w.objectName()} -> {data_set[i]}')
                        w.setText(str(data_set[i]))

                    widg_grp[-2].setText(r_str)
                    widg_grp[-1].setText(v_str)

            case 'attr_':
                data_set = curr_sb.body
                print(f'{data_set}')
                print(f'panel_key: {panel_key}, widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                for i, data in enumerate(data_set):
                    if i == 0 and data:
                        data = data.name
                    if type(data) == Quantity:
                        res = round_off(data)
                    else:
                        res = data

                    print(f'widget #{i}: {widg_grp[i].objectName()} -> {str(res)}')
                    widg_grp[i].setText(str(res))

            case 'cam_':
                # TODO: output the get_state() dict, whatever it is, in (key, value) pairs of labels.
                i = 0
                for k, v in self.cameras.curr_cam.get_state().items():
                    self.controls.with_prefix('key_')[i].setText(str(k))
                    self.controls.with_prefix(panel_key)[i].setText(str(v))
                    i += 1

        pass
        # self.update_panel.emit(model_agg_data)

    @property
    def curr_body_name(self):
        return self.ui.bodyBox.currentText()


'''==============================================================================================================='''
if __name__ == "__main__":
    if QT_NATIVE:
        app = QCoreApplication(sys.argv)
        app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    else:
        app = use_app("pyqt5")
        app.create()

    sim = MainQtWindow()
    sim.show()

    if QT_NATIVE:
        sys.exit(app.exec_())
    else:
        app.run()
