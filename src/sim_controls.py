# -*- coding: utf-8 -*-
"""
    This module contains classes to allow using Qt to control Vispy
"""
import logging.config
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from gui_tiled import Ui_SNS_DataPanels
from starsys_data import log_config

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
                               'tw_', 'twb_', 'axis_', '_key']
        self._widget_groups = self._scanUi_4panels(patterns=self._pattern_names)
        print(f'{len(self._widget_groups)} widget groups (panels) defined...\n\t-> CONTROLS initialized...')
        self._active_body = 'Earth'
        self._active_cam = 'def_cam'

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

    def set_active_cam(self, cam_id):
        print()
        self._active_cam = cam_id

    def set_active_body(self, body_name):
        self._active_body = body_name

    @property
    def widget_group(self, prefix=None):
        if prefix is None:
            return self._widget_groups
        elif prefix in self._widget_groups.keys():
            return self._widget_groups[prefix]
        else:
            raise ValueError(f'>>>ERROR: {prefix} is not a valid widget group name.')

