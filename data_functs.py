# -*- coding: utf-8 -*-

import os
import logging
from astropy.time import Time
from poliastro.constants import J2000_TDB
from poliastro.bodies import *
from poliastro.frames.fixed import *
from poliastro.frames.fixed import MoonFixed as LunaFixed
from poliastro.core.fixed import *
# from planet_visual import SkyMap
from viz_functs import get_tex_data

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
    DEF_EPOCH   = J2000_TDB  # default epoch
    TEX_FNAMES  = []  # list of texture filenames (will be sorted)
    TEX_PATH    = "C:\\_Projects\\sns2\\resources\\textures\\"  # directory of texture image files
    _body_names  = []  # list of body names available in sim
    _body_count  = 0  # number of available bodies
    _type_count  = {}  # dict of body types and the count of each type
    BODY_DATA   = {}  # dict of body name and the static parameters of each
    tex_dat_set = {}  # dist of body name and the texture data associated with it
    SYS_PARAMS  = dict(dist_unit=u.km,
                       periods=365,
                       spacing=365.25 * 24 * 60 * 60 * u.s,
                       fps=30,)
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
            _body_names.append(bod.name)
            
    _body_names = tuple(_body_names)      # the tuple locks in the order of elements

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
    colorset_rgba = []  # convert from RGBA to rgba (0...1)
    for c in color_RGB:
        if c is not None:
            color_norm = [c[0] / 255, c[1] / 255, c[2] / 255, 0]
            colorset_rgba.append(np.array(color_norm))
        else:
            colorset_rgba.append(None)

    colorset_rgba = np.array(colorset_rgba)

    # get listing of texture filenames
    tex_dirlist = os.listdir(TEX_PATH)
    for i in tex_dirlist:
        if "png" in i:
            TEX_FNAMES.append(i)  # add PNG filenames to list
    TEX_FNAMES.sort()  # sort the list
    TEX_FNAMES = tuple(TEX_FNAMES)      # the tuple locks in the order of elements

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
               ]  # indices of default texture filename for each body

    body_types = ["star",
                  "planet",
                  "moon",
                  "ship",
                  ]  # types of bodies in simulation

    body_tmark = ['star',
                  'o',
                  'diamond',
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

    # TODO: This needs to live somewhere else, as in StarSystem class
    # sky_fname = TEX_PATH + TEX_FNAMES[48]
    # print(sky_fname)
    # skymap = SkyMap(edge_color=(0, 0, 1, .3),
    #                 color=(1, 1, 1, 1),
    #                 texture=get_tex_data(fname=sky_fname),
    #                 )

    for idx in range(len(_body_names)):  # idx = [0..,len(_body_names)-1]
        _bod_name = _body_names[idx]
        _body = body_set[idx]
        _bod_prnt = _body.parent

        logging.debug(">LOADING STATIC DATA for " + str(_bod_name))

        tex_fname = TEX_PATH + TEX_FNAMES[tex_idx[idx]]  # get path of indexed filename
        tex_dat_set.update({_bod_name: get_tex_data(fname=tex_fname)})  # add texture data to active dict
        logging.debug("tex_dat_set[" + str(idx) + "] = " + str(tex_fname))
        if _body.parent is None:
            R = _body.R
            Rm = Rp = R
        else:
            R = _body.R
            Rm = _body.R_mean
            Rp = _body.R_polar

        # a dict of ALL body data EXCEPT the viz_dict{}
        _body_data = dict(body_name=_body.name,  # build the BODY_DATA dict
                          body_obj=_body,
                          parent_obj=_body.parent,
                          r_set=(R, Rm, Rp),
                          fname_idx=tex_idx[idx],
                          fixed_frame=frame_set[idx],
                          rot_func=rot_set[idx],
                          body_color=colorset_rgba[idx],
                          tex_fname=tex_fname,
                          tex_dat=tex_dat_set[_bod_name],  # tex_dat_set[idx],
                          viz_names=viz_assign[_bod_name],
                          body_type=body_types[type_set[idx]],
                          body_mark=body_tmark[type_set[idx]],
                          n_samples=180,
                          )

        logging.debug("STATIC DATA has been loaded and verified...")
        BODY_DATA.update({_bod_name: _body_data})
        if _body_data["body_type"] not in _type_count.keys():  # identify types of bodies
            _type_count[_body_data["body_type"]] = 0

        _type_count[body_types[type_set[idx]]] += 1  # count members of each type
        idx += 1
        _body_count += 1

    check_sets = [
        len(body_set),
        len(colorset_rgba),
        len(frame_set),
        len(rot_set),
        len(tex_idx),
        len(type_set),
        len(_body_names),
        len(tex_dat_set.keys()),
        len(TEX_FNAMES),
    ]
    print("Check sets = ", check_sets)
    assert check_sets == ([_body_count, ] * (len(check_sets) - 1) + [100,])
    print("\t>>>check sets check out!")

    DATASTORE = dict(
        DEF_EPOCH=DEF_EPOCH,
        SYS_PARAMS=SYS_PARAMS,
        TEX_FNAMES=TEX_FNAMES,
        TEX_PATH=TEX_PATH,
        TEX_DAT_SET=tex_dat_set,
        BODY_COUNT=_body_count,
        BODY_NAMES=_body_names,
        BODY_DATA=BODY_DATA,
        COLOR_SET=colorset_rgba,
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
