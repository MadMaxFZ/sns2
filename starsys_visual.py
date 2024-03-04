# -*- coding: utf-8 -*-
# x
import sys
import math
import logging
import numpy as np
import vispy.visuals.transforms as trx
from vispy.visuals import CompoundVisual
from vispy.scene.visuals import (create_visual_node,
                                 Markers, XYZAxis,
                                 Compound, Polygon)
from starsys_data import vec_type
from sysbody_visual import Planet
from sys_skymap import SkyMap
from sysbody_model import SimBody

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


class StarSystemView:
    """
    """
    def __init__(self, sys_model=None, system_view=None):
        """
        Constructs a collection of Visuals that represent entities in the system model,
        updating periodically based upon the quantities propagating in the model.
        TODO:   Remove the model from this module. The data required here must now
            be obtained using Signals to the QThread that the model will be running within.
        Parameters
        ----------
        sys_model :  TODO: Only require the SimBody object...
        system_view :   TODO: minimize the use of this. Only need scene for parents...?
        """
        if self._check_simbods(model=sys_model):
            self._simbods       = sys_model.simbodies
            body_count          = sys_model.body_count
            body_names = self._simbods.keys()
            self._init_state    = 0
            self._mainview      = system_view
            self._cam           = self._mainview.camera
            self._cam_rel_pos   = np.zeros((body_count,), dtype=vec_type)
            self._cam_rel_vel   = None  # there is no readily available velocity for camera
            self._skymap        = SkyMap( )
            self._bods_pos      = {}
            [self._bods_pos.update({name: sb.pos2primary}) for name, sb in self._simbods.items()]
            self._symbol_sizes  = []
            self._planets    = {}       # a dict of Planet visuals
            self._tracks     = {}       # a dict of Polygon visuals
            self._frame_viz = XYZAxis(parent=self._mainview.scene)  # set parent in MainSimWindow ???
            self._frame_viz.transform = MT()
            self._frame_viz.transform.scale((1e+08, 1e+08, 1e+08))
            ''' Generate Planet visual object for each SimBody
            '''
            [self._generate_vizz4body(name) for name in body_names]
            self._symbols = [pl.mark for pl in self._planets.values()]
            self._plnt_markers = Markers(parent=self._mainview.scene, **DEF_MARKS_INIT)  # a single instance of Markers
            self._cntr_markers = Markers(parent=self._mainview.scene,
                                         symbol='+',
                                         size=[(MIN_SYMB_SIZE - 2) for n in range(body_count)],
                                         **DEF_MARKS_INIT)  # another instance of Markers
            # self._plnt_markers.parent = self._mainview.scene
            self._cntr_markers.set_data(symbol=['+' for n in range(body_count)])

            self._subvizz = dict(sk_map=self._skymap,
                                 r_fram=self._frame_viz,
                                 p_mrks=self._plnt_markers,
                                 c_mrks=self._cntr_markers,
                                 tracks=self._tracks,
                                 surfcs=self._planets,
                                 )
            self.load_vizz()
            # self.update_vizz()
        else:
            print("Must provide a dictionary of SimBody objects...")
            sys.exit(1)

    def _generate_vizz4body(self, name):
        plnt = Planet(body_name=name,
                      rows=18,
                      color=(1, 1, 1, 1),
                      edge_color=(0, 0, 0, .2),       # sb.base_color,
                      parent=self._mainview.scene,
                      visible=True,
                      method='oblate',
                      )
        plnt.transform = trx.MatrixTransform()   # np.eye(4, 4, dtype=np.float64)
        self._planets.update({name: plnt})
        ''' Generate Polygon visual object for each SimBody orbit
        '''
        if not self._simbods[name].is_primary:
            # print(f"Body: %s / Track: %s / Parent.pos: %s", sb.name, sb.track, sb.sb_parent.pos)
            poly = Polygon(pos=self._simbods[name].track,  # + sb.sb_parent.pos,
                           border_color=np.array(list(plnt.base_color) + [0, ]) +
                                        np.array([0, 0, 0, plnt.track_alpha]),
                           triangulate=False,
                           parent=self._mainview.scene,
                           )
            poly.transform = trx.MatrixTransform()   # np.eye(4, 4, dtype=np.float64)
            self._tracks.update({name: poly})

    def load_vizz(self):
        for k, v in self._subvizz.items():
            if "_" in k:
                print(k)
                self._mainview.add(v)
            else:
                [self._mainview.add(t) for t in v.values()]

        pass

    def update_vizz(self):
        self._symbol_sizes = self.get_symb_sizes()  # update symbol sizes based upon FOV of body
        self._bods_pos = {}
        for sb_name, sb in self._simbods.items():
            # print(sb.pos2primary - sb.pos)
            sb_pos = np.zeros((4,))
            # here the data is acquired from the SimBody:
            sb_pos[0:3] = sb.pos2primary

            self._bods_pos.update({sb_name: sb_pos[0:3]})
            if self._planets[sb_name].visible:
                xform = self._planets[sb_name].transform
                xform.reset()
                xform.rotate(sb.W * np.pi / 180, sb.z_ax)
                xform.rotate(sb.DEC * np.pi / 180, sb.y_ax)
                xform.rotate(sb.RA * np.pi / 180, sb.z_ax)
                xform.translate(sb_pos)
                self._planets[sb_name].transform = xform

            if sb.sb_parent is not None:
                self._tracks[sb_name].transform.reset()
                self._tracks[sb_name].transform.translate(sb.sb_parent.pos2primary)

        # collect the body positions relative to the camera location
        self._cam_rel_pos = [sb.rel2pos(pos=self._mainview.camera.center * sb.dist_unit)['rel_pos']
                             for sb in self._simbods.values()]

        self._plnt_markers.set_data(pos=self._bods_pos.values(),
                                    face_color=[np.array(list(sb.base_color) + [0,]) +
                                                np.array([0, 0, 0, sb.track_alpha])
                                                for sb in self._simbods.values()
                                                ],
                                    edge_color=[1, 0, 0, .6],
                                    size=self._symbol_sizes,
                                    symbol=self._symbols,
                                    )
        self._cntr_markers.set_data(pos=self._bods_pos.values(),
                                    edge_color=[0, 1, 0, .6],
                                    size=MIN_SYMB_SIZE,
                                    symbol=['diamond' for sb in self._simbods.values()],
                                    )
        logging.info("\nSYMBOL SIZES :\t%s", self._symbol_sizes)
        logging.info("\nCAM_REL_DIST :\n%s", [np.linalg.norm(rel_pos) for rel_pos in self._cam_rel_pos])

    def get_symb_sizes(self, from_cam=None):
        """
        Calculates the size in pixels at which a SimBody will appear in the view from
        the perspective of a specified camera.
        TODO:   Check the math in here since the marker symbols seem too big.
                Maybe the perspective transform isn't being figured in properly?
        Parameters
        ----------
        from_cam :  A Camera object from which the apparent sizes are measured from

        Returns
        -------
        An np.array containing a pixel width for each SimBody
        """
        """ TODO: instead of only symbol sizes, include face and edge color, etc.
                  Probably rename this method to 'get_mark_data(self, from_cam=None)'
        """
        if from_cam is None:
            from_cam = self._cam

        pix_diams = []
        _bods_pos = []
        for sb_name, sb in self._simbods.items():
            _bods_pos.append(sb.pos2primary)
            # if sb.type not in ['star', 'planet']:
            #     self._bods_pos[-1] += sb.sb_parent.pos

            body_fov = sb.rel2pos(pos=from_cam.center * sb.dist_unit)['fov']
            pix_diam = 0
            raw_diam = math.ceil(self._mainview.size[0] * body_fov / self._cam.fov)

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
    def _check_simbods(model=None):
        """ Make sure that the simbods argument actually consists of
            a dictionary of SimBody objects.
        """
        check = True
        if model is None:
            print("Must provide a model... FAILED")
            check = False
        elif type(model.simbodies) is not dict:
            print("Model must provide a SimBody dictionary... FAILED")
            check = False
        else:
            for key, val in model.simbodies.items():
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