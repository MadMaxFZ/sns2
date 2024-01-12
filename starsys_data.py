# -*- coding: utf-8 -*-

import os
import logging
from astropy.time import Time
from poliastro.constants import J2000_TDB
from poliastro.bodies import *
from poliastro.frames.fixed import *
from poliastro.frames.fixed import MoonFixed as LunaFixed
from poliastro.core.fixed import *
from viz_functs import get_tex_data

logging.basicConfig(filename="logs/sns_defs.log",
                    level=logging.INFO,
                    format="%(funcName)s:\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )
vec_type = type(np.zeros((3,), dtype=np.float64))


def earth_rot_elements_at_epoch(T=None, d=None):
    """"""
    _T = T
    return 0, 90 - 23.5, (d - math.floor(d)) * 360.0


def t_since_ref(epoch=None, ref=J2000_TDB):
    """"""
    if epoch is None:
        epoch = Time.now()

    t_since = epoch - ref
    # calculate dt of epoch and J2000
    rot_T = (t_since / 36525.0).value  # dt in centuries
    rot_d = t_since.to(u.day).value  # dt in days
    return rot_T, rot_d


def toTD(epoch=None):
    d = (epoch - J2000_TDB).jd
    T = d / 36525
    return dict(T=T, d=d)


class SystemDataStore:
    def __init__(self):
        """
        """
        DEF_EPOCH    = J2000_TDB  # default epoch
        SIM_PARAMS   = dict(sys_name="Sol",
                            def_epoch=DEF_EPOCH,
                            dist_unit=u.km,
                            periods=365,
                            spacing=24 * 60 * 60 * u.s,
                            n_samples=365,
                            fps=60,
                            )
        _tex_path      = "C:\\_Projects\\sns2\\resources\\textures\\"  # directory of texture image files
        _def_tex_fname = "2k_ymakemake_fictional.png"
        _tex_fnames    = []  # list of texture filenames (will be sorted)
        _tex_dat_set   = {}  # dist of body name and the texture data associated with it
        _body_params   = {}  # dict of body name and the static parameters of each
        _body_count    = 0   # number of available bodies
        _type_count    = {}  # dict of body types and the count of each typE
        _viz_assign    = {}  # dict of visual names to use for each body
        _body_set: list[Body]      = [Sun,      # all built-ins from poliastro
                                      Mercury,
                                      Venus,
                                      Earth,
                                      Moon,
                                      Mars,
                                      Jupiter,
                                      Saturn,
                                      Uranus,
                                      Neptune,
                                      Pluto,
                                      # TODO: Find textures and rotational elements for the outer system moons,
                                      #       otherwise apply a default condition
                                      # Phobos,
                                      # Deimos,
                                      # Europa,
                                      # Ganymede,
                                      # Enceladus,
                                      # Titan,
                                      # Titania,
                                      # Triton,
                                      # Charon,
                                      ]
        self._body_names = [bod.name for bod in _body_set]
        # orbital periods of bodies
        _o_per_set = [11.86 * u.year,
                      87.97 * u.d,
                      224.70 * u.d,
                      365.26 * u.d,
                      27.3 * u.d,
                      686.98 * u.d,
                      11.86 * u.year,
                      29.46 * u.year,
                      84.01 * u.year,
                      164.79 * u.year,
                      248 * u.year,
                      ]
        # reference frame fixed to planet surfaces
        _frame_set = [SunFixed,
                      MercuryFixed,
                      VenusFixed,
                      ITRS,
                      LunaFixed,
                      MarsFixed,
                      JupiterFixed,
                      SaturnFixed,
                      UranusFixed,
                      NeptuneFixed,
                      None,
                      ]
        # rotational elements as function of time
        _rot_set = [sun_rot_elements_at_epoch,
                    mercury_rot_elements_at_epoch,
                    venus_rot_elements_at_epoch,
                    earth_rot_elements_at_epoch,
                    moon_rot_elements_at_epoch,
                    mars_rot_elements_at_epoch,
                    jupiter_rot_elements_at_epoch,
                    saturn_rot_elements_at_epoch,
                    uranus_rot_elements_at_epoch,
                    neptune_rot_elements_at_epoch,
                    moon_rot_elements_at_epoch,
                    ]
        # body color values in RGBA (0...255)
        _color_RGB = [[253, 184, 19],  # base color for each body
                      [26, 26, 26],
                      [230, 230, 230],
                      [47, 106, 105],
                      [50, 50, 50],
                      [153, 61, 0],
                      [176, 127, 53],
                      [176, 143, 54],
                      [95, 128, 170],
                      [54, 104, 150],
                      [255, 255, 255],
                      ]
        _colorset_rgb = np.array(_color_RGB) / 256

        # types of bodies in simulation
        _body_types = ("star",
                       "planet",
                       "moon",
                       "ship",
                       )
        # Markers symbol to be used for each body type
        _body_tmark = ('star',
                       'o',
                       'diamond',
                       'triangle',
                       )
        # indices of body type for each body
        # TODO: Discover primary body and hierarchy tree instead of this

        _type_set = (0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, )

        # default visual elements to use on which bodies (not used)
        _viz_keys = ("reticle", "nametag", "refframe", "ruler",
                     "surface", "oscorbit", "radvec", "velvec", )
        _com_viz = [_viz_keys[1], _viz_keys[2], _viz_keys[4]]
        _xtr_viz = [_viz_keys[5], _viz_keys[6], _viz_keys[7]]
        _xtr_viz.extend(_com_viz)
        [_viz_assign.update({name: _xtr_viz}) for name in self._body_names]
        _viz_assign['Sun'] = _com_viz

        # get listing of texture filenames
        _tex_dirlist = os.listdir(_tex_path)
        for i in _tex_dirlist:
            if "png" in i:
                _tex_fnames.append(i)       # add PNG type files to list
        # _tex_fnames = _tex_fnames.sort()  # it doesn't like this sort()
        _tex_fnames = tuple(_tex_fnames)    # the tuple locks in the order of sorted elements
        # indices of texture filenames for each body
        _tex_idx = (0, 1, 3, 10, 17, 11, 12, 13, 15, 16, 17,
                    # 21, 21, 21, 21, 21, 21, 21, 21, 21,
                    )

        for idx in range(len(self._body_names)):  # idx = [0..,len(_body_names)-1]
            _bod_name = self._body_names[idx]
            _body = _body_set[idx]
            _bod_prnt = _body.parent

            logging.debug(">LOADING STATIC DATA for " + str(_bod_name))

            try:
                _tex_fname = _tex_path + _tex_fnames[_tex_idx[idx]]  # get path of indexed filename
            except:
                _tex_fname = _tex_path + _def_tex_fname
            _tex_dat_set.update({_bod_name: get_tex_data(fname=_tex_fname)})  # add texture data to active dict
            logging.debug("_tex_dat_set[" + str(idx) + "] = " + str(_tex_fname))
            if _body.parent is None:
                R = _body.R
                Rm = Rp = R
            else:
                R = _body.R
                Rm = _body.R_mean
                Rp = _body.R_polar

            if _body.parent is None:
                _par_name = None
            else:
                _par_name = _body.parent.name

            # a dict of ALL body data EXCEPT the viz_dict{}
            _body_data = dict(body_name=_body.name,  # build the _body_params dict
                              body_obj=_body,
                              parent_name=_par_name,
                              r_set=(R, Rm, Rp),
                              fname_idx=_tex_idx[idx],
                              fixed_frame=_frame_set[idx],
                              rot_func=_rot_set[idx],
                              o_period=_o_per_set[idx].to(u.s),
                              body_type=_body_types[_type_set[idx]],

                              tex_fname=_tex_fnames[_tex_idx[idx]],
                              tex_data=_tex_dat_set[_bod_name],  # _tex_dat_set[idx],
                              viz_names=_viz_assign[_bod_name],
                              body_color=_colorset_rgb[idx],
                              body_mark=_body_tmark[_type_set[idx]],
                              )
            _body_params.update({_bod_name: _body_data})

            if _body_data["body_type"] not in _type_count.keys():  # identify types of bodies
                _type_count[_body_data["body_type"]] = 0
            _type_count[_body_types[_type_set[idx]]] += 1  # count members of each type
            idx += 1
            _body_count += 1

        _check_sets = [
            len(_body_set),
            len(_colorset_rgb),
            len(_frame_set),
            len(_rot_set),
            len(_tex_idx),
            len(_type_set),
            len(self._body_names),
            len(_tex_dat_set.keys()),
            len(_tex_fnames),
        ]
        print("Check sets = ", _check_sets)
        assert _check_sets == ([_body_count, ] * (len(_check_sets) - 1) + [100,])
        print("\t>>>check sets check out!")
        logging.debug("STATIC DATA has been loaded and verified...")

        self._datastore = dict(DEF_EPOCH=DEF_EPOCH,
                               SYS_PARAMS=SIM_PARAMS,
                               TEX_FNAMES=_tex_fnames,
                               TEX_PATH=_tex_path,
                               TEX_DAT_SET=_tex_dat_set,
                               BODY_COUNT=_body_count,
                               BODY_NAMES=self._body_names,
                               COLOR_SET=_colorset_rgb,
                               TYPE_COUNT=_type_count,
                               BODY_DATA=_body_params,
                               )
        logging.debug("ALL data for the system have been collected...!")

    @property
    def def_epoch(self):
        return self._datastore['DEF_EPOCH']

    @property
    def system_params(self):
        return self._datastore['SYS_PARAMS']

    @property
    def texture_path(self):
        return self._datastore['TEX_PATH']

    @property
    def body_count(self):
        return self._datastore['BODY_COUNT']

    @property
    def body_names(self):
        # list of body names available in sim, cast to a tuple to preserve order
        return tuple([name for name in self._body_names])

    def get_body_data(self,
                      body_name=None,
                      data_keys=None,
                      ):
        res = {}
        if (body_name in self.body_names) and (data_keys is None):
            res = self._datastore['BODY_DATA'][body_name]
        # else:
        #     for key in data_keys:
        #         if key in self._datastore['BODY_DATA'][body_name].keys():
        #             res.update({key: self._datastore['BODY_DATA'][body_name][key]})
        #
        # if (body_name is None) and (data_keys is None):
        #     res = self._datastore['BODY_DATA']
        # elif any([key in self._datastore['BODY_DATA'][body_name].keys() for key in data_keys]):
        #     [res.update({key: self._datastore['BODY_DATA'][body_name][key]})
        #      for key in data_keys]

        return res


if __name__ == "__main__":

    def main():
        logging.debug("-------->> RUNNING SYSTEM_DATASTORE() STANDALONE <<---------------")

        dict_store = SystemDataStore()
        print("dict store:", dict_store)
        exit()

    main()
