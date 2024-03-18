# -*- coding: utf-8 -*-
# x
import sys
import math
import logging
import numpy as np
import vispy.visuals.transforms as trx
from vispy.color import *
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import (create_visual_node,
                                 Markers, XYZAxis,
                                 Compound, Polygon)
from starsys_data import vec_type, _dist_unit
from sysbody_visual import Planet
from sys_skymap import SkyMap
from sysbody_model import SimBody
from camera_set import CameraSet

# these quantities can be served from DATASTORE class
MIN_SYMB_SIZE = 5
MAX_SYMB_SIZE = 30
ST = trx.STTransform
MT = trx.MatrixTransform
SUN_COLOR = tuple(np.array([253, 184, 19]) / 256)
DEF_MARKS_INIT = dict(scaling=False,
                      alpha=1,
                      antialias=1,
                      spherical=True,
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
_pl_e_alpha = 0.2
_pm_e_alpha = 0.6
_cm_e_alpha = 0.6


class StarSystemVisuals:
    """
    """
    def __init__(self, body_names):
        """
        Constructs a collection of Visuals that represent entities in the system model,
        updating periodically based upon the quantities propagating in the model.
        TODO:   Remove the model from this module. The data required here must now
                be obtained using Signals to the QThread that the model will be running within.
        Parameters
        ----------
        body_names   :  TODO: Only require the SimBody name... as an argument to generate_bodyvizz() method
        scene :   TODO: minimize the use of this. Only need scene for parents...?
        """
        self._IS_INITIALIZED = False
        self._body_names   = body_names
        self._body_count   = len(body_names)
        self._bods_pos     = None
        self._scene        = None
        self._skymap       = None
        self._planets      = {}      # a dict of Planet visuals
        self._tracks       = {}       # a dict of Polygon visuals
        self._symbols      = []
        self._symbol_sizes = []
        self._curr_camera  = None
        self._pos_rel2cam  = None
        self._frame_viz    = None
        self._plnt_markers = None
        self._cntr_markers = None
        self._subvizz      = None
        self._agg_cache    = None

    '''--------------------------- END StarSystemVisuals.__init__() -----------------------------------------'''

    def generate_visuals(self, view,  agg_data):
        """
        Parameters
        ----------
        view        :  View object
                            The view in which the visuals are to be rendered.
        agg_data    :  dict
                            The data to be used for generating the visuals.

        Returns
        -------
        None            : No return value, however all of the visuals for the sim rendering are
                          created here, collected together and then added to the scene.
        """
        self._agg_cache = agg_data
        self._scene = view.scene
        self._curr_camera = view.camera
        self._skymap = SkyMap(parent=self._scene)
        self._frame_viz = XYZAxis(parent=self._scene)  # set parent in MainSimWindow ???
        self._frame_viz.transform = MT()
        self._frame_viz.transform.scale((1e+08, 1e+08, 1e+08))

        for name in self._body_names:
            self._generate_planet_viz(body_name=name)
            if name != self._agg_cache['primary_name']:
                self._generate_trajct_viz(body_name=name)

        self._generate_marker_viz()
        self._subvizz = dict(sk_map=self._skymap,
                             r_fram=self._frame_viz,
                             p_mrks=self._plnt_markers,
                             c_mrks=self._cntr_markers,
                             tracks=self._tracks,
                             surfcs=self._planets,)
        self._upload2view()

    def _generate_planet_viz(self, body_name):
        """ Generate Planet visual object for each SimBody
        """
        plnt = Planet(body_name=body_name,
                      rows=18,
                      color=Color((1, 1, 1, self._agg_cache['b_alpha'][body_name])),
                      edge_color=(0, 0, 0, _pm_e_alpha),  # sb.base_color,
                      parent=self._scene,
                      visible=True,
                      method='oblate',
                      )
        plnt.transform = trx.MatrixTransform()  # np.eye(4, 4, dtype=np.float64)
        self._planets.update({body_name: plnt})

    def _generate_trajct_viz(self, body_name):
        """ Generate Polygon visual object for each SimBody orbit
        """
        t_color = self._agg_cache['color'][body_name]
        t_color.alpha = self._agg_cache['t_alpha'][body_name]
        poly = Polygon(pos=self._agg_cache['track'][body_name],
                       border_color=t_color,
                       triangulate=False,
                       parent=self._scene,
                       )
        poly.transform = trx.MatrixTransform()  # np.eye(4, 4, dtype=np.float64)
        self._tracks.update({body_name: poly})

    def _generate_marker_viz(self):
        # put init of markers into a method
        self._symbols = [pl.mark for pl in self._planets.values()]
        self._plnt_markers = Markers(parent=self._scene, **DEF_MARKS_INIT)  # a single instance of Markers
        self._cntr_markers = Markers(parent=self._scene,
                                     symbol=['+' for _ in range(self._body_count)],
                                     size=[(MIN_SYMB_SIZE - 2) for _ in range(self._body_count)],
                                     **DEF_MARKS_INIT)  # another instance of Markers
        # self._plnt_markers.parent = self._mainview.scene
        self._cntr_markers.set_data(symbol=['+' for _ in range(self._body_count)])

    def _upload2view(self):
        for k, v in self._subvizz.items():
            if "_" in k:
                print(k)
                self._scene.parent.add(v)
            else:
                [self._scene.parent.add(t) for t in v.values()]

    def update_vizz(self):
        """
        TODO:   Refactor to remove references to 'self._simbods' and look to implement multiprocessing.
        Returns
        -------
        Has no return value, but updates the transforms for the Planet and Polygon visuals,
        also, updates the positions and sizes of the Markers icons.
        """
        self._symbol_sizes = self.get_symb_sizes()  # update symbol sizes based upon FOV of body
        _p_face_colors = []
        _c_face_colors = []
        _edge_colors = []

        for sb_name in self._body_names:                                                    # <--
            x_ax = self._agg_cache['axes'][sb_name][0]
            y_ax = self._agg_cache['axes'][sb_name][1]
            z_ax = self._agg_cache['axes'][sb_name][2]
            RA   = self._agg_cache['rot'][sb_name][0]
            DEC  = self._agg_cache['rot'][sb_name][1]
            W    = self._agg_cache['rot'][sb_name][2]
            pos  = self._agg_cache['pos'][sb_name]

            if self._planets[sb_name].visible:
                xform = self._planets[sb_name].transform
                xform.reset()
                xform.rotate(W * np.pi / 180, x_ax)
                xform.rotate(DEC * np.pi / 180, y_ax)
                xform.rotate(RA * np.pi / 180, z_ax)
                xform.translate(pos)
                self._planets[sb_name].transform = xform

            if sb_name != self._agg_cache['primary_name']:
                self._tracks[sb_name].transform.reset()
                self._tracks[sb_name].transform.translate(pos)

            self._bods_pos.append(pos)
            _pf_clr = self._agg_cache['color'][sb_name].alpha = self._agg_cache['b_alpha'][sb_name]
            _cf_clr = _pf_clr.alpha = 0
            _p_face_colors.append(_pf_clr)
            _c_face_colors.append(_cf_clr)

            self._pos_rel2cam = [(self._curr_camera.center - _p) * _dist_unit
                                 for _p in self._bods_pos]                                          # <--

        self._plnt_markers.set_data(pos=self._bods_pos,
                                    face_color=_p_face_colors,
                                    edge_color=[1, 0, 0, _pm_e_alpha],
                                    size=self._symbol_sizes,
                                    symbol=self._symbols,
                                    )
        self._cntr_markers.set_data(pos=self._bods_pos,
                                    face_color=_c_face_colors,
                                    edge_color=[0, 1, 0, _cm_e_alpha],
                                    size=MIN_SYMB_SIZE,
                                    symbol=['diamond' for _ in range(self._body_count)],                  # <--
                                    )
        logging.info("\nSYMBOL SIZES :\t%s", self._symbol_sizes)
        logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self._pos_rel2cam])

    def get_symb_sizes(self, from_cam=None):
        """
        Calculates the size in pixels at which a SimBody will appear in the view from
        the perspective of a specified camera.
        TODO:   Refactor to remove references to 'self._simbods' and look to implement multiprocessing,
                decide how to handle the self._cam.fov reference as well.
        Parameters
        ----------
        from_cam :  A Camera object from which the apparent sizes are measured from

        Returns
        -------
        An np.array containing a pixel width for each SimBody

        TODO: instead of only symbol sizes, include face and edge color, etc.
                  Probably rename this method to 'get_mark_data(self, from_cam=None)'
        """
        if not from_cam:
            from_cam = self._curr_camera

        pix_diams = []
        _bods_pos = []
        for sb_name in self._body_names:                                                       # <--
            _bods_pos = self._agg_cache['pos'][sb_name]
            # if sb.type not in ['star', 'planet']:
            #     self._bods_pos[-1] += sb.sb_parent.pos

            body_fov = self._agg_cache['rel2cam'][sb_name]['fov']
            pix_diam = 0
            raw_diam = math.ceil(self._scene.parent.size[0] * body_fov / self._cam.fov)                # <--

            if raw_diam < MIN_SYMB_SIZE:
                pix_diam = MIN_SYMB_SIZE
            elif raw_diam < MAX_SYMB_SIZE:
                pix_diam = raw_diam
            elif raw_diam >= MAX_SYMB_SIZE:
                pix_diam = 0
                self._planets[sb_name].visible = True
            else:
                self._planets[sb_name].visible = False

            pix_diams.append(pix_diam)

        return np.array(pix_diams)

    @staticmethod
    def _check_simbods(simbods=None):
        """ Make sure that the simbods argument actually consists of
            a dictionary of SimBody objects.
        """
        check = True
        if simbods is None:
            print("Must provide a SimBody dict... FAILED")
            check = False
        elif type(simbods) is not dict:
            print("must provide a dictionary of SimBody objects... FAILED")
            check = False
        else:
            for key, val in simbods.items():
                if type(val) is not SimBody:
                    print(key, "is NOT a SimBody... FAILED.")
                    check = False

        return check

    @property
    def bods_pos(self):
        return self._bods_pos.values()

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

    @property
    def mesh_data(self, name=None):
        if name is None:
            res = {}
            return [res.update({k: v.mesh_data}) for k, v in self._planets.items()]
        else:
            return self._planets[name].mesh_data


def main():
    print("MAIN FUNCTION...")


if __name__ == "__main__":
    main()
