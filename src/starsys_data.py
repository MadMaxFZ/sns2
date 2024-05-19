# -*- coding: utf-8 -*-
# x
import os
import sys
import logging
import logging.config
import autologging
import astropy.units as u
from PIL import Image
from astropy.time import Time
from poliastro.constants import J2000_TDB
from poliastro.bodies import *
from poliastro.frames.fixed import *
from poliastro.frames.fixed import MoonFixed as LunaFixed
from vispy.util.quaternion import Quaternion
from poliastro.core.fixed import *
from vispy.geometry.meshdata import MeshData
from viz_functs import get_tex_data

SNS_SOURCE_PATH = "c:\\_Projects\\sns2\\src\\"
os.chdir(SNS_SOURCE_PATH)

logging.basicConfig(filename=SNS_SOURCE_PATH + "../logs/sns_defs.log",
                    level=logging.ERROR,
                    format="%(funcName)s:\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )
DEF_UNITS     = u.km
DEF_EPOCH0    = J2000_TDB
DEF_TEX_FNAME = "../resources/textures/2k_5earth_daymap.png"
vec_type = type(np.zeros((3,), dtype=np.float64))
DEF_CAM_STATE = {'center': (-8.0e+08, 0.0, 0.0),
                 'scale_factor': 0.5e+08,
                 'rotation1': Quaternion(-0.5, +0.5, -0.5, -0.5),
                 }


def quat_to_rpy(quat):
    if quat is not None:
        # quat.w = abs(quat.w)
        t0 = +2.0 * (quat.w * quat.x + quat.y * quat.z)
        t1 = +1.0 - 2.0 * (quat.x * quat.x + quat.y * quat.y)
        yaw_x = round(math.atan2(t0, t1) * 180 / math.pi, 4)

        t2 = +2.0 * (quat.w * quat.y - quat.z * quat.x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch_y = round(math.asin(t2) * 180 / math.pi - 90, 4)

        t3 = +2.0 * (quat.w * quat.z + quat.x * quat.y)
        t4 = +1.0 - 2.0 * (quat.y * quat.y + quat.z * quat.z)
        roll_z = round(math.atan2(t3, t4) * 180 / math.pi, 4)

        # if yaw_x >= 180:
        #     yaw_x -= 360
        # elif yaw_x <= -180:
        #     yaw_x += 360
        #
        # if roll_z >= 180:
        #     roll_z -= 360
        # elif roll_z <= -180:
        #     roll_z += 360

        return yaw_x, pitch_y, roll_z


def to_rpy_str(quat):
        yaw_x, pitch_y, roll_z = quat_to_rpy(quat)

        eul_str = str("R: " + pad_plus(f'{roll_z:5.4}') +
                      "\nP: " + pad_plus(f'{pitch_y:5.4}') +
                      "\nY: " + pad_plus(f'{yaw_x:5.4}'))

        return eul_str


def get_texture_data(fname=DEF_TEX_FNAME):
    with Image.open(fname) as im:
        print(fname, im.format, f"{im. size}x{im.mode}")
        return im.copy()


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


# taken from https://goshippo.com/blog/measure-real-size-any-python-object by Wissam Jarjoui
def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


def _latitude(rows=4, cols=8, radius=1, offset=False):
    verts = np.empty((rows+1, cols, 3), dtype=np.float32)

    # compute vertices
    phi = (np.arange(rows+1) * np.pi / rows).reshape(rows+1, 1)
    s = radius * np.sin(phi)
    verts[..., 2] = radius * np.cos(phi)
    th = ((np.arange(cols) * 2 * np.pi / cols).reshape(1, cols))
    if offset:
        # rotate each row by 1/2 column
        th = th + ((np.pi / cols) * np.arange(rows+1).reshape(rows+1, 1))
    verts[..., 0] = s * np.cos(th)
    verts[..., 1] = s * np.sin(th)
    # remove redundant vertices from top and bottom
    verts = verts.reshape((rows+1)*cols, 3)[cols-1:-(cols-1)]

    # compute faces
    faces = np.empty((rows*cols*2, 3), dtype=np.uint32)
    rowtemplate1 = (((np.arange(cols).reshape(cols, 1) +
                      np.array([[1, 0, 0]])) % (cols)) +
                    np.array([[0, 0, cols]]))
    rowtemplate2 = (((np.arange(cols).reshape(cols, 1) +
                      np.array([[1, 0, 1]])) % (cols)) +
                    np.array([[0, cols, cols]]))
    for row in range(rows):
        start = row * cols * 2
        faces[start:start + cols] = rowtemplate1 + row * cols
        faces[start + cols:start + 2 * cols] = rowtemplate2 + row * cols
    # cut off zero-area triangles at top and bottom
    faces = faces[cols:-cols]

    # adjust for redundant vertices that were removed from top and bottom
    vmin = cols-1
    faces[faces < vmin] = vmin
    faces -= vmin
    vmax = verts.shape[0]-1
    faces[faces > vmax] = vmax
    return MeshData(vertices=verts, faces=faces)


def _oblate_sphere(rows=4, cols=None, radius=(1200 * u.km,) * 3, offset=False):
    verts = np.empty((rows + 1, cols + 1, 3), dtype=np.float32)
    tcrds = np.empty((rows + 1, cols + 1, 2), dtype=np.float32)
    norms = np.linalg.norm(verts)

    # compute vertices
    phi = (np.arange(rows + 1) * np.pi / rows).reshape(rows+1, 1)
    s = radius[0] * np.sin(phi)
    verts[..., 2] = radius[2] * np.cos(phi)
    th = ((np.arange(cols + 1) * 2 * np.pi / cols).reshape(1, cols + 1))
    # if offset:
    #     # rotate each row by 1/2 column
    #     th = th + ((np.pi / cols) * np.arange(rows+1).reshape(rows+1, 1))
    verts[..., 0] = s * np.cos(th)
    verts[..., 1] = s * np.sin(th)
    tcrds[..., 0] = th / (2 * np.pi)
    tcrds[..., 1] = 1 - phi / np.pi
    # remove redundant vertices from top and bottom
    verts = verts.reshape((rows + 1) * (cols + 1), 3)  # [cols:-cols]
    tcrds = tcrds.reshape((rows + 1) * (cols + 1), 2)  # [cols:-cols]

    # compute faces
    rowtemplate1 = (((np.arange(cols).reshape(cols, 1) + np.array([[1, 0, 0]])) % (cols + 2)) +
                    np.array([[0, 0, cols + 1]]))
    rowtemplate2 = (((np.arange(cols).reshape(cols, 1) + np.array([[1, 0, 1]])) % (cols + 2)) +
                    np.array([[0, cols + 1, cols + 1]]))
    # print(rowtemplate1.shape, "\n", rowtemplate2.shape)
    faces = np.empty((rows * cols * 2, 3), dtype=np.uint32)
    for row in range(rows):
        start = row * cols * 2
        if row != 0:
            faces[start:start + cols] = rowtemplate1 + row * (cols + 1)
        if row != rows - 1:
            faces[start + cols:start + (2 * cols)] = rowtemplate2 + row * (cols + 1)
    faces = faces[cols:-cols]

    edges = MeshData(vertices=verts, faces=faces).get_edges()
    eclrs = np.zeros((len(edges), 4), dtype=np.float32)
    eclrs[np.arange(len(edges)), :] = (1, 1, 1, 1)

    return dict(verts=verts,
                norms=norms,
                faces=faces,
                edges=edges,
                ecolr=eclrs,
                tcord=tcrds,
                )


def round_off(val):
    n_digits = 3
    factor = pow(10, n_digits)
    try:
        data_unit = val / val.value
        res = (int(val.value * factor) / factor) * data_unit

    except:
        res = val

    return res


def show_it(value):
    # print(f'VAL: {value}, TYPE(VAL): {type(value)}')
    pass


def to_bold_font(value):
    if value:
        ante = "<html><head/><body><p><span style=\" font-weight:600;\">"
        post = "</span></p></body></html>"

        return ante + str(value) + post


def pad_plus(value):
    if value:
        res = value
        if float(value) > 0:
            res = "+" + value

        return res

    else:
        return ''


def to_vector_str(vec, hdrs=None):
    if vec is not None:
        # print(f'{type(vec)}')
        if not hdrs:
            hdrs = ('X:', '\nY:', '\nZ:')
        # vec = vec.value
        vec_str = str(hdrs[0] + pad_plus(f'{vec[0]:5.4}') +
                      hdrs[1] + pad_plus(f'{vec[1]:5.4}') +
                      hdrs[2] + pad_plus(f'{vec[2]:5.4}'))

        return vec_str


def to_quat_str(quat):
    if quat is not None:
        # print(f'{type(quat)}')
        quat_str = str("X: " + f'{quat.x:5.4}' +
                       "\nY: " + f'{quat.y:5.4}' +
                       "\nZ: " + f'{quat.z:5.4}' +
                       "\nW: " + f'{quat.w:5.4}')

        return quat_str


log_config = {
    "version": 1,
    "formatters": {
        "logformatter": {
            "format":
                "%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s",
        },
        "traceformatter": {
            "format":
                "%(asctime)s:%(process)s:%(levelname)s:%(filename)s:"
                    "%(lineno)s:%(name)s:%(funcName)s:%(message)s",
        },
    },
    "handlers": {
        "loghandler": {
            "class": "logging.FileHandler",
            "level": logging.DEBUG,
            "formatter": "logformatter",
            "filename": "app.log",
        },
        "tracehandler": {
            "class": "logging.FileHandler",
            "level": autologging.TRACE,
            "formatter": "traceformatter",
            "filename": "trace.log",
        },
    },
    "loggers": {
        "my_module.MyClass": {
            "level": autologging.TRACE,
            "handlers": ["tracehandler", "loghandler"],
        },
    },
}


class SystemDataStore:
    def __init__(self):
        """
        """
        self._dist_unit = DEF_UNITS
        DEF_EPOCH    = DEF_EPOCH0     # default epoch
        SYS_PARAMS   = dict(sys_name="Sol",
                            def_epoch=DEF_EPOCH,
                            dist_unit=self._dist_unit,
                            periods=365,
                            spacing=24 * 60 * 60 * u.s,     # one Earth day
                            fps=60,
                            n_samples=365,
                            )
        _tex_path      = "../resources/textures/"      # directory of texture image files for windows
        _def_tex_fname = "2k_ymakemake_fictional.png"
        _tex_fnames    = []  # list of texture filenames (will be sorted)
        _tex_dat_set   = {}  # dist of body name and the texture data associated with it
        _body_params   = {}  # dict of body name and the static parameters of each
        _vizz_params   = {}  # dict of body name and the semi-static visual parameters
        _type_count    = {}  # dict of body types and the count of each typE
        _viz_assign    = {}  # dict of visual names to use for each body
        _body_count    = 0   # number of available bodies
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
        _body_mark = ('star',
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
                              fixed_frame=_frame_set[idx],
                              rot_func=_rot_set[idx],
                              o_period=_o_per_set[idx].to(u.s),
                              body_type=_body_types[_type_set[idx]]
                              )
            _body_params.update({_bod_name: _body_data})
            # a dict of the initial visual parameters
            _vizz_data = dict(body_color=_colorset_rgb[idx],
                              body_alpha=1.0,
                              track_alpha=0.6,
                              body_mark=_body_mark[_type_set[idx]],
                              fname_idx=_tex_idx[idx],
                              tex_fname=_tex_fnames[_tex_idx[idx]],
                              tex_data=_tex_dat_set[_bod_name],  # _tex_dat_set[idx],
                              viz_names=_viz_assign[_bod_name],
                              )
            _vizz_params.update({_bod_name: _vizz_data})

            if _body_data['body_type'] not in _type_count.keys():  # identify types of bodies
                _type_count[_body_data['body_type']] = 0
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

        self._datastore = dict(DFLT_EPOCH=DEF_EPOCH,
                               SYS_PARAMS=SYS_PARAMS,
                               TEX_FNAMES=_tex_fnames,
                               TEXTR_PATH=_tex_path,
                               TEXTR_DATA=_tex_dat_set,
                               BODY_COUNT=_body_count,
                               BODY_NAMES=self._body_names,
                               COLOR_DATA=_colorset_rgb,
                               TYPE_COUNT=_type_count,
                               BODY_PARAM=_body_params,
                               VIZZ_PARAM=_vizz_params,
                               )
        logging.debug("ALL data for the system have been collected...!")

    @property
    def dist_unit(self):
        return self._dist_unit

    @property
    def vec_type(self):
        return type(np.zeros((3,), dtype=np.float64))

    @property
    def default_epoch(self):
        return self._datastore['DFLT_EPOCH']

    @property
    def system_params(self):
        return self._datastore['SYS_PARAMS']

    @property
    def body_count(self):
        return len(self.body_names)

    @property
    def body_names(self):
        # list of body names available in sim, cast to a tuple to preserve order
        return tuple([name for name in self._body_names])

    @property
    def body_data(self, name=None):
        res = None
        if not name:
            res = self._datastore['BODY_PARAM']
        elif name in self.body_names:
            res = self._datastore['BODY_PARAM'][name]

        return res

    def vizz_data(self, name=None):
        res = None
        if not name:
            res = self._datastore['VIZZ_PARAM']
        elif name in self.body_names:
            res = self._datastore['VIZZ_PARAM'][name]

        return res

    @property
    def texture_path(self):
        return self._datastore['TEXTR_PATH']

    @property
    def texture_fname(self, name=None):
        res = None
        if name is None:
            res = self._datastore['TEX_FNAMES']
        elif name in self.body_names:
            res = self._datastore['BODY_PARAM'][name]['tex_fname']

        return res

    @property
    def texture_data(self, name=None):
        res = None
        if name is None:
            res = self._datastore['TEXTR_DATA']
        elif name in self.body_names:
            res = self._datastore['BODY_PARAM'][name]['tex_data']

        return res

    @property
    def data_store(self):
        return self._datastore

    @property
    def model_data_group_keys(self):
        return tuple(['attr_', 'elem_coe', 'elem_pqw', 'elem_rv', 'syst_', 'vizz_'])


if __name__ == "__main__":

    def main():
        logging.debug("-------->> RUNNING SYSTEM_DATASTORE() STANDALONE <<---------------")

        dict_store = SystemDataStore()
        print("dict store:", dict_store)
        print(dict_store.body_data("Earth"))
        exit()

    main()

"""
    The following moons of the Solar System are tidally locked:
        Mercury:    (3-2 spin-orbit resonance)
        
        Earth:      Moon
        
        Mars:       Phobos
                    Deimos
        
        Jupiter:    Io
                    Europa
                    Ganymede
                    Callisto
                    Amalthea
                    Himalia
                    Elara
                    Pasiphae
                    Metis
                    Adrastea
                    Thebe
        
        Saturn:     Titan
                    Enceladus
                    Pan
                    Atlas
                    Prometheus
                    Pandora
                    Epimetheus
                    Janus
                    Mimas
                    Telesto
                    Tethys
                    Calypso
                    Dione
                    Rhea
                    Iapetus
                    - Daphnis
                    - Aegaeon
                    - Methone
                    - Anthe
                    - Pallene
                    - Helene
                    - Polydeuces
                    Hyperion    (rotates chaotically)
        
        Uranus:     Miranda
                    Ariel
                    Umbriel
                    Titania
                    Oberon
                    - Cordelia
                    - Ophelia
                    - Bianca
                    - Cressida
                    - Desdemona
                    - Juliet
                    - Portia
                    - Rosalind
                    - Cupid
                    - Belinda
                    - Perdita
                    - Puck
                    - Mab
        
        Neptune:    Proteus
                    Triton
                    - Naiad
                    - Thalassa
                    - Despina
                    = Galatea
                    - Larissa
        
        Pluto:      Charon      (mutually locked)
        
        Eris:       Dysnomia    (mutually locked)

        Orcus:      Vanth       (mutually locked)
"""