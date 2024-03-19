#! /usr/bin/python
import math

import numpy as np
from PyQt5.QtWidgets import QWidget
from vispy.scene import (BaseCamera, FlyCamera, TurntableCamera,
                         ArcballCamera, PanZoomCamera)

from starsys_data import vec_type
from sysbody_model import MIN_FOV


class CameraSet:
    """     This class contains and manages a set of camera objects.
        The user may add camera objects in a list, and these cameras
        can be used in various views within an application.
    """
    cam_types = [FlyCamera, TurntableCamera, ArcballCamera, PanZoomCamera]

    def __init__(self):
        self._cam_dict = {}  # super(CameraSet, self).__init__()
        self._cam_count = 0
        self._curr_key = ""
        self._curr_cam = None
        self.add_cam("def_cam", FlyCamera(fov=60))

    def add_cam(self, cam_label=None, new_cam=FlyCamera(fov=60)):
        """
        Parameters
        ----------
        cam_label : str
        new_cam :   is_subclass(vispy.scene.cameras.BaseCamera)

        Returns
        -------
        """
        assert issubclass(type(new_cam), BaseCamera)
        if not cam_label:
            cam_label = "cam_" + str(self._cam_count)
        self._cam_dict.update({cam_label: new_cam})
        self._curr_key = cam_label
        self._curr_cam = new_cam
        self._cam_count += 1

    def cam_state(self, cam_key=None):
        if not cam_key:
            cam_key = self._curr_key

        cam_states = self._cam_dict[cam_key].get_state()
        for k, v in cam_states.items():
            print(f"{cam_key}.{k} : {v}")

        return cam_states

    @property
    def cam_count(self):
        return self._cam_count

    @property
    def curr_cam(self):
        return self._curr_cam

    @curr_cam.setter
    def curr_cam(self, cam_label):
        if cam_label in self._cam_dict.keys():
            self._curr_cam = self._cam_dict[cam_label]

    @property
    def curr_key(self):
        return self._curr_key


class CameraSetWidget(QWidget):
    """ This widget will display the state of a camera in
        the dictionary
    """

    def __init__(self):
        super(CameraSetWidget, self).__init__()
