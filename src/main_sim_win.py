# -*- coding: utf-8 -*-

# import logging
# from typing import List
# import autologging
# import numpy as np
# from vispy.scene import SceneCanvas, visuals
# from vispy.app.timer import Timer
# from composite import Ui_frm_sns_controls

import cProfile
import math
import pstats
import sys
import logging.config

import psygnal
from vispy.app import use_app
from vispy.util.quaternion import Quaternion
from PyQt5 import QtWidgets, QtCore, Qt
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication
from poliastro.bodies import Body
from astropy.units.quantity import Quantity
from astropy.time import Time
from starsys_model import SystemWrapper
from sim_canvas import CanvasWrapper
from sim_controls import Controls
from starsys_visual import StarSystemVisuals
from starsys_data import *

logging.config.dictConfig(log_config)
QT_NATIVE = False
STOP_IT = True
DO_PROFILE = False


# noinspection PyArgumentList
class MainQtWindow(QtWidgets.QMainWindow):
    """     This module contains MainQtWindow class, the entry point into the application and
        where access to all simulation components can be utilized to provide control of the sim.
    """
    # Signals for communication between simulation components:
    main_window_ready = pyqtSignal(str)
    panel_refreshed = pyqtSignal(str)
    on_draw_sig    = psygnal.Signal(str)
    vispy_keypress = psygnal.Signal(str)
    # newActiveTab = pyqtSignal(int)
    # newActiveCam = pyqtSignal(int)

    """     A dictionary of labels to act as keys to reference the data stored in the SimSystem model:
        The first four data elements must be computed every cycle regardless, while the remaining elements will
        only require updating if they are modified by the user at runtime. (Maybe separate the two sets?)
    """

    def __init__(self, _body_names=None, *args, **kwargs):
        """
            Here we initialize the primary QMainWindow that will interface to the Simulation.

        Parameters
        ----------
        _body_names :
        args        :
        kwargs      :
        """
        super(MainQtWindow, self).__init__(*args,
                                           **kwargs)
        self.timer_paused = True
        self.interval = 10
        self.tw_hold = 0
        self.setWindowTitle("SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten")
        self.system = SystemWrapper(auto_up=False)
        # self.model = self.system.model
        self.system.model.load_from_names()
        # [sb.set_field_dict() for sb in self.system.model.data.values()]    # if not sb.is_primary]

        #       TODO:   Encapsulate the creation of the CameraSet instance inside the
        #               CanvasWrapper class, which will expose methods to manipulate the cameras.
        #       CONSIDER:   Encapsulating the CanvasWrapper instance inside the
        #                   StarSystemVisuals class, which would assume the role of CanvasWrapper
        self.canvas = CanvasWrapper(self.on_draw_sig, self.vispy_keypress)
        self.cameras = self.canvas.cam_set
        self.controls = Controls()
        self.ui = self.controls.ui
        self.central_widget = QtWidgets.QWidget(self)
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)

        #       TODO:   Encapsulate the vizz_fields2agg inside StartSystemVisuals class
        self._vizz_fields2agg = ('pos', 'radius', 'body_alpha', 'track_alpha', 'body_mark',
                                 'body_color', 'track_data', 'tex_data', 'is_primary',
                                 'axes', 'rot', 'parent_name'
                                 )
        self.visuals = StarSystemVisuals(self.system.model.body_names)
        self.visuals.generate_visuals(self.canvas.view,
                                      self.system.model.get_agg_fields(self._vizz_fields2agg))

        self._setup_layout()
        self.controls.init_controls(self.system.model.body_names, self.cameras.cam_ids)
        # self.thread = QThread()
        # self.model.moveToThread(self.thread)
        # self.thread.start()
        self._connect_slots()
        self.cameras.curr_cam.set_range(x=self.visuals.vizz_bounds,
                                        y=self.visuals.vizz_bounds,
                                        z=self.visuals.vizz_bounds,
                                        )
        # set the initial camera position in the ecliptic looking towards the primary
        self.cameras.curr_cam.set_state({'center': (0.0, -8.0e+08, 0.0),
                                         'scale_factor': 0.5e+08,
                                         'rotation1': Quaternion(+0.7071, -0.7071, +0.0, +0.0),
                                         }
                                        )
        self.reset_rotation()
        self.main_window_ready.emit('Earth')
        self._last_elapsed = 0.0

    def _key_handler(self, key_chr):
        match key_chr:

            case "[":
                # lower time warp
                pass

            case "]":
                # increase time warp
                pass

            case "[":
                pass

    def _setup_layout(self):
        # TODO:     Learn more about the QSplitter object
        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.controls)
        splitter.addWidget(self.canvas.native)
        main_layout.addWidget(splitter)
        self.central_widget.setLayout(main_layout)
        self.setCentralWidget(self.central_widget)

    def _connect_slots(self):
        """
            Connects slots to signals.
        """
        self.blockSignals(True)
        # Handling signals when GUI created
        self.main_window_ready.connect(self.setActiveBody)
        self.main_window_ready.connect(self.setActiveCam)
        self.main_window_ready.connect(self.refresh_canvas)
        self.canvas.key_sig.connect(self._key_handler)

        # Handling changes in the GUI
        self.ui.bodyBox.currentIndexChanged.connect(self.ui.bodyList.setCurrentRow)
        self.ui.bodyList.currentRowChanged.connect(self.ui.bodyBox.setCurrentIndex)
        self.ui.bodyBox.currentTextChanged.connect(self.setActiveBody)
        self.ui.camBox.currentTextChanged.connect(self.setActiveCam)

        #   Handling epoch timer widget signals
        self.ui.time_wexp.valueChanged.connect(self.controls.tw_exp_updated)
        self.ui.time_slider.valueChanged.connect(self.controls.tw_slider_updated)
        self.ui.time_elapsed.textChanged.connect(self.controls.tw_elapsed_updated)
        self.ui.time_sys_epoch.textChanged.connect(self.update_model_epoch)
        self.ui.time_sys_epoch.textChanged.connect(self.updatePanels)
        self.system.model.has_updated.connect(self.canvas.update_canvas)
        self.system.model.has_updated.connect(self.refresh_canvas)

        self.timer.setInterval(self.interval)
        self.timer.timeout.connect(self.update_elapsed)

        # Handling buttons in epoch timer
        self.ui.btn_play_pause.pressed.connect(self.toggle_play_pause)
        self.ui.btn_real_twarp.pressed.connect(self.controls.toggle_twarp2norm)
        self.ui.btn_reverse.pressed.connect(self.controls.toggle_twarp_sign)
        self.ui.btn_stop_reset.pressed.connect(self.controls.reset_epoch_timer)
        self.ui.btn_set_rot.pressed.connect(self.reset_rotation)
        self.blockSignals(False)
        print("Signals / Slots Connected...")

    def reset_rotation(self):
        self.cameras.curr_cam.set_default_state()
        self.cameras.curr_cam.reset()
        self.updatePanels('')

    def update_elapsed(self):
        self.ui.time_elapsed.setText(f'{(float(self.ui.time_elapsed.text()) + self.interval / 86400):.4f}')

    @property
    def curr_body_name(self):
        return self.ui.bodyBox.currentText()

    @pyqtSlot(str)
    def setActiveBody(self, new_body_name):
        if new_body_name in self.system.model.body_names:
            self.controls.set_active_body(new_body_name)
            if self.ui.cam2selected.isChecked():
                pass
                # self.cameras.curr_cam.set_state()

        self.refresh_panel('attr_')
        self.updatePanels('')

    @pyqtSlot(str)
    def updatePanels(self, new_bod_idx):
        self.refresh_panel('elem_coe_')
        self.refresh_panel('elem_rv_')
        self.refresh_panel('elem_pqw_')
        self.refresh_panel('cam_')

    @pyqtSlot(str)
    def setActiveCam(self, new_cam_id):
        if new_cam_id in self.cameras.cam_ids:
            self.canvas.view.camera = self.cameras.set_curr2key(new_cam_id)
            self.canvas.view.camera = self.cameras.curr_cam

        self.refresh_panel('cam_')

    @pyqtSlot()
    def refresh_canvas(self):
        self.visuals.update_vizz(self.system.model.get_agg_fields(self._vizz_fields2agg))
        self.canvas.update_canvas()
        self.updatePanels('')

    @pyqtSlot()
    def update_model_epoch(self):
        self.system.model.epoch = Time(self.ui.time_sys_epoch.text(), format='jd')
        if not self.system.model._USE_AUTO_UPDATE_STATE:
            self.system.model.update_state(self.system.model.epoch)

    @pyqtSlot()
    def toggle_play_pause(self):
        if self.timer_paused:
            self.ui.time_warp.setText(f'{self.tw_hold}')
            self.timer_paused = False
            self.timer.start()
            # self.ui.time_elapsed.setText(f'{(float(self.ui.time_elapsed.text()) + DEFAULT_DT):.4f}')
        else:
            self.tw_hold = float(self.ui.time_warp.text())
            self.timer_paused = True
            self.timer.stop()

    @pyqtSlot(str)
    def refresh_panel(self, panel_key):
        """
            This method will return the data block for the selected target given
        Parameters
        ----------
        panel_key : str     A tag to serve as a key to indicate which panels(s) to update

        Returns
        -------
            Has no return value, but emits the panel_key via the signal
        """
        widg_grp    = self.controls.widget_group(panel_key)
        # show_it(widg_grp)
        curr_simbod = self.system.model.data[self.controls.ui.bodyBox.currentText()]
        curr_cam_id = self.controls.ui.camBox.currentText()

        match panel_key:

            case 'elem_coe_':
                if curr_simbod.is_primary:
                    for w in widg_grp:
                        w.setText('')
                else:
                    data_set = self.system.model.data_group(sb_name=curr_simbod.name, tgt_key=panel_key)
                    # print(f'widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                    for i, w in enumerate(widg_grp):
                        # print(f'widget #{i}: {w.objectName()} -> {data_set[i]}')
                        w.setText(str(data_set[i].round(4)))

            case 'elem_rv_':
                [w.setText("") for w in widg_grp]
                self.ui.elem_rv_0.setText(to_vector_str(curr_simbod.r.value))
                self.ui.elem_rv_1.setText(to_vector_str(curr_simbod.v.value))
                self.ui.elem_rv_3.setText(to_vector_str(curr_simbod.rot,
                                                        ('RA: ', '\nDEC:', '\nW:  '))
                                          )

            case 'elem_pqw_':
                if curr_simbod.is_primary:
                    for w in widg_grp:
                        w.setText('')
                else:
                    data_set = self.system.model.data_group(sb_name=curr_simbod.name, tgt_key=panel_key)
                    # print(f'widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                    for i, w in enumerate(widg_grp):
                        # print(f'widget #{i}: {w.objectName()} -> {data_set[i]}')
                        w.setText(str(to_vector_str(data_set[i])))

            case 'attr_':
                data_set = curr_simbod.body
                # print(f'{data_set}')
                # print(f'panel_key: {panel_key}, widg_grp: {len(widg_grp)}, data_set: {len(data_set)}')
                for i, data in enumerate(data_set):
                    if type(data) == Body:
                        res = data.name
                    elif type(data) == Quantity:
                        res = f'{data:.4e}'
                    elif type(data) == str:
                        res = f'{data}'
                    else:
                        res = data

                    # print(f'widget #{i}: {widg_grp[i].objectName()} -> {str(res)}')
                    widg_grp[i].setText(str(res))

            case 'cam_':
                # TODO: output the get_state() dict, whatever it is, in (key, value) pairs of labels.
                i = 0
                cam_state = self.cameras.curr_cam.get_state()
                key_widgs = self.controls.widget_group('key_')
                # [print(f'{k} has type {type(v)} with value {v}') for k, v in cam_state.items()]
                for k, v in cam_state.items():
                    key_widgs[i].setText(str(k))
                    match str(type(v)):

                        case "<class \'float\'>":
                            res = f'{v:.4}'

                        case "<class \'tuple\'>":
                            res = to_vector_str(v)

                        case "<class \'vispy.util.quaternion.Quaternion\'>":
                            res = to_quat_str(v)
                            widg_grp[i].setText(res)
                            key_widgs[-1].setText('Attitude:')
                            widg_grp[-1].setText(to_euler_str(v))
                            break

                        case _:
                            res = ''

                    widg_grp[i].setText(res)
                    i += 1

        self.panel_refreshed.emit(panel_key)


def main():
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


'''==============================================================================================================='''
if __name__ == "__main__":

    if DO_PROFILE:
        cProfile.run('main()', sort='tottime')
    else:
        main()
