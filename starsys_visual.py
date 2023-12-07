# -*- coding: utf-8 -*-

import math
import logging
import numpy as np
import vispy.visuals.transforms as tr
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import (create_visual_node,
                                 Markers, XYZAxis,
                                 Compound, Polygon)
from data_functs import vec_type
from body_visual import Planet
from skymap import SkyMap
from simbody import SimBody


MIN_SYMB_SIZE = 5
MAX_SYMB_SIZE = 20
ST = tr.STTransform
MT = tr.MatrixTransform
SUN_COLOR = [253 / 255, 184 / 255, 19 / 255]
DEF_MARKS_INIT = dict(scaling=False,
                      alpha=1,
                      antialias=1,
                      spherical=False,
                      light_color=SUN_COLOR,
                      light_position=(0.01, 0.01, 0.01),
                      light_ambient=0.3,
                      )
DEF_MARKS_DATA = dict(pos=None,
                      size=None,
                      edge_width=None,
                      edge_width_rel=None,
                      edge_color=None,
                      face_color=None,
                      symbol=None,
                      )


class StarSystemVisual(CompoundVisual):
    """
    """
    def __init__(self, sim_bods=None, system_view=None):
        if self._check_simbods(sbs=sim_bods):
            self._simbods       = sim_bods
            self._init_state    = 0
            self._mainview      = system_view
            self._cam           = self._mainview.camera
            self._cam_rel_pos   = np.zeros((len(self._simbods.keys()),), dtype=vec_type)
            self._cam_rel_vel   = None  # there is no readily available velocity for camera
            self._skymap        = SkyMap(edge_color=(0, 0, 1, 0.4))
            self._bods_pos      = [sb.pos2primary() for sb in self._simbods.values()]
            self._sb_symbols    = [sb.body_symbol for sb in self._simbods.values()]
            self._symbol_sizes  = []
            self._sb_planets    = []       # a list of Planet visuals
            self._sb_tracks     = []       # a list of Polygon visuals
            self._sb_markers    = Markers(parent=self._skymap, **DEF_MARKS_INIT)  # a single instance of Markers
            # self._system_viz    = self._setup_sysviz(sbs=sim_bods)
            super(StarSystemVisual, self).__init__(subvisuals=self._setup_sysviz(sbs=sim_bods))
        else:
            print("Must provide a dictionary of SimBody objects...")
            exit(1)

    def _setup_sysviz(self, sbs=None):
        # TODO: generate/assign visuals here to build SystemVizual instance
        if sbs is not None:
            self._frame_viz = XYZAxis(parent=self._skymap)  # set parent in MainSimWindow ???
            self._frame_viz.transform = ST(scale=[1e+08, 1e+08, 1e+08])
            self._sb_markers.parent = self._skymap
            self._sb_symbols = [sb.body_symbol for sb in sbs.values()]
            for sb_name, sb in sbs.items():
                self._sb_planets.append(Planet(body_ref=sb.body,
                                               color=sb.base_color,
                                               edge_color=sb.base_color,
                                               texture=sb.texture,
                                               parent=self._skymap,
                                               visible=False,
                                               ))
                if sb.sb_parent is not None:
                    self._sb_tracks.append(Polygon(pos=sb.o_track + sbs[sb.sb_parent.name].pos,
                                                   border_color=sb.base_color +
                                                   np.array([0, 0, 0, sb.track_alpha]),
                                                   triangulate=False,
                                                   parent=self._skymap,
                                                   ))

            subvisuals = [self._skymap,
                          self._frame_viz,
                          self._sb_markers,
                          Compound(self._sb_tracks),
                          Compound(self._sb_planets),
                          ]
            return subvisuals
        else:
            print("Must provide SimBody dictionary...")

    def update_sysviz(self):
        # collect positions of the bodies into an array
        _bods_pos = [sb.pos2primary() for sb in self._simbods.values()]
        # self._sb_tracks[3].parent = self._sb_planets[3]  # move moon orbit to Earth pos
        self._bods_pos = np.array(_bods_pos)

        # collect the body positions relative to the camera location
        self._cam_rel_pos = [sb.rel2pos(pos=self._mainview.camera.center)['rel_pos']
                             for sb in self._simbods.values()]
        self._symbol_sizes = self.get_symb_sizes()        # update symbol sizes based upon FOV of body
        self._sb_markers.set_data(pos=self._bods_pos,
                                  face_color=np.array([sb.base_color + np.array([0, 0, 0, sb.track_alpha])
                                                       for sb in self._simbods.values()]),
                                  edge_color=[1, 0, 0, .6],
                                  size=self._symbol_sizes,
                                  symbol=self._sb_symbols,
                                  )
        logging.info("\nSYMBOL SIZES :\t%s", self._symbol_sizes)
        logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self._cam_rel_pos])

    def get_symb_sizes(self):
        # TODO: Rework this method to have only one loop!
        body_fovs = []
        for sb in self._simbods.values():
            body_fovs.append(sb.rel2pos(pos=self._cam.center)['fov'])

        raw_diams = [math.ceil(self._mainview.size[0] * b_fov / self._cam.fov) for b_fov in body_fovs]
        pix_diams = []
        for rd in raw_diams:
            if rd < MIN_SYMB_SIZE:
                pix_diams.append(MIN_SYMB_SIZE)
            elif rd < MAX_SYMB_SIZE:
                pix_diams.append(rd)
            else:
                pix_diams.append(0)

        return np.array(pix_diams)

    @staticmethod
    def _check_simbods(sbs=None):
        """ Make sure that the simbods argument actually consists of
            a dictionary of SimBody objects.
        """
        check = True
        if sbs is None:
            print("Must provide something... FAILED")
            check = False
        elif type(sbs) is not dict:
            print("Must provide SimBody dictionary... FAILED")
            check = False
        else:
            for key, val in sbs.items():
                if type(val) is not SimBody:
                    print(key, "is NOT a SimBody... FAILED.")
                    check = False

        return check

    @property
    def skymap(self):
        if self._skymap is None:
            print("No SkyMap defined...")
        else:
            return self._skymap

    @skymap.setter
    def skymap(self, new_skymap=None):
        if type(new_skymap) is SkyMap:
            self._skymap = new_skymap
        else:
            print("Must provide a SkyMap object...")


StarSystem = create_visual_node(StarSystemVisual)


def main():
    print("MAIN FUNCTION...")


if __name__ == "__main__":
    main()