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
        self.star_sys = StarSystem()
        self.view = self.central_widget.add_view()
        self.view.camera = scene.cameras.FlyCamera(fov=30)
        self.view.camera.scale_factor = 0.01
        self.view.camera.zoom_factor = 0.001
        self.b_states = None
        self.b_symbs = ['star', 'o', 'o', 'o',
                        '+',
                        'o', 'o', 'o', 'o', 'o', 'o', ]     # could base this on body type
        self.bods_viz = None
        self.sys_viz = None
        self.skymap = None          # need to fix this
        self.simbods = None         # need to fix this
        self.b_names = None         # need to fix this
        self.freeze()

        self.sys_viz = self.init_sysviz()
        self.skymap.parent = self.view.scene
        self.view.add(self.sys_viz)
        self.view.add(self.skymap)
        self.view.camera.set_range((-1e+09, 1e+09),
                                   (-1e+09, 1e+09),
                                   (-1e+09, 1e+09), )       # this initial range gets bulk of system

    def init_sysviz(self):
        frame = scene.visuals.XYZAxis(parent=self.view.scene)
        # frame.transform = tr.STTransform(scale=(1e+08, 1e+08, 1e+08))
        self.bods_viz = Markers(edge_color=(0, 1, 0, 1))
        orb_vizz = Compound([Polygon(pos=self.simbods[name].o_track,
                                     border_color=self.simbods[name].base_color,
                                     triangulate=False)
                             for name in self.b_names])
        viz = Compound([frame, self.bods_viz, orb_vizz])
        viz.parent = self.view.scene

        return viz

    def update_bodies(self, event=None):
        self.b_states = []
        self.b_states.extend([sb.state[0] for sb in self.sb_set])
        self.b_states[4] += self.simbods['Earth'].state[0, :]
        self.b_states = np.array(self.b_states)
        self.bods_viz.set_data(pos=self.b_states,
                               face_color=self.dat_store["COLOR_SET"],
                               edge_color=(0, 1, 0, .2),
                               symbol=self.b_symbs,
                               )

    def run(self):
        # self.wclock.start()
        self.show()
        app.run()

    def stop(self):
        app.quit()


def main():
    my_can = MainSimWindow()
    my_can.run()


if __name__ == "__main__":

    main()
