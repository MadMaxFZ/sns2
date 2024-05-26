#! /usr/bin/python
import math
from collections import UserDict

import numpy as np
import astropy.units as u
from PyQt5.QtWidgets import QWidget
from vispy.scene import (BaseCamera, FlyCamera, TurntableCamera,
                         ArcballCamera, PanZoomCamera)
from sim_body import MIN_FOV
from psygnal import Signal


class CameraSet(UserDict):
    """     This class contains and manages a set of camera objects.
        The user may add camera objects in a list, and these cameras
        can be used in various views within an application.
    """
    _curr_key: str
    cam_types = [FlyCamera, TurntableCamera, ArcballCamera, PanZoomCamera]
    canvas_changed = Signal(str)

    # noinspection PyTypeChecker
    def __init__(self, data=None, dist_unit=None, vec_type=None):
        super().__init__()
        if data:
            self.data = {cam_id: self._validate_cam(cam)
                         for cam_id, cam in data.items()}
        else:
            self.data = {}  # super(CameraSet, self).__init__()

        if vec_type:
            self._vec_type = vec_type
        else:
            self._vec_type = type(np.zeros((3,), dtype=np.float64))

        if dist_unit:
            self._dist_unit = dist_unit
        else:
            self._dist_unit = u.km = u.km

        self._curr_key = "fly_cam"
        self._curr_cam = FlyCamera(fov=60, name=self._curr_key)
        self.update({self._curr_key: self._curr_cam})
        self.update({'tt_cam': TurntableCamera(name='tt_cam')})
        self._curr_cam.center = (-9851768.0, -9750760.0, -5012921.5)

    @staticmethod
    def _validate_cam(camera):
        if not issubclass(type(camera), BaseCamera):
            raise TypeError("Camera object expected")
        return camera

    def __set_item__(self, cam_id=None, new_cam=FlyCamera(fov=60)):
        """
        Parameters
        ----------
        cam_id  :   str
        new_cam :   is_subclass(vispy.scene.cameras.BaseCamera)

        Returns
        -------
        nothing :   if new_cam is a valid object, it is added to the CameraSet.
        """
        if not cam_id:
            cam_id = "cam_" + str(len(self.keys()))
        if self._validate_cam(new_cam):
            self.data[cam_id] = new_cam
            self._curr_key = cam_id
            self._curr_cam = new_cam

    def __getitem__(self, cam_id):
        return self.data[cam_id]

    def on_timer(self, ev):
        self.canvas_changed.emit('')

    @property
    def cam_count(self):
        return len(self.data)

    @property
    def curr_cam(self):
        return self._curr_cam

    @curr_cam.setter
    def curr_cam(self, cam_label):
        # if cam_label in self._cam_dict.keys():
        #     self._curr_cam = self._cam_dict[cam_label]
        self._curr_cam = self.data[cam_label]

    @property
    def curr_key(self):
        return self._curr_key

    def set_curr2key(self, new_key):
        if new_key in self.cam_ids:
            self._curr_key = new_key
            self._curr_cam = self.data[self._curr_key]
            return self._curr_cam

    @property
    def cam_ids(self):
        return list(self.data.keys())

    @property
    def cam_list(self):
        return self.data.values()

