#! /usr/bin/python
from PyQt5.QtWidgets import QWidget
from vispy.scene import (BaseCamera, FlyCamera, TurntableCamera,
                         ArcballCamera, PanZoomCamera)

class CameraSet(dict):
    """     This class contains and manages a set of camera objects.
        The user may add camera objects in a list, and these cameras
        can be used in various views within an application.
    """
    def __init__(self):
        super(CameraSet, self).__init__()
        self._curr_key = "def_cam"
        self.add_cam(self._curr_key, FlyCamera(fov=60))
        self._curr_cam = self[self._curr_key]

    def add_cam(self, cam_label=None, new_cam=FlyCamera(fov=60)):
        if issubclass(new_cam, BaseCamera):
            if not cam_label:
                cam_label = "cam_" + str(len(self))
            self.update({cam_label: new_cam})
        self._curr_key = cam_label
        self._curr_cam = self[self._curr_key]

    def cam_state(self, cam_key=None):
        if not cam_key:
            cam_key = self._curr_key
        cam_states = self[cam_key].get_state()
        for k, v in cam_states.items():
            print(f"{cam_key}.{k} : {v}")

        return cam_states

    @property
    def cam_count(self):
        return len(self.keys())

    @property
    def curr_cam(self):
        return self[self._curr_key]

    @property
    def curr_key(self):
        return self._curr_key


class CameraSetWidget(QWidget):
    """ This widget will display the state of a camera in
        the dictionary
    """
    def __init__(self):
        super(CameraSetWidget, self).__init__()
