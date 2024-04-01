# -*- coding: utf-8 -*-

"""
    This module contains classes to allow using Qt to control Vispy
"""

import logging
import logging.config
from typing import List

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
#from composite import Ui_frm_sns_controls
from tiled import Ui_SNS_DataPanels
from src.starsys_data import log_config

logging.config.dictConfig(log_config)

QT_NATIVE = False


class Controls(QtWidgets.QWidget):
    data_request = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Controls, self).__init__(parent)
        # self.ui = Ui_frm_sns_controls()
        self.ui = Ui_SNS_DataPanels()
        self.ui.setupUi(self)
        self.ui_obj_dict = self.ui.__dict__
        # logging.info([i for i in self.ui.__dict__.keys() if (i.startswith("lv") or "warp" in i)])
        self._pattern_names = ['attr_', 'elem_', 'cam_', 'elem_coe_', 'elem_pqw_', 'elem_rv_',
                               'tw_', 'twb_', 'axis_']
        self._tab_names = ['elem_', 'syst_', 'vizz_']
        self._widget_groups = self._scanUi_4panels(patterns=self._pattern_names)
        print(f'{len(self._widget_groups)} widget groups (panels) defined...\n\t-> CONTROLS initialized...')
        self.active_bod = 0
        self.active_pnl = 0
        self.active_cam = 0

    # @pyqtSlot(int)
    # def newActiveBody(self, new_body_idx):
    #     self._active_body_idx = new_body_idx
    #     self.refresh_panel('attr_', new_body_idx)
    #
    # @pyqtSlot(int)
    # def newActiveTab(self, new_panel_idx):
    #     self._active_panl_idx = new_panel_idx
    #     self.refresh_panel('panel', new_panel_idx)
    #
    # @pyqtSlot(int)
    # def newActiveCam(self, new_cam_idx):
    #     self._active_cmid_idx = new_cam_idx
    #     self.refresh_panel('cam_', new_cam_idx)

    def with_prefix(self, prefix):
        res = {}
        [res.update({name: widget})
         for name, widget in self.ui_obj_dict.items()
         if name.startswith(prefix)
         ]

        return res

    def _scanUi_4panels(self, patterns: List[str]) -> dict:
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

    # @pyqtSlot(str, str)
    # def refresh_panel(self, tgt_group, tgt_bname):
    #     """
    #         This method is called when the simulation panel needs to be refreshed.
    #     Parameters
    #     ----------
    #     tgt_group      :   key for a widget_group in the _widget_groups dict,
    #                     also it is a key for a set of values from the model.
    #     tgt_bname      :   the name of the SimBody to be used in the refresh.
    #
    #     Returns
    #     -------
    #     nothing     :   applies a tuple of values from the model based upon the target key
    #                     to the currentText field of the widgets identified by the key.
    #     """
    #     if tgt_group in ['attr_', 'elem_', 'syst_']:
    #         new_data = self.model.data_group(sb_name=tgt_bname,
    #                                          tgt_group=tgt_group)
    #         for i, w in enumerate(self.widget_group[tgt_group]):
    #             print(f'widget#{i:>2}: {w}\n\tdata: {new_data[i]}')
    #             try:
    #                 w.setCurrentText(new_data[i])
    #             except:
    #                 print(f'>>>ERROR: Did not like widget {i}: {w} set to {new_data[i]}')
    #
    #     elif tgt_group == 'cams_':
    #         pass

    @property
    def widget_group(self, group_name=None):
        if group_name is None:
            return self._widget_groups
        elif group_name in self._widget_groups.keys():
            return self._widget_groups[group_name]
        else:
            raise ValueError(f'>>>ERROR: {group_name} is not a valid widget group name.')
