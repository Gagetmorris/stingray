import numpy as np

from astropy.tests.helper import pytest

from stingray import Lightcurve
from stingray import Powerspectrum, AveragedPowerspectrum, \
    DynamicalPowerspectrum
from stingray.powerspectrum import classical_pvalue

np.random.seed(20150907)


class TestPowerspectrum(object):
    @classmethod
    def setup_class(cls):
        tstart = 0.0
        tend = 1.0
        dt = 0.0001

        time = np.arange(tstart + 0.5*dt, tend + 0.5*dt, dt)

        mean_count_rate = 100.0
        mean_counts = mean_count_rate * dt

        poisson_counts = np.random.poisson(mean_counts,
                                           size=time.shape[0])

        cls.lc = Lightcurve(time, counts=poisson_counts, dt=dt,
                            gti=[[tstart, tend]])

    def test_make_empty_periodogram(self):
        ps = Powerspectrum()
        assert ps.norm == "frac"
        assert ps.freq is None
        assert ps.power is None
        assert ps.power_err is None
        assert ps.df is None
        assert ps.m == 1
        assert ps.n is None

    def test_make_periodogram_from_lightcurve(self):
        ps = Powerspectrum(lc=self.lc)
        assert ps.freq is not None
        assert ps.power is not None
        assert ps.power_err is not None
        assert ps.df == 1.0 / self.lc.tseg
        assert ps.norm == "frac"
        assert ps.m == 1
        assert ps.n == self.lc.time.shape[0]
        assert ps.nphots == np.sum(self.lc.counts)

    def test_periodogram_types(self):
        ps = Powerspectrum(lc=self.lc)
        assert isinstance(ps.freq, np.ndarray)
        assert isinstance(ps.power, np.ndarray)
        assert isinstance(ps.power_err, np.ndarray)

    def test_init_with_lightcurve(self):
        assert Powerspectrum(self.lc)

    def test_init_without_lightcurve(self):
        with pytest.raises(TypeError):
            assert Powerspectrum(self.lc.counts)

    def test_init_with_nonsense_data(self):
        nonsense_data = [None for i in range(100)]
        with pytest.raises(TypeError):
            assert Powerspectrum(nonsense_data)

    def test_init_with_nonsense_norm(self):
        nonsense_norm = "bla"
        with pytest.raises(ValueError):
            assert Powerspectrum(self.lc, norm=nonsense_norm)

    def test_init_with_wrong_norm_type(self):
        nonsense_norm = 1.0
        with pytest.raises(TypeError):
            assert Powerspectrum(self.lc, norm=nonsense_norm)

    def test_total_variance(self):
        """
        the integral of powers (or Riemann sum) should be close
        to the variance divided by twice the length of the light curve.

        Note: make sure the factors of ncounts match!
        Also, make sure to *exclude* the zeroth power!
        """
        ps = Powerspectrum(lc=self.lc)
        nn = ps.n
        pp = ps.unnorm_power / np.float(nn) ** 2
        p_int = np.sum(pp[:-1] * ps.df) + (pp[-1] * ps.df) / 2
        var_lc = np.var(self.lc.counts) / (2. * self.lc.tseg)
        assert np.isclose(p_int, var_lc, atol=0.01, rtol=0.01)

    def test_frac_normalization_is_standard(self):
        """
        Make sure the standard normalization of a periodogram is
        rms and it stays that way!
        """
        ps = Powerspectrum(lc=self.lc)
        assert ps.norm == "frac"

    def test_frac_normalization_correct(self):
        """
        In rms normalization, the integral of the powers should be
        equal to the variance of the light curve divided by the mean
        of the light curve squared.
        """
        ps = Powerspectrum(lc=self.lc, norm="frac")
        ps_int = np.sum(ps.power[:-1] * ps.df) + ps.power[-1] * ps.df / 2
        std_lc = np.var(self.lc.counts) / np.mean(self.lc.counts) ** 2
        assert np.isclose(ps_int, std_lc, atol=0.01, rtol=0.01)

    def test_fractional_rms_in_frac_norm_is_consistent(self):
        time = np.arange(0, 100, 1) + 0.5

        poisson_counts = np.random.poisson(100.0,
                                           size=time.shape[0])

        lc = Lightcurve(time, counts=poisson_counts, dt=1,
                            gti=[[0, 100]])
        ps = Powerspectrum(lc=lc, norm="leahy")
        rms_ps_l, rms_err_l = ps.compute_rms(min_freq=ps.freq[1],
                                         max_freq=ps.freq[-1], white_noise_offset=0)

        ps = Powerspectrum(lc=lc, norm="frac")
        rms_ps, rms_err = ps.compute_rms(min_freq=ps.freq[1],
                                         max_freq=ps.freq[-1], white_noise_offset=0)
        assert np.allclose(rms_ps, rms_ps_l, atol=0.01)
        assert np.allclose(rms_err, rms_err_l, atol=0.01)

    def test_fractional_rms_in_frac_norm_is_consistent_averaged(self):
        time = np.arange(0, 400, 1) + 0.5

        poisson_counts = np.random.poisson(100.0,
                                           size=time.shape[0])

        lc = Lightcurve(time, counts=poisson_counts, dt=1,
                            gti=[[0, 400]])
        ps = AveragedPowerspectrum(lc=lc, norm="leahy", segment_size=100)
        rms_ps_l, rms_err_l = ps.compute_rms(min_freq=ps.freq[1],
                                         max_freq=ps.freq[-1], white_noise_offset=0)

        ps = AveragedPowerspectrum(lc=lc, norm="frac", segment_size=100)
        rms_ps, rms_err = ps.compute_rms(min_freq=ps.freq[1],
                                         max_freq=ps.freq[-1], white_noise_offset=0)
        assert np.allclose(rms_ps, rms_ps_l, atol=0.01)
        assert np.allclose(rms_err, rms_err_l, atol=0.01)

    def test_fractional_rms_in_frac_norm(self):
        time = np.arange(0, 400, 1) + 0.5

        poisson_counts = np.random.poisson(100.0,
                                           size=time.shape[0])

        lc = Lightcurve(time, counts=poisson_counts, dt=1,
                            gti=[[0, 400]])
        ps = AveragedPowerspectrum(lc=lc, norm="frac", segment_size=100)
        rms_ps, rms_err = ps.compute_rms(min_freq=ps.freq[1],
                                         max_freq=ps.freq[-1],
                                         white_noise_offset=0)
        rms_lc = np.std(lc.counts) / np.mean(lc.counts)
        assert np.isclose(rms_ps, rms_lc, atol=0.01)

    def test_leahy_norm_correct(self):
        time = np.linspace(0, 10.0, 1e5)
        counts = np.random.poisson(1000, size=time.shape[0])

        lc = Lightcurve(time, counts)
        ps = Powerspectrum(lc, norm="leahy")

        assert np.isclose(np.mean(ps.power[1:]), 2.0, atol=0.01, rtol=0.01)

    def test_leahy_norm_total_variance(self):
        """
        In Leahy normalization, the total variance should be the sum of
        powers multiplied by the number of counts and divided by the
        square of the number of data points in the light curve
        """
        ps = Powerspectrum(lc=self.lc, norm="Leahy")
        ps_var = (np.sum(self.lc.counts) / ps.n ** 2.) * \
                 (np.sum(ps.power[:-1]) + ps.power[-1] / 2.)

        assert np.isclose(ps_var, np.var(self.lc.counts), atol=0.01)

    def test_fractional_rms_in_leahy_norm(self):
        """
        fractional rms should only be *approximately* equal the standard
        deviation divided by the mean of the light curve. Therefore, we allow
        for a larger tolerance in np.isclose()
        """
        ps = Powerspectrum(lc=self.lc, norm="Leahy")
        rms_ps, rms_err = ps.compute_rms(min_freq=ps.freq[0],
                                         max_freq=ps.freq[-1])

        rms_lc = np.std(self.lc.counts) / np.mean(self.lc.counts)
        assert np.isclose(rms_ps, rms_lc, atol=0.01)

    def test_fractional_rms_fails_when_rms_not_leahy(self):
        with pytest.raises(Exception):
            ps = Powerspectrum(lc=self.lc, norm="rms")
            rms_ps, rms_err = ps.compute_rms(min_freq=ps.freq[0],
                                             max_freq=ps.freq[-1])

    def test_fractional_rms_error(self):
        """
        TODO: Need to write a test for the fractional rms error.
        But I don't know how!
        """
        pass

    def test_rebin_makes_right_attributes(self):
        ps = Powerspectrum(lc=self.lc, norm="Leahy")
        # replace powers
        ps.power = np.ones_like(ps.power) * 2.0

        rebin_factor = 2
        bin_ps = ps.rebin(rebin_factor*ps.df)

        assert bin_ps.freq is not None
        assert bin_ps.power is not None
        assert bin_ps.power is not None
        assert bin_ps.df == rebin_factor * 1.0 / self.lc.tseg
        assert bin_ps.norm.lower() == "leahy"
        assert bin_ps.m == 2
        assert bin_ps.n == self.lc.time.shape[0]
        assert bin_ps.nphots == np.sum(self.lc.counts)

    def test_rebin_uses_mean(self):
        """
        Make sure the rebin-method uses "mean" to average instead of summing
        powers by default, and that this is not changed in the future!
        Note: function defaults come as a tuple, so the first keyword argument
        had better be 'method'
        """
        ps = Powerspectrum(lc=self.lc, norm="Leahy")
        assert ps.rebin.__defaults__[2] == "mean"

    @pytest.mark.parametrize('df', [2, 3, 5, 1.5, 1, 85])
    def test_rebin(self, df):
        """
        TODO: Not sure how to write tests for the rebin method!
        """
        ps = Powerspectrum(lc=self.lc, norm="Leahy")
        bin_ps = ps.rebin(df)
        assert np.isclose(bin_ps.freq[1] - bin_ps.freq[0], bin_ps.df,
                          atol=1e-4, rtol=1e-4)
        assert np.isclose(bin_ps.freq[0],
                          (ps.freq[0] - ps.df * 0.5 + bin_ps.df * 0.5),
                          atol=1e-4, rtol=1e-4)

    def test_classical_significances_runs(self):
        ps = Powerspectrum(lc=self.lc, norm="Leahy")
        ps.classical_significances()

    def test_classical_significances_fails_in_rms(self):
        ps = Powerspectrum(lc=self.lc, norm="frac")
        with pytest.raises(ValueError):
            ps.classical_significances()

    def test_classical_significances_threshold(self):
        ps = Powerspectrum(lc=self.lc, norm="leahy")

        # change the powers so that just one exceeds the threshold
        ps.power = np.zeros_like(ps.power) + 2.0

        index = 1
        ps.power[index] = 10.0

        threshold = 0.01

        pval = ps.classical_significances(threshold=threshold,
                                          trial_correction=False)
        assert pval[0, 0] < threshold
        assert pval[1, 0] == index

    def test_classical_significances_trial_correction(self):
        ps = Powerspectrum(lc=self.lc, norm="leahy")
        # change the powers so that just one exceeds the threshold
        ps.power = np.zeros_like(ps.power) + 2.0
        index = 1
        ps.power[index] = 10.0
        threshold = 0.01
        pval = ps.classical_significances(threshold=threshold,
                                          trial_correction=True)
        assert np.size(pval) == 0


    def test_classical_significances_with_logbinned_psd(self):
        ps = Powerspectrum(lc=self.lc, norm="leahy")
        ps_log = ps.rebin_log()
        pval = ps_log.classical_significances(threshold=1.1, trial_correction=False)

        assert len(pval[0]) == len(ps_log.power)

    def test_pvals_is_numpy_array(self):
        ps = Powerspectrum(lc=self.lc, norm="leahy")
        # change the powers so that just one exceeds the threshold
        ps.power = np.zeros_like(ps.power) + 2.0

        index = 1
        ps.power[index] = 10.0

        threshold = 1.0

        pval = ps.classical_significances(threshold=threshold,
                                          trial_correction=True)

        assert isinstance(pval, np.ndarray)
        assert pval.shape[0] == 2


class TestAveragedPowerspectrum(object):
    @classmethod
    def setup_class(cls):
        tstart = 0.0
        tend = 10.0
        dt = 0.0001

        time = np.arange(tstart + 0.5*dt, tend + 0.5*dt, dt)

        mean_count_rate = 1000.0
        mean_counts = mean_count_rate * dt

        poisson_counts = np.random.poisson(mean_counts,
                                           size=time.shape[0])

        cls.lc = Lightcurve(time, counts=poisson_counts, gti=[[tstart, tend]],
                            dt=dt)

    def test_one_segment(self):
        segment_size = self.lc.tseg

        ps = AveragedPowerspectrum(self.lc, segment_size)
        assert np.isclose(ps.segment_size, segment_size)

    def test_make_empty_periodogram(self):
        ps = AveragedPowerspectrum()
        assert ps.norm == "frac"
        assert ps.freq is None
        assert ps.power is None
        assert ps.power_err is None
        assert ps.df is None
        assert ps.m == 1
        assert ps.n is None

    @pytest.mark.parametrize('nseg', [1, 2, 3, 5, 10, 20, 100])
    def test_n_segments(self, nseg):
        segment_size = self.lc.tseg/nseg
        ps = AveragedPowerspectrum(self.lc, segment_size)
        assert ps.m == nseg

    def test_segments_with_leftover(self):
        segment_size = self.lc.tseg / 2. - 1.
        ps = AveragedPowerspectrum(self.lc, segment_size)
        assert np.isclose(ps.segment_size, segment_size)
        assert ps.m == 2

    def test_init_without_segment(self):
        with pytest.raises(ValueError):
            assert AveragedPowerspectrum(self.lc)

    def test_init_with_nonsense_segment(self):
        segment_size = "foo"
        with pytest.raises(TypeError):
            assert AveragedPowerspectrum(self.lc, segment_size)

    def test_init_with_none_segment(self):
        segment_size = None
        with pytest.raises(ValueError):
            assert AveragedPowerspectrum(self.lc, segment_size)

    def test_init_with_inf_segment(self):
        segment_size = np.inf
        with pytest.raises(ValueError):
            assert AveragedPowerspectrum(self.lc, segment_size)

    def test_init_with_nan_segment(self):
        segment_size = np.nan
        with pytest.raises(ValueError):
            assert AveragedPowerspectrum(self.lc, segment_size)

    def test_list_of_light_curves(self):
        n_lcs = 10

        tstart = 0.0
        tend = 1.0
        dt = 0.0001

        time = np.arange(tstart + 0.5*dt, tend + 0.5*dt, dt)

        mean_count_rate = 1000.0
        mean_counts = mean_count_rate * dt

        lc_all = []
        for n in range(n_lcs):
            poisson_counts = np.random.poisson(mean_counts,
                                               size=len(time))

            lc = Lightcurve(time, counts=poisson_counts, gti=[[tstart, tend]],
                            dt=dt)
            lc_all.append(lc)

        segment_size = 0.5
        assert AveragedPowerspectrum(lc_all, segment_size)

    @pytest.mark.parametrize('df', [2, 3, 5, 1.5, 1, 85])
    def test_rebin(self, df):
        """
        TODO: Not sure how to write tests for the rebin method!
        """

        aps = AveragedPowerspectrum(lc=self.lc, segment_size=1,
                                    norm="Leahy")
        bin_aps = aps.rebin(df)
        assert np.isclose(bin_aps.freq[1]-bin_aps.freq[0], bin_aps.df,
                          atol=1e-4, rtol=1e-4)
        assert np.isclose(bin_aps.freq[0],
                          (aps.freq[0]-aps.df*0.5+bin_aps.df*0.5),
                          atol=1e-4, rtol=1e-4)

    @pytest.mark.parametrize('f', [20, 30, 50, 15, 1, 850])
    def test_rebin_factor(self, f):
        """
        TODO: Not sure how to write tests for the rebin method!
        """

        aps = AveragedPowerspectrum(lc=self.lc, segment_size=1,
                                    norm="Leahy")
        bin_aps = aps.rebin(f=f)
        assert np.isclose(bin_aps.freq[1]-bin_aps.freq[0], bin_aps.df,
                          atol=1e-4, rtol=1e-4)
        assert np.isclose(bin_aps.freq[0],
                          (aps.freq[0]-aps.df*0.5+bin_aps.df*0.5),
                          atol=1e-4, rtol=1e-4)

    @pytest.mark.parametrize('df', [0.01, 0.1])
    def test_rebin_log(self, df):
        # For now, just verify that it doesn't crash
        aps = AveragedPowerspectrum(lc=self.lc, segment_size=1,
                                    norm="Leahy")
        bin_aps = aps.rebin_log(df)

    def test_rebin_with_invalid_type_attribute(self):
        new_df = 2
        aps = AveragedPowerspectrum(lc=self.lc, segment_size=1,
                                    norm='leahy')
        aps.type = 'invalid_type'
        with pytest.raises(AttributeError):
            assert aps.rebin(df=new_df)

    def test_list_with_nonsense_component(self):
        n_lcs = 10

        tstart = 0.0
        tend = 1.0
        dt = 0.0001

        time = np.linspace(tstart, tend, int((tend - tstart) / dt))

        mean_count_rate = 1000.0
        mean_counts = mean_count_rate * dt

        lc_all = []
        for n in range(n_lcs):
            poisson_counts = np.random.poisson(mean_counts,
                                               size=len(time))

            lc = Lightcurve(time, counts=poisson_counts)
            lc_all.append(lc)

        lc_all.append(1.0)
        segment_size = 0.5

        with pytest.raises(TypeError):
            assert AveragedPowerspectrum(lc_all, segment_size)

    def test_leahy_correct_for_multiple(self):

        n = 10
        lc_all = []
        for i in range(n):
            time = np.arange(0.0, 10.0, 10. / 10000)
            counts = np.random.poisson(1000, size=time.shape[0])
            lc = Lightcurve(time, counts)
            lc_all.append(lc)

        ps = AveragedPowerspectrum(lc_all, 1.0, norm="leahy")

        assert np.isclose(np.mean(ps.power), 2.0, atol=1e-2, rtol=1e-2)
        assert np.isclose(np.std(ps.power), 2.0 / np.sqrt(n*10), atol=0.1,
                          rtol=0.1)


class TestClassicalSignificances(object):
    def test_function_runs(self):
        power = 2.0
        nspec = 1.0
        classical_pvalue(power, nspec)

    def test_power_is_not_infinite(self):
        power = np.inf
        nspec = 1
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_power_is_not_infinite2(self):
        power = -np.inf
        nspec = 1
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_power_is_non_nan(self):
        power = np.nan
        nspec = 1
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_power_is_positive(self):
        power = -2.0
        nspec = 1.0
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_nspec_is_not_infinite(self):
        power = 2.0
        nspec = np.inf
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_nspec_is_not_infinite2(self):
        power = 2.0
        nspec = -np.inf
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_nspec_is_not_nan(self):
        power = 2.0
        nspec = np.nan
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_nspec_is_positive(self):
        power = 2.0
        nspec = -1.0
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_nspec_is_nonzero(self):
        power = 2.0
        nspec = 0.0
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_nspec_is_an_integer_number(self):
        power = 2.0
        nspec = 2.5
        with pytest.raises(ValueError):
            classical_pvalue(power, nspec)

    def test_nspec_float_type_okay(self):
        power = 2.0
        nspec = 2.0
        classical_pvalue(power, nspec)

    def test_pvalue_decreases_with_increasing_power(self):
        power1 = 2.0
        power2 = 20.0
        nspec = 1.0
        pval1 = classical_pvalue(power1, nspec)
        pval2 = classical_pvalue(power2, nspec)

        assert pval1 - pval2 > 0.0

    def test_pvalue_must_decrease_with_increasing_nspec(self):
        power = 3.0
        nspec1 = 1.0
        nspec2 = 10.0

        pval1 = classical_pvalue(power, nspec1)
        pval2 = classical_pvalue(power, nspec2)

        assert pval1 - pval2 > 0.0

    def test_very_large_powers_produce_zero_prob(self):
        power = 31000.0
        nspec = 1
        pval = classical_pvalue(power, nspec)
        assert np.isclose(pval, 0.0)


class TestDynamicalPowerspectrum(object):
    def setup_class(cls):
        # generate timestamps
        timestamps = np.linspace(1, 100, 10000)
        freq = 25 + 1.2 * np.sin(2 * np.pi * timestamps / 130)
        # variability signal with drifiting frequency
        vari = 25 * np.sin(2 * np.pi * freq * timestamps)
        signal = vari + 50
        # create a lightcurve
        lc = Lightcurve(timestamps, signal, err_dist='gauss')
        cls.lc = lc

        # Simple lc to demonstrate rebinning of dyn ps
        # Simple lc to demonstrate rebinning of dyn ps
        test_times = np.arange(16)
        test_counts = [2, 3, 1, 3, 1, 5, 2, 1, 4, 2, 2, 2, 3, 4, 1, 7]
        cls.lc_test = Lightcurve(test_times, test_counts)

    def test_with_short_seg_size(self):
        with pytest.raises(ValueError):
            dps = DynamicalPowerspectrum(self.lc, segment_size=0)

    def test_with_long_seg_size(self):
        with pytest.raises(ValueError):
            dps = DynamicalPowerspectrum(self.lc, segment_size=1000)

    def test_matrix(self):
        dps = DynamicalPowerspectrum(self.lc, segment_size=3)
        nsegs = int(self.lc.tseg / dps.segment_size)
        nfreq = int((1 / self.lc.dt) / (2 * (dps.freq[1] - dps.freq[0])) -
                    (1 / self.lc.tseg))
        assert dps.dyn_ps.shape == (nfreq, nsegs)

    def test_trace_maximum_without_boundaries(self):
        dps = DynamicalPowerspectrum(self.lc, segment_size=3)
        max_pos = dps.trace_maximum()

        assert np.max(dps.freq[max_pos]) <= 1 / self.lc.dt
        assert np.min(dps.freq[max_pos]) >= 1 / dps.segment_size

    def test_trace_maximum_with_boundaries(self):
        dps = DynamicalPowerspectrum(self.lc, segment_size=3)
        minfreq = 21
        maxfreq = 24
        max_pos = dps.trace_maximum(min_freq=minfreq, max_freq=maxfreq)

        assert np.max(dps.freq[max_pos]) <= maxfreq
        assert np.min(dps.freq[max_pos]) >= minfreq

    def test_size_of_trace_maximum(self):
        dps = DynamicalPowerspectrum(self.lc, segment_size=3)
        max_pos = dps.trace_maximum()
        nsegs = int(self.lc.tseg / dps.segment_size)
        assert len(max_pos) == nsegs

    def test_rebin_small_dt(self):
        segment_size = 3
        dps = DynamicalPowerspectrum(self.lc_test, segment_size=segment_size)
        with pytest.raises(ValueError):
            dps.rebin_time(dt_new=2.0)

    def test_rebin_small_df(self):
        segment_size = 3
        dps = DynamicalPowerspectrum(self.lc, segment_size=segment_size)
        with pytest.raises(ValueError):
            dps.rebin_frequency(df_new=dps.df/2.0)

    def test_rebin_time_default_method(self):
        segment_size = 3
        dt_new = 4.0
        rebin_time = np.array([1.5, 5.5, 9.5, 13.5])
        rebin_dps = np.array([[0.7962963, 1.16402116, 0.28571429, 0.65625]])
        dps = DynamicalPowerspectrum(self.lc_test, segment_size=segment_size)
        dps.rebin_time(dt_new=dt_new)
        assert np.allclose(dps.time, rebin_time)
        assert np.allclose(dps.dyn_ps, rebin_dps)
        assert np.isclose(dps.dt, dt_new)

    def test_rebin_frequency_default_method(self):
        segment_size = 50
        df_new = 10.0
        rebin_freq = np.array([5.01000198, 15.01000198, 25.01000198,
                               35.01000198, 45.01000198])
        rebin_dps = np.array([[5.76369293e-06],
                              [7.07524761e-05],
                              [6.24846189e+00],
                              [5.77470465e-05],
                              [1.76918128e-05]])
        dps = DynamicalPowerspectrum(self.lc, segment_size=segment_size)
        dps.rebin_frequency(df_new=df_new)
        assert np.allclose(dps.freq, rebin_freq)
        assert np.allclose(dps.dyn_ps, rebin_dps)
        assert np.isclose(dps.df, df_new)

    def test_rebin_time_mean_method(self):
        segment_size = 3
        dt_new = 4.0
        rebin_time = np.array([1.5, 5.5, 9.5, 13.5])
        rebin_dps = np.array([[0.59722222, 0.87301587, 0.21428571, 0.4921875]])
        dps = DynamicalPowerspectrum(self.lc_test, segment_size=segment_size)
        dps.rebin_time(dt_new=dt_new, method='mean')
        assert np.allclose(dps.time, rebin_time)
        assert np.allclose(dps.dyn_ps, rebin_dps)
        assert np.isclose(dps.dt, dt_new)

    def test_rebin_frequency_mean_method(self):
        segment_size = 50
        df_new = 10.0
        rebin_freq = np.array([5.01000198, 15.01000198, 25.01000198,
                               35.01000198, 45.01000198])
        rebin_dps = np.array([[1.15296690e-08],
                              [1.41532979e-07],
                              [1.24993989e-02],
                              [1.15516968e-07],
                              [3.53906336e-08]])
        dps = DynamicalPowerspectrum(self.lc, segment_size=segment_size)
        dps.rebin_frequency(df_new=df_new, method="mean")
        assert np.allclose(dps.freq, rebin_freq)
        assert np.allclose(dps.dyn_ps, rebin_dps)
        assert np.isclose(dps.df, df_new)

    def test_rebin_time_average_method(self):
        segment_size = 3
        dt_new = 4.0
        rebin_time = np.array([1.5, 5.5, 9.5, 13.5])
        rebin_dps = np.array([[0.59722222, 0.87301587, 0.21428571, 0.4921875]])
        dps = DynamicalPowerspectrum(self.lc_test, segment_size=segment_size)
        dps.rebin_time(dt_new=dt_new, method='average')
        assert np.allclose(dps.time, rebin_time)
        assert np.allclose(dps.dyn_ps, rebin_dps)
        assert np.isclose(dps.dt, dt_new)

    def test_rebin_frequency_average_method(self):
        segment_size = 50
        df_new = 10.0
        rebin_freq = np.array([5.01000198, 15.01000198, 25.01000198,
                               35.01000198, 45.01000198])
        rebin_dps = np.array([[1.15296690e-08],
                              [1.41532979e-07],
                              [1.24993989e-02],
                              [1.15516968e-07],
                              [3.53906336e-08]])
        dps = DynamicalPowerspectrum(self.lc, segment_size=segment_size)
        dps.rebin_frequency(df_new=df_new, method="average")
        assert np.allclose(dps.freq, rebin_freq)
        assert np.allclose(dps.dyn_ps, rebin_dps)
        assert np.isclose(dps.df, df_new)
