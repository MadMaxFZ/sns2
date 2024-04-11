# -*- coding: utf-8 -*-
"""
    This module contains classes to allow using Qt to control Vispy
"""
import logging.config
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from gui_tiled import Ui_SNS_DataPanels
from starsys_data import log_config
from starsys_data import DEF_EPOCH0 as DEF_EPOCH

logging.config.dictConfig(log_config)


class Controls(QtWidgets.QWidget):
    new_active_body = pyqtSignal(str)
    new_active_camera = pyqtSignal(str)

    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)
        self.ui = Ui_SNS_DataPanels()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        self._pattern_names = ['attr_', 'elem_', 'cam_', 'elem_coe_', 'elem_pqw_', 'elem_rv_',
                               'time_', 'btn_', 'axis_', 'key_']
        self._widget_groups = self._scanUi_4panels(patterns=self._pattern_names)
        print(f'{len(self._widget_groups)} widget groups (panels) defined...\n\t-> CONTROLS initialized...')
        self._active_body = 'Earth'
        self._active_cam = 'def_cam'
        self.timer_widgets = self._widget_groups['time_']

    def with_prefix(self, prefix):
        return [widget for name, widget in self.ui.__dict__.items()
                if name.startswith(prefix)
                ]

    def _scanUi_4panels(self, patterns: list[str]) -> dict:
        """ This method identifies objects that contain one of the strings in the patterns list.
            The objects containing each pattern are collected into a dict with the pattern
            as the key with the value being a list of objects containing that pattern.

        Parameters
        ----------
            patterns :  a list of strings that the object names are matched to

        Returns
        -------
            dict     : a dict with the pattern string as a key and the value is a list of
                       the objects whose name contains that string.
        """
        panels = {}
        for p in patterns:
            panels.update({p: self.with_prefix(p)})

        return panels

    def init_controls(self, body_names, cam_ids):
        self.ui.bodyList.clear()
        self.ui.bodyBox.clear()
        self.ui.bodyList.addItems(body_names)
        self.ui.bodyBox.addItems(body_names)
        self.ui.camBox.addItems(cam_ids)
        self.ui.bodyBox.setCurrentIndex(3)
        self.ui.camBox.setCurrentIndex(0)
        self.init_epoch_timer()
        print("Controls initialized...")

    def init_epoch_timer(self, wexp=1, ref_epoch=DEF_EPOCH,):
        # [print(f'{k}:\t{v.objectName()}:\t{v}') for k, v in enumerate(self.timer_widgets)]
        print(f'JD1:\t{ref_epoch.jd1}\nJD2:\t{ref_epoch.jd2}')

        self.ui.time_ref_epoch.setText(str(ref_epoch.jd1))
        self.ui.time_elapsed.setText(f'{str(0)}')
        self.ui.time_wexp.setValue(wexp)
        self.ui.time_wmax.setText(str(pow(10, wexp)))
        self.ui.time_slider.setMinimum(0)
        self.ui.time_slider.setMaximum(int(self.ui.time_wmax.text()))
        self.ui.time_slider.setValue(0)
        self.ui.time_warp.setText(str(self.ui.time_slider.value()))
        self.ui.time_sys_epoch.setText(str(self.ui.time_ref_epoch.text()))

    def update_epoch_timer(self):
        self.ui.time_sys_epoch.setText(self.ui.time_ref_epoch +
                                       self.ui.time_slider.value() *
                                       float(self.ui.time_elapsed.text()))

    def set_active_cam(self, cam_id):
        print()
        self._active_cam = cam_id

    def set_active_body(self, body_name):
        self._active_body = body_name

    def widget_group(self, prefix=None):

        if prefix is None:
            return self._widget_groups.keys()
        elif prefix in self._widget_groups.keys():
            return self._widget_groups[prefix]
        else:
            raise ValueError(f'>>>ERROR: {prefix} is not a valid widget group name.')

