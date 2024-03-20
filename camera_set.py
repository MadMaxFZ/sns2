#! /usr/bin/python
import math
import numpy as np
import astropy.units as u
from PyQt5.QtWidgets import QWidget
from vispy.scene import (BaseCamera, FlyCamera, TurntableCamera,
                         ArcballCamera, PanZoomCamera)
from starsys_data import vec_type, dist_unit
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

    def rel2cam(self, tgt_pos, tgt_radius):
        """
            This method is used to get the position of a SimBody object relative to the current camera.
        Parameters
        ----------
        tgt_pos     :   vec_type    :   The position vector of the target SimBody object.

        tgt_radius  :   float       :   The radius of the target SimBody object.

        Returns
        -------
        res         :   dict        :   The relative position, distance to and FOV of the SimBody object.
        """
        rel_2cam = (tgt_pos - self._curr_cam.center)
        dist = np.linalg.norm(rel_2cam)
        if dist < 1e-09:
            dist = 0.0 * dist_unit
            rel_pos = np.zeros((3,), dtype=vec_type)
            fov = MIN_FOV
        else:
            fov = np.float64(math.atan(tgt_radius.value / dist))
            # print(f' FOV : {fov:.4f}')

        return {"rel_pos": rel_2cam * dist_unit,
                "dist": dist * dist_unit,
                "fov": fov * u.rad,
                }

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
