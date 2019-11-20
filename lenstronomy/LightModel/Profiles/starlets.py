__author__ = 'aymgal'

import numpy as np
import scipy.signal as scs
import scipy.ndimage.filters as scf

from lenstronomy.Util import util


class Starlets(object):
    """

    """
    param_names = ['n_scales']
    lower_limit_default = {'n_scales': 2}
    upper_limit_default = {'n_scales': 20}

    def __init__(self, thread_count=1, fast_inverse=True, second_gen=False, show_pysap_plots=False):
        self._use_pysap = self._load_pysap()
        if self._use_pysap:
            self._transf_class = self._pysap.load_transform('BsplineWaveletTransformATrousAlgorithm')
        self._thread_count = thread_count
        self._fast_inverse = fast_inverse
        self._second_gen = second_gen
        self._show_pysap_plots = show_pysap_plots

    def function(self, coeffs, n_scales):
        """return inverse starlet transform from starlet coefficients stored in amp"""
        if self._use_pysap:
            return self._inverse_transform(coeffs, n_scales)
        else:
            return self._inverse_transform_slit(coeffs)

    def decomposition(self, image, n_scales):
        """
        decomposes an image into starlet coefficients
        :return:
        """
        if self._use_pysap:
            return self._transform(image, n_scales)
        else:
            return self._transform_slit(image, n_scales)


    def spectral_norm(self, num_pix, n_scales):
        if not hasattr(self, '_spectral_norm') or n_scales != self._n_scales_cache:
            self._spectral_norm = self._compute_spectral_norm(num_pix, n_scales, num_iter=20, tol=1e-10)
            self._n_scales_cache = n_scales
        return self._spectral_norm


    def _inverse_transform(self, coeffs, n_scales):
        """performs inverse starlet transform"""
        self._check_transform_pysap(n_scales)
        if self._fast_inverse and not self._second_gen:
            # for 1st gen starlet the reconstruction can be performed by summing all scales 
            image = np.sum(coeffs, axis=0)
        else:
            coeffs = self._coeffs2pysap(coeffs)
            self._transf.analysis_data = coeffs
            result = self._transf.synthesis()
            if self._show_pysap_plots:
                result.show()
            image = result.data
        return image

    def _transform(self, image, n_scales):
        """
        decomposes an image into starlets coefficients
        """
        self._check_transform_pysap(n_scales)
        self._transf.data = image
        self._transf.analysis()
        if self._show_pysap_plots:
            self._transf.show()
        coeffs = self._transf.analysis_data
        coeffs = self._pysap2coeffs(coeffs)
        return coeffs

    def _check_transform_pysap(self, n_scales):
        if not hasattr(self, '_transf') or n_scales != self._n_scales:
            self._transf = self._transf_class(nb_scale=n_scales, verbose=False, 
                                              nb_procs=self._thread_count)
            self._n_scales = n_scales

    def _pysap2coeffs(self, coeffs):
        return np.asarray(coeffs)

    def _coeffs2pysap(self, coeffs):
        coeffs_list = []
        for i in range(coeffs.shape[0]):
            coeffs_list.append(coeffs[i, :, :])
        return coeffs_list

    def _transform_slit(self, img, n_scales, Filter='Bspline', convol2d=0):

        mode = 'nearest'
        
        lvl = n_scales-1
        sh = np.shape(img)
        if np.size(sh) == 3:
            mn = np.min(sh)
            wave = np.zeros([lvl+1, sh[1], sh[1], mn])
            for h in range(mn):
                if mn == sh[0]:
                    wave[:, :, :, h] = wave_transform(img[h,:,:], lvl+1, Filter=Filter)
                else:
                    wave[:, :, :, h] = wave_transform(img[:,:,h], lvl+1, Filter=Filter)
            return wave

        n1 = sh[1]
        n2 = sh[1]
        
        if Filter == 'Bspline':
            h = [1./16, 1./4, 3./8, 1./4, 1./16]
        else:
            h = [1./4, 1./2, 1./4]
        n = np.size(h)
        h = np.array(h)
        
        max_lvl = np.min( (lvl, int(np.log2(n2))) )
        if lvl > max_lvl:
            lvl = max_lvl
            print("Warning : lvl set to {}".format(lvl))

        c = img
        ## wavelet set of coefficients.
        wave = np.zeros((lvl+1, n1, n2))

        for i in range(lvl):
            newh = np.zeros((1, n+(n-1)*(2**i-1)))
            newh[0, np.linspace(0, np.size(newh)-1, len(h), dtype=int)] = h

            H = np.dot(newh.T, newh)

            ######Calculates c(j+1)
            ###### Line convolution
            if convol2d == 1:
                cnew = scs.convolve2d(c, H, mode='same', boundary='symm')
            else:
                cnew = scf.convolve1d(c, newh[0, :], axis=0, mode=mode)

                ###### Column convolution
                cnew = scf.convolve1d(cnew, newh[0,:],axis=1, mode=mode)

     
          
            if self._second_gen:
                ###### hoh for g; Column convolution
                if convol2d == 1:
                    hc = scs.convolve2d(cnew, H, mode='same', boundary='symm')
                else:
                    hc = scf.convolve1d(cnew, newh[0, :],axis=0, mode=mode)
     
                    ###### hoh for g; Line convolution
                    hc = scf.convolve1d(hc, newh[0, :],axis=1, mode=mode)
                
                ###### wj+1 = cj - hcj+1
                wave[i, :, :] = c - hc
                
            else:
                ###### wj+1 = cj - cj+1
                wave[i, :, :] = c - cnew


            c = cnew
         
        wave[i+1, :, :] = c

        return wave

    def _inverse_transform_slit(self, wave, convol2d=0, fast=True):
        if self._fast_inverse and not self._second_gen:
            # simply sum all scales, including the coarsest one
            return np.sum(wave, axis=0)

        mode = 'nearest'
        
        lvl, n1, n2 = np.shape(wave)
        h = np.array([1./16, 1./4, 3./8, 1./4, 1./16])
        n = np.size(h)

        cJ = np.copy(wave[lvl-1, :, :])
        

        for i in range(1, lvl):
            
            newh = np.zeros((1, n+(n-1)*(2**(lvl-1-i)-1)))
            newh[0, np.linspace(0, np.size(newh)-1, len(h), dtype=int)] = h
            H = np.dot(newh.T, newh)

            ###### Line convolution
            if convol2d == 1:
                cnew = scs.convolve2d(cJ, H, mode='same', boundary='symm')
            else:
                cnew = scf.convolve1d(cJ, newh[0, :], axis=0, mode=mode)
                ###### Column convolution
                cnew = scf.convolve1d(cnew, newh[0, :], axis=1, mode=mode)

            cJ = cnew + wave[lvl-1-i, :, :]

        return np.reshape(cJ, (n1, n2))


    def _compute_spectral_norm(self, num_pix, n_scales, num_iter=20, tol=1e-10):
        """compute spectral norm of the starlet operator"""
        operator = lambda x: self.decomposition(x, n_scales)
        inverse_operator = lambda c: self.function(c, n_scales)
        return util.spectral_norm(num_pix, operator, inverse_operator, num_iter=num_iter, tol=tol)


    def _load_pysap(self):
        try:
            import pysap
        except ImportError:
            self._pysap = None
            return False
        else:
            self._pysap = pysap
            return True