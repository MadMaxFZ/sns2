# -*- coding: utf-8 -*-

# import functiontrace
import numpy as np
import math
import vispy.visuals.transforms as tr
from vispy.util.transforms import *
from vispy.scene.visuals import Markers, Compound, Polygon
from vispy.color import Color
from viz_functs import get_tex_data, get_viz_data
from vispy import app, scene
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
        self.view.camera.scale_factor = 0.01
        self.view.camera.zoom_factor = 0.001
        self.star_sys = StarSystem(cam=self.view.camera)
        self.skymap = self.star_sys.skymap
        self.sys_viz = self.init_sysviz()
        self.freeze()
        self.skymap.parent = self.view.scene
        self.view.add(self.skymap)
        self.view.add(self.sys_viz)
        self.view.camera.set_range((-1e+09, 1e+09),
                                   (-1e+09, 1e+09),
                                   (-1e+09, 1e+09), )       # this initial range gets bulk of system

    def init_sysviz(self):
        frame = scene.visuals.XYZAxis(parent=self.view.scene)
        # frame.transform = tr.STTransform(scale=(1e+08, 1e+08, 1e+08))
        orb_vizz = Compound([Polygon(pos=sb.o_track,
                                     border_color=sb.base_color,
                                     triangulate=False)
                             for sb in self.star_sys.sb_list])
        viz = Compound([frame, self.star_sys.bods_viz, orb_vizz])
        viz.parent = self.view.scene

        return viz

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
