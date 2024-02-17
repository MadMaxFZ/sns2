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
        self.update({"def_cam": FlyCamera()})
        self.curr_cam = self["def_cam"]

    def add_cam(self, new_cam, cam_label):
        if issubclass(new_cam, BaseCamera):
            if not cam_label:
                cam_label = "cam_" + str(len(self))
            self.update({cam_label: new_cam})
        self.curr_cam = self[cam_label]

    def cam_state(self, cam_key="def_cam"):
        cam_states = self[cam_key].get_state()
        for k, v in cam_states.items():
            print(f"{cam_key}.{k} : {v}")

        return cam_states


class CameraSetWidget(QWidget):
    """ This widget will display the state of a camera in
        the dictionary
    """
    def __init__(self):
        super(CameraSetWidget, self).__init__()
