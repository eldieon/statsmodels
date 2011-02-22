from cStringIO import StringIO
import numpy as np

from scikits.statsmodels.iolib import SimpleTable
import scikits.statsmodels.tsa.var.util as util

mat = np.array

_default_table_fmt = dict(
    empty_cell = '',
    colsep='  ',
    row_pre = '',
    row_post = '',
    table_dec_above='=',
    table_dec_below='=',
    header_dec_below='-',
    header_fmt = '%s',
    stub_fmt = '%s',
    title_align='c',
    header_align = 'r',
    data_aligns = 'r',
    stubs_align = 'l',
    fmt = 'txt'
)

class VARSummary(object):
    default_fmt = dict(
        #data_fmts = ["%#12.6g","%#12.6g","%#10.4g","%#5.4g"],
        #data_fmts = ["%#10.4g","%#10.4g","%#10.4g","%#6.4g"],
        data_fmts = ["%#15.6F","%#15.6F","%#15.3F","%#14.3F"],
        empty_cell = '',
        #colwidths = 10,
        colsep='  ',
        row_pre = '',
        row_post = '',
        table_dec_above='=',
        table_dec_below='=',
        header_dec_below='-',
        header_fmt = '%s',
        stub_fmt = '%s',
        title_align='c',
        header_align = 'r',
        data_aligns = 'r',
        stubs_align = 'l',
        fmt = 'txt'
    )

    part1_fmt = dict(default_fmt,
        data_fmts = ["%s"],
        colwidths = 15,
        colsep=' ',
        table_dec_below='',
        header_dec_below=None,
    )
    part2_fmt = dict(default_fmt,
        data_fmts = ["%#12.6g","%#12.6g","%#10.4g","%#5.4g"],
        colwidths = None,
        colsep='    ',
        table_dec_above='-',
        table_dec_below='-',
        header_dec_below=None,
    )

    def __init__(self, estimator):
        self.model = estimator
        self.summary = self.make()

    def __repr__(self):
        return self.summary

    def make(self, endog_names=None, exog_names=None):
        """
        Summary of VAR model
        """
        buf = StringIO()

        print >> buf, self._header_table()
        print >> buf, self._stats_table()
        print >> buf, self._coef_table()
        print >> buf, self._resid_info()

        return buf.getvalue()

    def _header_table(self):
        import time

        model = self.model

        t = time.localtime()

        # TODO: change when we allow coef restrictions
        # ncoefs = len(model.beta)

        # Header information
        part1title = "Summary of Regression Results"
        part1data = [[model._model_type],
                     ["OLS"], #TODO: change when fit methods change
                     [time.strftime("%a, %d, %b, %Y", t)],
                     [time.strftime("%H:%M:%S", t)]]
        part1header = None
        part1stubs = ('Model:',
                     'Method:',
                     'Date:',
                     'Time:')
        part1 = SimpleTable(part1data, part1header, part1stubs,
                            title=part1title, txt_fmt=self.part1_fmt)

        return str(part1)

    def _stats_table(self):
        # TODO: do we want individual statistics or should users just
        # use results if wanted?
        # Handle overall fit statistics

        model = self.model


        part2Lstubs = ('No. of Equations:',
                       'Nobs:',
                       'Log likelihood:',
                       'AIC:')
        part2Rstubs = ('BIC:',
                       'HQIC:',
                       'FPE:',
                       'Det(Omega_mle):')
        part2Ldata = [[model.neqs], [model.nobs], [model.loglike], [model.aic]]
        part2Rdata = [[model.bic], [model.hqic], [model.fpe], [model.detomega]]
        part2Lheader = None
        part2L = SimpleTable(part2Ldata, part2Lheader, part2Lstubs,
                             txt_fmt = self.part2_fmt)
        part2R = SimpleTable(part2Rdata, part2Lheader, part2Rstubs,
                             txt_fmt = self.part2_fmt)
        part2L.extend_right(part2R)

        return str(part2L)

    def _coef_table(self):
        model = self.model
        k = model.neqs

        Xnames = self.model.coef_names

        data = zip(model.params.ravel(),
                   model.stderr.ravel(),
                   model.t().ravel(),
                   model.pvalues.ravel())

        header = ('coefficient','std. error','t-stat','prob')

        buf = StringIO()
        dim = k * model.p + 1
        for i in range(k):
            section = "Results for equation %s" % model.names[i]
            print >> buf, section

            table = SimpleTable(data[dim * i : dim * (i + 1)], header,
                                Xnames, title=None, txt_fmt = self.default_fmt)

            print >> buf, str(table)

            if i < k - 1: buf.write('\n')

        return buf.getvalue()

    def _resid_info(self):
        buf = StringIO()
        names = self.model.names

        resid_cov = np.cov(self.model.resid, rowvar=0)
        rdiag = np.sqrt(np.diag(resid_cov))
        resid_corr = resid_cov / np.outer(rdiag, rdiag)

        print >> buf, "Correlation matrix of residuals"
        print >> buf, pprint_matrix(resid_corr, names, names)

        return buf.getvalue()

def causality_summary(results, variables, equation, kind):
    fmt = dict(_default_table_fmt,
               data_fmts=["%#15.6F","%#15.6F","%#15.3F", "%s"])

    buf = StringIO()
    table = SimpleTable([[results['statistic'],
                          results['crit_value'],
                          results['pvalue'],
                          str(results['df'])]],
                        ['Test statistic', 'Critical Value', 'p-value',
                         'df'], [''], title=None, txt_fmt=fmt)

    print >> buf, "Granger causality %s-test" % kind
    print >> buf, table

    print >> buf, 'H_0: %s do not Granger-cause %s' % (variables, equation)

    buf.write("Conclusion: %s H_0" % results['conclusion'])
    buf.write(" at %.2f%% significance level" % (results['signif'] * 100))

    return buf.getvalue()

def print_ic_table(ics, selected_orders):
    """
    For VAR order selection

    """
    # Can factor this out into a utility method if so desired

    cols = sorted(ics)

    data = mat([["%#10.4F" % v for v in ics[c]] for c in cols],
               dtype=object).T

    # start minimums
    for i, col in enumerate(cols):
        idx = int(selected_orders[col]), i
        data[idx] = data[idx] + '*'
        # data[idx] = data[idx][:-1] + '*' # super hack, ugh

    fmt = dict(_default_table_fmt,
               data_fmts=("%s",) * len(cols))

    buf = StringIO()
    table = SimpleTable(data, cols, range(len(data)),
                        title='VAR Order Selection', txt_fmt=fmt)
    print >> buf, table
    print >> buf, '* Minimum'

    print buf.getvalue()


def pprint_matrix(values, rlabels, clabels, col_space=None):
    buf = StringIO()

    T, K = len(rlabels), len(clabels)

    if col_space is None:
        min_space = 10
        col_space = [max(len(str(c)) + 2, min_space) for c in clabels]
    else:
        col_space = (col_space,) * K

    row_space = max([len(str(x)) for x in rlabels]) + 2

    head = _pfixed('', row_space)

    for j, h in enumerate(clabels):
        head += _pfixed(h, col_space[j])

    print >> buf, head

    for i, rlab in enumerate(rlabels):
        line = ('%s' % rlab).ljust(row_space)

        for j in range(K):
            line += _pfixed(values[i,j], col_space[j])

        print >> buf, line

    return buf.getvalue()

def _pfixed(s, space, nanRep=None, float_format=None):
    if isinstance(s, float):
        if float_format:
            formatted = float_format(s)
        else:
            formatted = "%#8.6F" % s

        return formatted.rjust(space)
    else:
        return ('%s' % s)[:space].rjust(space)