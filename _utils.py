# basic imports, general data and functions
# @2023 Max S. Whitten madmaxfz@protonmail.com

import os
import sys
import numpy as np
import logging
import subprocess
from starsys_data import *
from viz_functs import *
from multiprocessing import Pool, Queue, Process, Lock
from astropy.time import TimeDelta, Time
from poliastro.bodies import *
from poliastro.constants import J2000_TDB
from poliastro.twobody.orbit.scalar import Orbit
from poliastro.ephem import *
from poliastro.frames.enums import Planes
from poliastro.frames.fixed import *
from poliastro.frames.fixed import MoonFixed as LunaFixed
from astropy.coordinates import solar_system_ephemeris
from poliastro.core.fixed import *
import astropy.units as u
from astropy.coordinates.solar_system import get_body_barycentric_posvel
from vispy import app
from vispy.app import Canvas
from vispy.app.timer import Timer
from vispy.visuals import transforms as tr
from vispy.scene.visuals import *

solar_system_ephemeris.set("jpl")
# bods=solar_system_ephemeris.bodies
# [print(dir(d)) for d in bods]

# globals
epoch0 = J2000_TDB
T_now = Time(val=Time.now(), format="jd", scale="tdb")
t_delta = 24 * u.hr
body_dict = dict(
    Sun=Sun,
    Mercury=Mercury,
    Venus=Venus,
    Earth=Earth,
    Moon=Moon,
    Mars=Mars,
    Jupiter=Jupiter,
    Saturn=Saturn,
    Uranus=Uranus,
    Neptune=Neptune,
    Pluto=Pluto,
)
symb = "star"


def earth_rot_elements_at_epoch(T=None, d=None):
    # d = (epoch - epoch0).jd
    # T = d / 36525
    # print("Centuries since J2000:", T)
    # print("Days since J2000:", d)
    return 23.5, 0, (d / 360.0)


def toTD(epoch=None):
    d = (epoch - epoch0).jd
    T = d / 36525
    return dict(T=T, d=d)


# body color values in RGBA (0...255)
color_RGBA = [
    (253, 184, 19, 255),  # base color for Sun
    (26, 26, 26, 255),  # base color for Mercury
    (230, 230, 230, 255),  # base color for Venus
    (47, 106, 105, 255),  # base color for Earth
    (192, 192, 192, 255),  # base color for Moon
    (153, 61, 0, 255),  # base color for Mars
    (176, 127, 53, 255),  # base color for Jupiter
    (176, 143, 54, 255),  # base color for Saturn
    (95, 128, 170, 255),  # base color for Uranus
    (54, 104, 150, 255),  # base color for Neptune
    (221, 196, 175, 255),  # base color for Pluto
]
color_rgba = [(c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255) for c in color_RGBA]
rot_set = [
    sun_rot_elements_at_epoch,
    mercury_rot_elements_at_epoch,
    venus_rot_elements_at_epoch,
    earth_rot_elements_at_epoch,
    moon_rot_elements_at_epoch,
    mars_rot_elements_at_epoch,
    jupiter_rot_elements_at_epoch,
    saturn_rot_elements_at_epoch,
    uranus_rot_elements_at_epoch,
    neptune_rot_elements_at_epoch,
    earth_rot_elements_at_epoch,
]

idx = 0
body_color = {}
rotfunc = {}
for b_name in body_dict.keys():
    body_color.update({b_name: color_rgba[idx]})
    rotfunc.update({b_name: rot_set[idx]})
    idx += 1

ss_obj_radii = []  # [696342, 2440, 6052, 6371, 1737, 3390,
# 69911, 58232, 25362, 24622, 1188]
[ss_obj_radii.append(body.R.to(u.km).value) for body in body_dict.values()]
min_rad = np.min(ss_obj_radii)
max_rad = np.max(ss_obj_radii)
sun_unit = ss_obj_radii / max_rad
merc_unit = np.ceil(ss_obj_radii / min_rad)
sun_mark = merc_unit[0]
merc_unit *= 2
merc_unit[0] = sun_mark

solar_sys = {}


class Listener:
    def __init__(self):
        pass

    def listen(self, q=None, func=print):

        while True:
            try:
                data = q.get_nowait()
                if data is not None:
                    logging.info("Got data = " + str(data))
                    func(data)
                    if data == "DONE":
                        break
            except:
                pass


class Emitter:
    def __init__(
        self,
        t=None,
    ):
        self.timer = t
        logging.info("Emitter __init__...")

    def emit(self, q=None):
        self.timer.start()
        while True:
            dt = self.timer.elapsed
            while (self.timer.elapsed - dt) < self.timer.interval:
                pass
            sent = False
            while not sent:
                try:
                    q.put(dt)
                    sent = True
                except:
                    pass
