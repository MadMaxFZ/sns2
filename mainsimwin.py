# -*- coding: utf-8 -*-

# import functiontrace
import numpy as np
import math
from vispy.util.transforms import *
from viz_functs import get_tex_data, get_viz_data
from vispy import app, scene
from vispy.color import Color
from data_functs import *
from starsystem import *

logging.basicConfig(filename="logs/mainsimwin.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class MainSimWindow(scene.SceneCanvas):
    def __init__(self):
        super(MainSimWindow, self).__init__(keys="interactive",
                                            size=(1024, 768),
                                            show=False,
                                            bgcolor=Color("black"),
                                            )
        self.unfreeze()
        self.view = self.central_widget.add_view()
        self.view.camera = scene.cameras.FlyCamera(fov=30)
        self.view.camera.scale_factor = 0.000001
        self.view.camera.zoom_factor = 0.00001
        self.star_sys = StarSystem(view=self.view)
        self.skymap = self.star_sys.skymap
        self.sys_viz = self.star_sys.init_sysviz()
        self.freeze()
        self.skymap.parent = self.view.scene
        self.view.add(self.skymap)
        self.view.add(self.sys_viz)
        self.view.camera.set_range((-1e+09, 1e+09),
                                   (-1e+09, 1e+09),
                                   (-1e+09, 1e+09), )       # this initial range gets bulk of system

    def run(self):
        self.show()
        self.star_sys.run()
        app.run()

    def stop(self):
        app.quit()


def main():
    my_simwin = MainSimWindow()
    my_simwin.run()


if __name__ == "__main__":

    main()
