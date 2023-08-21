"""Provisional Euclid instrument and observational settings.

See Optics and Observation Conditions spreadsheet at
https://docs.google.com/spreadsheets/d/1pMUB_OOZWwXON2dd5oP8PekhCT5MBBZJO1HV7IMZg4Y/edit?usp=sharing
for list of
sources.
"""
import lenstronomy.Util.util as util

__all__ = ["Euclid"]

VIS_obs = {
    "exposure_time": 565.0,
    "sky_brightness": 22.35,
    "magnitude_zero_point": 24.0,
    "num_exposures": 4,
    "seeing": 0.16,
    "psf_type": "GAUSSIAN",
}
"""
:keyword exposure_time: exposure time per image (in seconds)
:keyword sky_brightness: sky brightness (in magnitude per square arcseconds in units of electrons)
:keyword magnitude_zero_point: magnitude in which 1 count (e-) per second per arcsecond square is registered
:keyword num_exposures: number of exposures that are combined (depends on coadd_years)  
:keyword seeing: Full-Width-at-Half-Maximum (FWHM) of PSF
:keyword psf_type: string, type of PSF ('GAUSSIAN' supported) 
"""


class Euclid(object):
    """Class contains Euclid instrument and observation configurations."""

    def __init__(self, band="VIS", psf_type="GAUSSIAN", coadd_years=6):
        """

        :param band: string, only 'VIS' supported. Determines obs dictionary.
        :param psf_type: string, type of PSF ('GAUSSIAN' supported).
        :param coadd_years: int, number of years corresponding to num_exposures in obs dict. Currently supported: 2-6.
        """
        self.obs = VIS_obs
        if band != "VIS":
            raise ValueError("band %s not supported! Choose 'VIS'." % band)

        if psf_type != "GAUSSIAN":
            raise ValueError("psf_type %s not supported!" % psf_type)

        if coadd_years > 6 or coadd_years < 2:
            raise ValueError(
                " %s coadd_years not supported! Choose an integer between 2 and 6."
                % coadd_years
            )
        elif coadd_years != 6:
            self.obs["num_exposures"] = (coadd_years * VIS_obs["num_exposures"]) // 6

        self.camera = {"read_noise": 4.2, "pixel_scale": 0.101, "ccd_gain": 3.1}
        """:keyword read_noise: std of noise generated by read-out (in units of
        electrons) :keyword pixel_scale: scale (in arcseconds) of pixels :keyword
        ccd_gain: electrons/ADU (analog-to-digital unit)."""

    def kwargs_single_band(self):
        """

        :return: merged kwargs from camera and obs dicts
        """
        kwargs = util.merge_dicts(self.camera, self.obs)
        return kwargs
