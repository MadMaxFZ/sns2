# -*- coding: utf-8 -*-

# import functiontrace
# import numpy as np
# import math
# from vispy.util.transforms import *
# from viz_functs import get_tex_data, get_viz_data
from vispy import app, scene
from vispy.color import Color
# from data_functs import *
from starsystem import *

logging.basicConfig(filename="logs/mainsimwin.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class MainSimWindow(scene.SceneCanvas):
    def __init__(self):
        super(MainSimWindow, self).__init__(keys="interactive",
                                            size=(1024, 512),
                                            show=False,
                                            bgcolor=Color("black"),
                                            )
        self.unfreeze()
        self._sys_view = self.central_widget.add_view()
        self._sys_view.camera = scene.cameras.FlyCamera(fov=60)
        self._sys_view.camera.scale_factor = 1.0
        self._sys_view.camera.zoom_factor = 1.0
        self._star_sys = StarSystem(sys_data=setup_datastore(), view=self._sys_view)
        self._system_viz = self._star_sys.sys_viz
        self.freeze()
        self._sys_view.add(self._system_viz)
        self._sys_view.camera.set_range((-1e+09, 1e+09),
                                        (-1e+09, 1e+09),
                                        (-1e+09, 1e+09), )       # this initial range gets bulk of system
        if __name__ != "__main__":
            self.run()

    def on_key_press(self, ev):
        try:
            if ev.key.name == "+":
                self._sys_view.camera.scale_factor *= 1.1
                print("SCALE_FACTOR", self._sys_view.camera.scale_factor)
            elif ev.key.name == "-":
                self._sys_view.camera.scale_factor *= 0.9
                print("SCALE_FACTOR", self._sys_view.camera.scale_factor)
            # elif ev.key.name == "*":
            #     self._sys_view.camera.zoom_factor *= 1.1
            #     print("ZOOM_FACTOR", self._sys_view.camera.zoom_factor)
            # elif ev.key.name == "/":
            #     self._sys_view.camera.zoom_factor *= 0.9
            #     print("ZOOM_FACTOR", self._sys_view.camera.zoom_factor)
            elif ev.key.name == "*":
                self._star_sys.t_warp *= 1.1
                print("TIME_WARP:", self._star_sys.t_warp)
            elif ev.key.name == "/":
                self._star_sys.t_warp *= 0.9
                print("TIME_WARP:", self._star_sys.t_warp)

        except AttributeError:
            print("Key Error...")

    def run(self):
        self.show()
        self._star_sys.run()
        app.run()

    def stop(self):
        app.quit()


def main():
    my_simwin = MainSimWindow()
    my_simwin.run()


if __name__ == "__main__":

    main()
