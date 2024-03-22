# -*- coding: utf-8 -*-
import logging
import psygnal
from vispy.app.timer import Timer
from vispy import app, scene
from vispy.color import Color
# from starsys_data import sys_data
from starsys_model import StarSystemModel

logging.basicConfig(filename="logs/mainsimwin.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class MainSimCanvas(scene.SceneCanvas):
    FIRST_RUN = True
    emit_keypress = psygnal.Signal(str)

    #   TODO::  Refactor to remove all references to the StarSystemModel instance.
    #           This class only needs to handle the CameraSet and key/mouse events here.
    #           There may need to be methods added to handle some operations for this SceneCanvas.
    def __init__(self, camera_set):
        super(MainSimCanvas, self).__init__(keys="interactive",
                                            size=(800, 600),
                                            show=False,
                                            bgcolor=Color("black"),
                                            title="SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten",
                                            )
        self.unfreeze()
        self._sys_vizz = None
        # self._cam_set = cam_set
        self._fpv_viewbox = self.central_widget.add_view()
        # self._fpv_viewbox.camera = None
        self.freeze()

        # for k, v in self._fpv_viewbox.camera.get_state().items():
        #     print(k, ":", v)

    #   TODO::  Implement a class that accepts a keystroke value then calls a
    #           function associated with that value. These associations will be
    #           represented with a dict that can be stored, modified or loaded
    #           from a file.

    def assign_camera(self, new_cam):
        self._fpv_viewbox.camera = new_cam

    def on_key_press(self, ev):
        try:
            self.emit_keypress.emit(ev)
            if ev.key.name == "+":
                self._fpv_viewbox.camera.scale_factor *= 1.1
                print("SCALE_FACTOR", self._fpv_viewbox.camera.scale_factor)
            elif ev.key.name == "-":
                self._fpv_viewbox.camera.scale_factor *= 0.9
                print("SCALE_FACTOR", self._fpv_viewbox.camera.scale_factor)
            elif ev.key.name == "*":
                self._fpv_viewbox.camera.fov *= 1.5
                print("CAM_FOV", self._fpv_viewbox.camera.fov)
            elif ev.key.name == "/":
                self._fpv_viewbox.camera.fov *= 0.75
                print("CAM_FOV", self._fpv_viewbox.camera.fov)
            elif ev.key.name == "]":
                self.model.t_warp *= 1.1
                print("TIME_WARP:", self.model.t_warp)
            elif ev.key.name == "[":
                self.model.t_warp *= 0.9
                print("TIME_WARP:", self.model.t_warp)
            elif ev.key.name == "\\":
                print("Toggle timer...")
            elif ev.key.name == "p":
                print("MESH_DATA[\"Sun\"]", self._sys_vizz.mesh_data["Sun"].save())
            elif ev.key.name == "'":
                new_aplha = (self._fpv_viewbox.skymap.mesh.meshdata.color[3] + .1) % 1
                self._fpv_viewbox.skymap.mesh.meshdata.color[3] = new_aplha

        except AttributeError:
            print("Key Error...")

    # def run(self):
    #     self.show()
    #     self._system_model.cmd_timer()
    #     app.run()
    #
    # def toggle_timer(self):
    #     self._system_model.cmd_timer()
    #
    # @property
    # def model(self):
    #     return self._system_model

    def quit(self):
        app.quit()

    @property
    def curr_cam(self):
        return self._fpv_viewbox.camera.get_state()

    @property
    def view(self):
        return self._fpv_viewbox

    @property
    def vizz(self):
        return self._sys_vizz


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


if __name__ == "__main__":

    main()
