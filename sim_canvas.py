# -*- coding: utf-8 -*-
# x
import logging
from vispy.app.timer import Timer
from vispy import app, scene
from vispy.color import Color
from starsys_data import sys_data
from starsys_model import StarSystemModel
from starsys_visual import StarSystemView
from camera_set import CameraSet

logging.basicConfig(filename="logs/mainsimwin.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class MainSimCanvas(scene.SceneCanvas):
    FIRST = True

    def __init__(self, body_names=sys_data.body_names):
        super(MainSimCanvas, self).__init__(keys="interactive",
                                            size=(850, 600),
                                            show=False,
                                            bgcolor=Color("black"),
                                            )
        self.unfreeze()
        self._system_model = StarSystemModel(body_names=body_names)
        # TODO: Set up a system view with a FlyCamera,
        #       a secondary box with a Body list along
        #       with a view of a selected Body.
        #       25(75/25V)/75H
        # or these sub-views could be within sys_viz?
        self._sys_viewbox = self.central_widget.add_view()
        self._sys_vizz = StarSystemView(sys_model=self._system_model, system_view=self._sys_viewbox)

        self.cameras = CameraSet()
        self._sys_viewbox.camera = self.cameras.curr_cam
        self._sys_viewbox.camera.set_range((-1e+09, 1e+09),
                                           (-1e+09, 1e+09),
                                           (-1e+09, 1e+09),
                                           )       # this initial range gets bulk of system
        self._sys_viewbox.camera.zoom_factor = 1.0
        self._sys_viewbox.camera.scale_factor = 14.5e+06

        self._system_model.t_warp = 9000
        self._model_timer = Timer(interval='auto',
                                  connect=self.on_mod_timer,
                                  iterations=-1
                                  )
        self._report_timer = Timer(interval=1,
                                   connect=self.on_rpt_timer,
                                   iterations=-1
                                   )
        self._system_model.assign_timer(self._model_timer)
        self.freeze()

        for k, v in self._sys_viewbox.camera.get_state().items():
            print(k, ":", v)

    def on_key_press(self, ev):
        try:
            if ev.key.name == "+":
                self._sys_viewbox.camera.scale_factor *= 1.1
                print("SCALE_FACTOR", self._sys_viewbox.camera.scale_factor)
            elif ev.key.name == "-":
                self._sys_viewbox.camera.scale_factor *= 0.9
                print("SCALE_FACTOR", self._sys_viewbox.camera.scale_factor)
            elif ev.key.name == "*":
                self._sys_viewbox.camera.fov *= 1.5
                print("CAM_FOV", self._sys_viewbox.camera.fov)
            elif ev.key.name == "/":
                self._sys_viewbox.camera.fov *= 0.75
                print("CAM_FOV", self._sys_viewbox.camera.fov)
            elif ev.key.name == "]":
                self.model.t_warp *= 1.1
                print("TIME_WARP:", self.model.t_warp)
            elif ev.key.name == "[":
                self.model.t_warp *= 0.9
                print("TIME_WARP:", self.model.t_warp)
            elif ev.key.name == "\\":
                self._system_model.cmd_timer()
            elif ev.key.name == "p":
                print("MESH_DATA[\"Sun\"]", self._sys_vizz.mesh_data["Sun"].save())
            elif ev.key.name == "'":
                new_aplha = (self._sys_viewbox.skymap.mesh.meshdata.color[3] + .1) % 1
                self._sys_viewbox.skymap.mesh.meshdata.color[3] = new_aplha

        except AttributeError:
            print("Key Error...")

    def on_mod_timer(self, event=None):
        self._system_model.update_epochs()
        self._sys_vizz.update_vizz()

    def on_rpt_timer(self, event=None):
        print("MeshData:\n", self._sys_vizz.planet_meshdata)

    def run(self):
        self.show()
        self._system_model.cmd_timer()
        app.run()

    # def stop(self):
    #     app.quit()
    @property
    def model(self):
        return self._system_model

    @property
    def view(self):
        return self._sys_viewbox

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
    my_simwin = MainSimCanvas(body_names=_body_include_set)
    my_simwin.run()


if __name__ == "__main__":

    main()
