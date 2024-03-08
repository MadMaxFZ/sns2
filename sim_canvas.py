# -*- coding: utf-8 -*-
# x
import logging
from vispy.app.timer import Timer
from vispy import app, scene
from vispy.color import Color
from starsys_data import sys_data
#rom starsys_model import StarSystemModel
from starsys_visual import StarSystemViewer
from camera_set import CameraSet

logging.basicConfig(filename="logs/mainsimwin.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class MainSimCanvas(scene.SceneCanvas):
    FIRST_RUN = True

    def __init__(self, system_model):
        super(MainSimCanvas, self).__init__(keys="interactive",
                                            size=(800, 600),
                                            show=False,
                                            bgcolor=Color("black"),
                                            title="SPACE NAVIGATION SIMULATOR, (c)2024 Max S. Whitten",
                                            )
        self.unfreeze()
        # if type(system_model) == StarSystemModel:
        #     self._system_model = system_model
        # else:
        #     exit("MainSimCanvas.__init__: BAD MODEL")
        # TODO: Set up a system view with a FlyCamera,
        #       a secondary box with a Body list along
        #       with a view of a selected Body.
        #       25(75/25V)/75H
        # or these sub-views could be within sys_viz?
        self._fpv_viewbox = self.central_widget.add_view()
        self._cam_set = CameraSet(canvas=self)
        self._fpv_viewbox.camera = self._cam_set.curr_cam
        self._sys_vizz = StarSystemViewer(sim_bods=self._system_model.simbodies,
                                          system_view=self._fpv_viewbox)
        self._fpv_viewbox.camera.set_range((-1e+09, 1e+09),
                                           (-1e+09, 1e+09),
                                           (-1e+09, 1e+09),
                                           )       # this initial range gets bulk of system
        self._fpv_viewbox.camera.zoom_factor = 1.0
        self._fpv_viewbox.camera.scale_factor = 14.5e+06

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

        for k, v in self._fpv_viewbox.camera.get_state().items():
            print(k, ":", v)

    def on_key_press(self, ev):
        try:
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
                self._system_model.cmd_timer()
            elif ev.key.name == "p":
                print("MESH_DATA[\"Sun\"]", self._sys_vizz.mesh_data["Sun"].save())
            elif ev.key.name == "'":
                new_aplha = (self._fpv_viewbox.skymap.mesh.meshdata.color[3] + .1) % 1
                self._fpv_viewbox.skymap.mesh.meshdata.color[3] = new_aplha

        except AttributeError:
            print("Key Error...")

    def on_mod_timer(self, event=None):
        self._system_model.update_epoch()
        self._sys_vizz.update_vizz()

    def on_rpt_timer(self, event=None):
        print("MeshData:\n", self._sys_vizz.planet_meshdata)

    def run(self):
        self.show()
        self._system_model.cmd_timer()
        app.run()

    def toggle_timer(self):
        self._system_model.cmd_timer()

    def quit(self):
        app.quit()

    @property
    def curr_cam(self):
        return self._cam_set.curr_cam

    @property
    def model(self):
        return self._system_model

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
    my_simwin = MainSimCanvas(body_names=_body_include_set)
    my_simwin.run()


if __name__ == "__main__":

    main()
