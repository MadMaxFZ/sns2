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


def setup_datastore():
    """"""
    DEF_EPOCH    = J2000_TDB  # default epoch
    SIM_PARAMS   = dict(sys_name="Sol",
                        def_epoch=DEF_EPOCH,
                        dist_unit=u.km,
                        periods=365,
                        spacing=24 * 60 * 60 * u.s,
                        fps=60,
                        )
    _tex_path    = "C:\\_Projects\\sns2\\resources\\textures\\"  # directory of texture image files
    _tex_fnames  = []  # list of texture filenames (will be sorted)
    _tex_dat_set = {}  # dist of body name and the texture data associated with it
    _body_params = {}  # dict of body name and the static parameters of each
    _body_names  = []  # list of body names available in sim
    _body_count  = 0   # number of available bodies
    _type_count  = {}  # dict of body types and the count of each typE
    _viz_assign   = {}  # dict of visual names to use for each body

    body_set = [Sun,
                Mercury,
                Venus,
                Earth,
                Moon,  # all built-ins from poliastro
                Mars,
                Jupiter,
                Saturn,
                Uranus,
                Neptune,
                Pluto,
                ]
    # reference frame fixed to planet surfaces
    frame_set = [SunFixed,
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
    rot_set = [sun_rot_elements_at_epoch,
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
    color_RGB = [[253, 184, 19],  # base color for each body
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
    colorset_rgb = np.array(color_RGB) / 256
    # indices of texture filenames for each body
    tex_idx = (0,
               1,
               3,
               10,
               17,
               11,
               12,
               13,
               15,
               16,
               17,
               )
    # types of bodies in simulation
    body_types = ("star",
                  "planet",
                  "moon",
                  "ship",
                  )
    # Markers symbol to be used for each body type
    body_tmark = ('star',
                  'o',
                  'diamond',
                  'triangle',
                  )
    # indices of body type for each body
    type_set = (0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, )
    # visual elements to use on which bodies
    viz_keys = ("reticle", "nametag", "refframe", "ruler",
                "surface", "oscorbit", "radvec", "velvec", )
    com_viz = [viz_keys[1], viz_keys[2], viz_keys[4]]
    xtr_viz = [viz_keys[5], viz_keys[6], viz_keys[7]]
    xtr_viz.extend(com_viz)
    [_viz_assign.update({name: xtr_viz}) for name in _body_names]
    _viz_assign['Sun'] = com_viz

    for _body in body_set:
        if _body is not None:
            _body_names.append(_body.name)
    _body_names = tuple(_body_names)      # the tuple locks in the order of elements

    # get listing of texture filenames
    tex_dirlist = os.listdir(_tex_path)
    for i in tex_dirlist:
        if "png" in i:
            _tex_fnames.append(i)       # add PNG type files to list
    # _tex_fnames = _tex_fnames.sort()  # it doesn't like this sort()
    _tex_fnames = tuple(_tex_fnames)    # the tuple locks in the order of sorted elements

    for idx in range(len(_body_names)):  # idx = [0..,len(_body_names)-1]
        _bod_name = _body_names[idx]
        _body = body_set[idx]
        _bod_prnt = _body.parent

        logging.debug(">LOADING STATIC DATA for " + str(_bod_name))

        tex_fname = _tex_path + _tex_fnames[tex_idx[idx]]  # get path of indexed filename
        _tex_dat_set.update({_bod_name: get_tex_data(fname=tex_fname)})  # add texture data to active dict
        logging.debug("_tex_dat_set[" + str(idx) + "] = " + str(tex_fname))
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
                          fname_idx=tex_idx[idx],
                          fixed_frame=frame_set[idx],
                          rot_func=rot_set[idx],
                          body_color=colorset_rgb[idx],
                          tex_fname=_tex_fnames[tex_idx[idx]],
                          tex_dat=_tex_dat_set[_bod_name],  # _tex_dat_set[idx],
                          viz_names=_viz_assign[_bod_name],
                          body_type=body_types[type_set[idx]],
                          body_mark=body_tmark[type_set[idx]],
                          n_samples=365,
                          )
        _body_params.update({_bod_name: _body_data})

        if _body_data["body_type"] not in _type_count.keys():  # identify types of bodies
            _type_count[_body_data["body_type"]] = 0
        _type_count[body_types[type_set[idx]]] += 1  # count members of each type
        idx += 1
        _body_count += 1

    check_sets = [
        len(body_set),
        len(colorset_rgb),
        len(frame_set),
        len(rot_set),
        len(tex_idx),
        len(type_set),
        len(_body_names),
        len(_tex_dat_set.keys()),
        len(_tex_fnames),
    ]
    print("Check sets = ", check_sets)
    assert check_sets == ([_body_count, ] * (len(check_sets) - 1) + [100,])
    print("\t>>>check sets check out!")
    logging.debug("STATIC DATA has been loaded and verified...")

    DATASTORE = dict(DEF_EPOCH=DEF_EPOCH,
                     SYS_PARAMS=SIM_PARAMS,
                     TEX_FNAMES=_tex_fnames,
                     TEX_PATH=_tex_path,
                     TEX_DAT_SET=_tex_dat_set,
                     BODY_COUNT=_body_count,
                     BODY_NAMES=_body_names,
                     BODY_DATA=_body_params,
                     COLOR_SET=colorset_rgb,
                     TYPE_COUNT=_type_count,
                     )

    logging.debug("ALL visuals for the system have been created...!")

    return DATASTORE


if __name__ == "__main__":

    def main():
        logging.debug("-------->> RUNNING DATA_FUNCTS() STANDALONE <<---------------")

        dict_store = setup_datastore()
        print("dict store:", dict_store)
        exit()

    main()
