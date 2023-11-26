# -*- coding: utf-8 -*-

from planet_visual import *
from vispy.scene import visuals


class SystemVizual(visuals.Compound):
    """
    """
    def __init__(self, sim_bods=None):
        self._skymap = SkyMap(edge_color=(0, 0, 1, 0.4))
        self._init_state = 0
        if self._check_simbods(sbs=sim_bods):
            self._build_sys_viz(sbs=sim_bods)
        else:
            print("Must provide SimBody dictionary...")
            exit(1)
        self._body_marks = None
        self._body_marks_data = None
        self._planet_vizz = None
        self._planet_vizz_data = None
        self._track_polys = None
        self._track_polys_data = None


        super(SystemVizual, self).__init__([])

    @staticmethod
    def _check_simbods(sbs=None):
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

    def _build_sys_viz(self, sbs=None):
        if sbs is None:
            print("Must provide SimBody dictionary...")
        else:
            for sb_name, sb in sbs.items():


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

