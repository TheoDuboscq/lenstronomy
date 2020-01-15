import numpy as np
import warnings
import lenstronomy.Util.data_util as data_util
from lenstronomy.Data.psf import PSF


class Instrument(object):
    """
    basic access points to instrument properties
    """
    def __init__(self, pixel_scale, read_noise=None, ccd_gain=None):
        """

        :param read_noise: std of noise generated by read-out (in units of electrons)
        :param pixel_scale: scale (in arcseonds) of pixels
        :param ccd_gain: electrons/ADU (analog-to-digital unit). A gain of 8 means that the camera digitizes the CCD signal
         so that each ADU corresponds to 8 photoelectrons.
        """
        if ccd_gain is not None:
            ccd_gain = float(ccd_gain)
        self.ccd_gain = ccd_gain
        self._read_noise = read_noise
        self.pixel_scale = pixel_scale


class Observation(object):
    """
    basic access point to observation properties
    """
    def __init__(self, exposure_time, sky_brightness=None, seeing=None, num_exposures=1,
                 psf_type='GAUSSIAN', kernel_point_source=None, truncation=5):
        """

        :param exposure_time: exposure time per image (in seconds)
        :param sky_brightness: sky brightness (in magnitude per square arcseconds)
        :param seeing: full width at half maximum of the PSF (if not specific psf_model is specified)
        :param num_exposures: number of exposures that are combined
        :param psf_type: string, type of PSF ('GAUSSIAN' and 'PIXEL' supported)
        :param kernel_point_source: 2d numpy array, model of PSF centered with odd number of pixels per axis
        (optional when psf_type='PIXEL' is chosen)
        """
        self._exposure_time = exposure_time
        self._sky_brightness = sky_brightness
        self._num_exposures = num_exposures
        self._seeing = seeing
        self._psf_type = psf_type
        self._truncation = truncation
        self._kernel_point_source = kernel_point_source

    def update_observation(self, exposure_time=None, sky_brightness=None, seeing=None, num_exposures=None,
                           psf_type=None, kernel_point_source=None):
        """
        updates class instance with new properties if specific argument is not None

        :param exposure_time: exposure time per image (in seconds)
        :param sky_brightness: sky brightness (in magnitude per square arcseconds)
        :param seeing: full width at half maximum of the PSF (if not specific psf_model is specified)
        :param num_exposures: number of exposures that are combined
        :param psf_type: string, type of PSF ('GAUSSIAN' and 'PIXEL' supported)
        :param kernel_point_source: 2d numpy array, model of PSF centered with odd number of pixels per axis (optional when psf_type='PIXEL' is chosen)
        :return: None, updated class instance
        """
        if exposure_time is not None:
            self._exposure_time = exposure_time
        if sky_brightness is not None:
            self._sky_brightness = sky_brightness
        if seeing is not None:
            self._seeing = seeing
        if num_exposures is not None:
            self._num_exposures = num_exposures
        if psf_type is not None:
            self._psf_type = psf_type
        if kernel_point_source is not None:
            self._kernel_point_source = kernel_point_source

    @property
    def exposure_time(self):
        """
        total exposure time

        :return: summed exposure time
        """
        return self._exposure_time * self._num_exposures

    @property
    def psf_class(self):
        """
        creates instance of PSF() class based on knowledge of the observations
        For the full possibility of how to create such an instance, see the PSF() class documentation

        :return: instance of PSF() class
        """
        if self._psf_type == 'GAUSSIAN':
            psf_type = "GAUSSIAN"
            fwhm = self._seeing
            truncation = self._truncation
            kwargs_psf = {'psf_type': psf_type, 'fwhm': fwhm, 'truncation': truncation}
        elif self._psf_type == 'PIXEL':
            if self._kernel_point_source is not None:
                kwargs_psf = {'psf_type': "PIXEL", 'kernel_point_source': self._kernel_point_source}
            else:
                raise ValueError("You need to create the class instance with a psf_model!")
        elif self._psf_type == 'NONE':
            kwargs_psf = {'psf_type': "NONE"}
        else:
            raise ValueError("psf_type %s not supported!" % self._psf_type)
        psf_class = PSF(**kwargs_psf)
        return psf_class


class SingleBand(Instrument, Observation):
    """
    class that combines Instrument and Observation
    """
    def __init__(self, pixel_scale, exposure_time, magnitude_zero_point, read_noise=None, ccd_gain=None,
                 sky_brightness=None, seeing=None, num_exposures=1, psf_type='GAUSSIAN', kernel_point_source=None,
                 truncation=5, data_count_unit='ADU', background_noise=None):
        """

        :param read_noise: std of noise generated by read-out (in units of electrons)
        :param pixel_scale: scale (in arcseconds) of pixels
        :param ccd_gain: electrons/ADU (analog-to-digital unit). A gain of 8 means that the camera digitizes the CCD signal
         so that each ADU corresponds to 8 photoelectrons.
        :param exposure_time: exposure time per image (in seconds)
        :param sky_brightness: sky brightness (in magnitude per square arcseconds)
        :param seeing: fwhm of PSF
        :param magnitude_zero_point: magnitude in which 1 count per second per arcsecond square is registered
        :param num_exposures: number of exposures that are combined
        :param data_count_unit: string, unit of the data (and other properties), 'e-': (electrons assumed to be IID),
        'ADU': (analog-to-digital unit)
        :param background_noise: sqrt(variance of background) as a total contribution from readnoise, sky brightness etc in units of the data_count_units
        If you set this parameter, it will use this value regardless of the values of read_noise, sky_brightness
        """
        Instrument.__init__(self, pixel_scale, read_noise, ccd_gain)  # read_noise and ccd_gain can be None
        Observation.__init__(self, exposure_time=exposure_time, sky_brightness=sky_brightness,
                             seeing=seeing, num_exposures=num_exposures,
                             psf_type=psf_type, kernel_point_source=kernel_point_source, 
                             truncation=truncation)
        if data_count_unit not in ['e-', 'ADU']:
            raise ValueError("count_unit type %s not supported! Please chose e- or ADU." % data_count_unit)
        self._data_count_unit = data_count_unit
        self._background_noise = background_noise
        self._magnitude_zero_point = magnitude_zero_point

    @property
    def read_noise(self):
        """

        :return: sqrt(variance) of read noise in units of the data
        """
        if self._read_noise is None:
            raise ValueError('read_noise is not specified!')
        if self._data_count_unit == 'ADU':
            return self._read_noise / self.ccd_gain
        else:
            return self._read_noise

    @property
    def sky_brightness(self):
        """

        :return: sky brightness (counts per square arcseconds in unit of data per unit time)
        """
        if self._sky_brightness is None:
            raise ValueError('sky_brightness is not set in the class instance!')
        cps = data_util.magnitude2cps(self._sky_brightness, magnitude_zero_point=self._magnitude_zero_point)
        if self._data_count_unit == 'e-':
            cps *= self.ccd_gain
        return cps

    @property
    def background_noise(self):
        """
        Gaussian sigma of noise level per pixel (in counts per second)

        :return: sqrt(variance) of background noise level in data units
        """
        if self._background_noise is None:
            if self._read_noise is None:
                raise ValueError('read_noise is not specified to evaluate background noise!')
            return data_util.bkg_noise(self.read_noise, self._exposure_time, self.sky_brightness, self.pixel_scale,
                                       num_exposures=self._num_exposures)
        else:
            if self._read_noise is not None:
                warnings.warn('read noise is specified but not used for noise properties. background noise is estimated'
                              ' from "background_noise" argument')
            return self._background_noise

    def flux_noise(self, flux):
        """

        :param flux: float or array, units of count_unit/seconds, needs to be positive semi-definite in the flux value
        :return: Gaussian approximation of Poisson statistics in IIDs sqrt(variance)
        """
        if self._data_count_unit == 'ADU':
            flux_iid = flux * self.ccd_gain * self.exposure_time
        else:
            flux_iid = flux * self.exposure_time  # if in electrons per seconds
        variance = flux_iid  # the variance of a Poisson distribution is the IID count number
        if isinstance(variance, int) or isinstance(variance, float):
            variance = max(variance, 0)
        else:
            variance[flux_iid < 0] = 0  # make sure negative pixels do not lead to variances (or nans) in the return
        noise = np.sqrt(variance) / self.exposure_time
        if self._data_count_unit == 'ADU':
            noise /= self.ccd_gain
        return noise

    @property
    def scaled_exposure_time(self):
        """
        scaled "effective" exposure time of IID counts. This can be used by lenstronomy to estimate the Poisson errors
        keeping the assumption that the counts are IIDs (even if they are not).

        :return: scaled exposure time
        """
        if self._data_count_unit == 'ADU':
            exp_time = self.ccd_gain * self.exposure_time
        else:
            exp_time = self.exposure_time
        return exp_time

    def noise_for_model(self, model, background_noise=True, poisson_noise=True, seed=None):
        """

        :param model: 2d numpy array of modelled image (with pixels in units of data specified in class)
        :param background_noise: bool, if True, adds background noise
        :param poisson_noise: bool, if True, adds Poisson noise of modelled flux
        :param seed: int, seed number to be used to render the noise properties. If None, then uses the current numpy.random seed to render the noise properties.
        :return: noise realization corresponding to the model
        """
        if seed is not None:
            g = np.random.RandomState(seed=seed)
        else:
            g = np.random
        nx, ny = np.shape(model)
        noise = np.zeros_like(model)
        if background_noise is True:
            noise += g.randn(nx, ny) * self.background_noise
        if poisson_noise is True:
            noise += g.randn(nx, ny) * self.flux_noise(model)
        return noise

    def estimate_noise(self, image):
        """

        :param image: noisy data, background subtracted
        :return: estimated noise map  sqrt(variance) for each pixel as estimated from the instrument and observation
        """
        return np.sqrt(self.background_noise**2 + data_util.flux_noise(image, self.exposure_time)**2)

    def magnitude2cps(self, magnitude):
        """
        converts an apparent magnitude to counts per second (in units of the data)

        The zero point of an instrument, by definition, is the magnitude of an object that produces one count
        (or data number, DN) per second. The magnitude of an arbitrary object producing DN counts in an observation of
        length EXPTIME is therefore:
        m = -2.5 x log10(DN / EXPTIME) + ZEROPOINT

        :param magnitude: magnitude of object
        :return: counts per second of object
        """
        # compute counts in units of ADS (as magnitude zero point is defined)
        cps = data_util.magnitude2cps(magnitude, magnitude_zero_point=self._magnitude_zero_point)
        if self._data_count_unit == 'e-':
            cps *= self.ccd_gain
        return cps
