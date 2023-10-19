# -*- coding: utf-8 -*-

import os
import math
import logging

import _utils
from planet_visual import SkyMap
from viz_functs import get_tex_data
from astropy.time import Time
from poliastro.constants import J2000_TDB
from poliastro.bodies import *
from poliastro.frames.fixed import *
from poliastro.frames.fixed import MoonFixed as LunaFixed
from poliastro.core.fixed import *


logging.basicConfig(
    filename="logs/sns_defs.log",
    level=logging.INFO,
    format="%(funcName)s:\t%(levelname)s:%(asctime)s:\t%(message)s",
)

vec_type = type(np.zeros((3,), dtype=np.float64))


def earth_rot_elements_at_epoch(T=None, d=None):
    """
    :param T:
    :param d:
    :return:
    """
    _T = T
    return 0, 90 - 23.5, (d - math.floor(d)) * 360.0


def t_since_ref(epoch=None, ref=J2000_TDB):
    """

    :param epoch:
    :param ref:
    :return:
    """
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
    """

    :return:
    """
    DEF_EPOCH = J2000_TDB  # default epoch
    TEX_FNAMES = []  # list of texture filenames (will be sorted)
    TEX_PATH = "C:\\Users\\madmaxfz\\PycharmProjects\\sns2\\resources\\textures\\"  # directory of texture image files
    BODY_NAMES = []  # list of body names available in sim
    BODY_COUNT = 0  # number of available bodies
    TYPE_COUNT = {}  # dict of body types and the count of each type
    BODY_DATA = {}  # dict of body name and the static parameters of each
    tex_data_set = {}  # dist of body name and the texture data associated with it
    SYS_PARAMS = dict(
        dist_unit=u.km,
        periods=30,
        spacing=1 * u.s / 30,
        fps=30,
    )
    body_set = [Sun,
                Mercury,
                Venus,
                Earth,
                Moon,  # all built-ins from poliastro
                Mars,
                Jupiter,
                Saturn,
                Uranus,
                Neptune,  # except Pluto
                Pluto,
                ]
    for bod in body_set:
        if bod is not None:
            BODY_NAMES.append(bod.name)
    BODY_NAMES = tuple(BODY_NAMES)

    tex_dirlist = os.listdir(TEX_PATH)  # get listing of texture filenames
    for i in tex_dirlist:
        if "png" in i:
            TEX_FNAMES.append(i)  # add PNG filenames to list
    TEX_FNAMES.sort()  # sort the list
    TEX_FNAMES = tuple(TEX_FNAMES)

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
    color_RGBA = [(253, 184, 19),  # base color for each body
                  (26, 26, 26),
                  (230, 230, 230),
                  (47, 106, 105),
                  (50, 50, 50),
                  (153, 61, 0),
                  (176, 127, 53),
                  (176, 143, 54),
                  (95, 128, 170),
                  (54, 104, 150),
                  (255, 255, 255),
                  ]
    colorset_rgba = []  # convert from RGBA to rgba (0...1)
    for c in color_RGBA:
        if c is not None:
            color_norm = [c[0] / 255, c[1] / 255, c[2] / 255, 1.]
            colorset_rgba.append(np.array(color_norm))
        else:
            colorset_rgba.append(None)

    colorset_rgba = np.array(colorset_rgba)

    tex_idx = [0,
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
               ]  # indices of texture filename for each body

    body_types = ["star",
                  "planet",
                  "moon",
                  "ship",
                  ]  # types of bodies in simulation

    body_tmark = ['star',
                  'o',
                  '+',
                  'diamond',
                  ]

    type_set = (0,
                1,
                1,
                1,
                2,
                1,
                1,
                1,
                1,
                1,
                1,
                )  # indices of type for each body

    viz_keys = ("reticle",
                "nametag",
                "refframe",
                "ruler",
                "surface",
                "oscorbit",
                "radvec",
                "velvec",
                )
    com_viz = [viz_keys[1], viz_keys[2], viz_keys[4]]
    xtr_viz = [viz_keys[5], viz_keys[6], viz_keys[7]]
    xtr_viz.extend(com_viz)
    xtr_viz = com_viz
    viz_assign = dict(
        Sun=com_viz,
        Mercury=xtr_viz,
        Venus=xtr_viz,
        Earth=xtr_viz,
        Moon=xtr_viz,
        Mars=xtr_viz,
        Jupiter=xtr_viz,
        Saturn=xtr_viz,
        Uranus=xtr_viz,
        Neptune=xtr_viz,
        Pluto=xtr_viz,
    )
    sky_fname = TEX_PATH + TEX_FNAMES[24]
    print(sky_fname)
    skymap = SkyMap(edge_color=(0, 0, 1, .3),
                    color=(0, 0, 0, .4),
                    texture=get_tex_data(fname=sky_fname),
                    )
    for idx in range(len(BODY_NAMES)):  # idx = [0..,len(BODY_NAMES)-1]
        _bod_name = BODY_NAMES[idx]
        _body = body_set[idx]
        _bod_prnt = _body.parent

        logging.debug(">LOADING STATIC DATA for " + str(_bod_name))

        tex_fname = TEX_PATH + TEX_FNAMES[tex_idx[idx]]  # get path of indexed filename
        tex_data_set.update({_bod_name: get_tex_data(fname=tex_fname)})  # add texture data to active dict
        logging.debug("tex_data_set[" + str(idx) + "] = " + str(tex_fname))

        # a dict of ALL body data EXCEPT the viz_dict{}
        _static_dat = dict(
            body_name=_body.name,  # build the BODY_DATA dict
            body_obj=_body,
            parent_obj=_body.parent,
            body_type=body_types[type_set[idx]],
            body_mark=body_tmark[type_set[idx]],
            fname_idx=tex_idx[idx],
            fixed_frame=frame_set[idx],
            rot_func=rot_set[idx],
            n_samples=180,
            body_color=colorset_rgba[idx],
            tex_data=tex_data_set[_bod_name],  # tex_data_set[idx],
            viz_names=viz_assign[_bod_name],
        )
        R_set = {}
        if _body.name == "Sun" or _static_dat["body_type"] == "star":
            R = _static_dat["body_obj"].R.value
            Rm = Rp = R
        else:
            R = _static_dat["body_obj"].R.value
            Rm = _static_dat["body_obj"].R_mean.value
            Rp = _static_dat["body_obj"].R_polar.value

        R_set.update({_static_dat["body_name"]: (R, Rm, Rp, )})
        _static_dat.update({_body.name: R_set})
        logging.debug("STATIC DATA has been loaded and verified...")
        BODY_DATA.update({_bod_name: _static_dat})
        if _static_dat["body_type"] not in TYPE_COUNT.keys():  # identify types of bodies
            TYPE_COUNT[_static_dat["body_type"]] = 0

        TYPE_COUNT[body_types[type_set[idx]]] += 1  # count members of each type
        # idx += 1
        BODY_COUNT += 1

    check_sets = [
        len(body_set),
        len(colorset_rgba),
        len(frame_set),
        len(rot_set),
        len(tex_idx),
        len(type_set),
        len(BODY_NAMES),
        len(tex_data_set.keys()),
        len(TEX_FNAMES),
    ]
    print("Check sets =\n", check_sets)
    assert check_sets == ([BODY_COUNT, ] *8 + [100,])
    print("\t>>>check sets check out!")

    DATASTORE = dict(
        DEF_EPOCH=DEF_EPOCH,
        SYS_PARAMS=SYS_PARAMS,
        TEX_FNAMES=TEX_FNAMES,
        TEX_PATH=TEX_PATH,
        BODY_NAMES=BODY_NAMES,
        BODY_COUNT=BODY_COUNT,
        TYPE_COUNT=TYPE_COUNT,
        BODY_DATA=BODY_DATA,
        TEX_DAT_SET=tex_data_set,
        SKYMAP=skymap,
        COLOR_SET=colorset_rgba,
    )

    logging.debug("ALL visuals for the system have been created...!")

    return DATASTORE


# def get_skymap():
#     _SkyMap = setup_datastore()["SKYMAP"]
#     logging.info("SkyMap available for import: " + str(_SkyMap))
#     return _SkyMap


if __name__ == "__main__":

    def main():
        logging.debug("-------->> RUNNING DATA_FUNCTS() STANDALONE <<---------------")

        dict_store = setup_datastore()
        print("dict store:", dict_store)

        # print("get_viz_data(Sun).items =",
        #       get_viz_data(Sun).items(), '\n',
        #       get_viz_data(Earth).items(),
        #       '\n', get_viz_data(Moon).items())
        exit()

    main()
