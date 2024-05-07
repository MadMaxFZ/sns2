# -*- coding: utf-8 -*-
import logging
import psygnal
from vispy.app.timer import Timer
from PyQt5.QtCore import pyqtSignal
from vispy import app, scene
from vispy.color import Color
from vispy.scene.cameras import BaseCamera
from camera_dict import CameraSet

logging.basicConfig(filename="logs/mainsimwin.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class CanvasWrapper:
    """     This class simply encapsulates the simulation, which resides within
        the vispy SceneCanvas object.
    """
    #   TODO:: Be prepared to add some methods to this class
    qt_keypress = pyqtSignal(str)
    qt_mouse_move = pyqtSignal()

    def __init__(self, on_draw_sig, vispy_kb_sig):
        self._canvas = MainSimCanvas(on_draw_sig, vispy_kb_sig)
        self._scene = self._canvas.view.scene
        self._view = self._canvas.view

    def update_canvas(self):
        # pass
        self._canvas.draw_scene()

    @property
    def up_sig(self):
        return self._canvas.update_signal

    @property
    def key_sig(self):
        return self._canvas.keybrd_signal

    @property
    def curr_cam(self):
        return self._canvas.curr_cam

    @property
    def curr_cam_state(self):
        return self._canvas.curr_cam.get_state()

    @property
    def native(self):
        return self._canvas.native

    @property
    def view(self):
        return self._canvas.view

    @property
    def scene(self):
        return self._scene

    @property
    def cam_set(self):
        return self._canvas.cam_set


class MainSimCanvas(scene.SceneCanvas):
    FIRST_RUN = True
    vispy_keypress = psygnal.Signal(str)
    vispy_mouse_move = psygnal.Signal()

    #   TODO::  Refactor to remove all references to the StarSystemModel instance.
    #           This class only needs to handle the CameraSet and key/mouse events here.
    #           There may need to be methods added to handle some operations for this SceneCanvas.
    def __init__(self, up_sig, key_sig):
        super(MainSimCanvas, self).__init__(keys="interactive",
                                            size=(800, 600),
                                            show=False,
                                            bgcolor=Color("black"),
                                            title="SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten",
                                            )
        self.unfreeze()
        self._sys_vizz = None
        self._cam_set = CameraSet()
        self._viewbox = self.central_widget.add_view()
        self.update_signal = up_sig
        self.keybrd_signal = key_sig
        self.assign_camera(new_cam=self._cam_set.curr_cam)
        self.freeze()

        # for k, v in self._fpv_viewbox.camera.get_state().items():
        #     print(k, ":", v)

    def assign_camera(self, new_cam=None):
        """         Sets the Assigns the new_cam to the viewbox.
        Parameters
        ----------
            new_cam :   is_subclass(vispy.scene.cameras.BaseCamera)
                The new camera to be assigned to the viewbox.

        Returns
        -------
            None, but the camera is set to the new_cam.
        """
        if not new_cam:
            new_cam = self._cam_set.curr_cam

        if issubclass(type(new_cam), BaseCamera):
            self._viewbox.camera = new_cam

    def on_key_press(self, ev):
        """
            TODO::>    Implement a method in CanvasWrapper to forward keyboard events here if they
                     are not handled by the CanvasWrapper object,
                     OR have the CanvasWrapper call methods here in response to Qt parent window

                  >    Implement a class that accepts a keystroke value then calls a
                     function associated with that value. These associations will be
                     represented with a dict that can be stored, modified or loaded
                     from a file.
        """
        try:
            vispy_keypress.emit(ev.key.name)
            if ev.key.name == "+":          # increase camera scale factor
                self._viewbox.camera.scale_factor *= 1.1
                print("SCALE_FACTOR", self._viewbox.camera.scale_factor)

            elif ev.key.name == "-":        # decrease camera scale factor
                self._viewbox.camera.scale_factor *= 0.9
                print("SCALE_FACTOR", self._viewbox.camera.scale_factor)

            elif ev.key.name == "*":        # increase camera FOV
                self._viewbox.camera.fov *= 1.5
                print("CAM_FOV", self._viewbox.camera.fov)

            elif ev.key.name == "/":        # decrease camera FOV
                self._viewbox.camera.fov *= 0.75
                print("CAM_FOV", self._viewbox.camera.fov)

            elif ev.key.name == "]":        # increase time warp factor
                pass
                # self.model.t_warp *= 1.1
                # print("TIME_WARP:", self.model.t_warp)

            elif ev.key.name == "[":        # decrease time warp factor
                pass
                # self.model.t_warp *= 0.9
                # print("TIME_WARP:", self.model.t_warp)

            elif ev.key.name == "\\":       # toggle timer on/off
                print("Toggle timer...")

            elif ev.key.name == "p":        # print mesh data for Sun
                print("MESH_DATA[\"Sun\"]", self._sys_vizz.mesh_data["Sun"].save())

            elif ev.key.name == "'":        # rotate the skymap grid line color
                new_aplha = (self._viewbox.skymap.mesh.meshdata.color[3] + .1) % 1
                self._viewbox.skymap.mesh.meshdata.color[3] = new_aplha

            else:
                pass

        except AttributeError:
            print("Key Error...")

    def draw_scene(self):
        self.update()
        # self.update_signal.emit('')

    def quit(self):
        app.quit()

    @property
    def curr_cam_state(self):
        return self._cam_set.curr_cam.get_state()

    @property
    def curr_cam(self):
        return self._cam_set.curr_cam

    @property
    def view(self):
        return self._viewbox

    @property
    def vizz(self):
        return self._sys_vizz

    @property
    def cam_set(self):
        return self._cam_set


if __name__ == "__main__":
    def main():
        _body_include_set = ['Sun',
                             'Mercury',
                             'Venus',
                             'Earth',
                             'Moon',  # all built-ins from poliastro
                             'Mars',
                             'Jupiter',
                             'Saturn',
                             'Uranus',
                             'Neptune',
                             'Pluto',
                             # 'Phobos',
                             # 'Deimos',
                             # 'Europa',
                             # 'Ganymede',
                             # 'Enceladus',
                             # 'Titan',
                             # 'Titania',
                             # 'Triton',
                             # 'Charon',
                             ]
        my_simwin = MainSimCanvas()
        my_simwin.run()

    main()
