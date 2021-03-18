"""
MODFLOW 6 Autotest
Test to make sure that recharge is passed to the highest active layer and
verify that recharge is in the highest active layer by looking at the
individual budget terms.  For this test, there are two layers and five
columns.  The top layer is dry except for the middle cell.  Recharge is
applied to the top layer.  In the test a, IRCH is not specified.  In test b
IRCH is specified as 1, and in test c IRCH is specified as [2, 2, 1, 2, 2]
"""

import os
import sys
import numpy as np

try:
    import pymake
except:
    msg = 'Error. Pymake package is not available.\n'
    msg += 'Try installing using the following command:\n'
    msg += ' pip install https://github.com/modflowpy/pymake/zipball/master'
    raise Exception(msg)

try:
    import flopy
except:
    msg = 'Error. FloPy package is not available.\n'
    msg += 'Try installing using the following command:\n'
    msg += ' pip install flopy'
    raise Exception(msg)

from framework import testing_framework
from simulation import Simulation

ex = ['rch01a', 'rch01b', 'rch01c']
irch = [None, 0, [1, 1, 0, 1, 1]]
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))


def get_model(idx, dir):

    nlay, nrow, ncol = 2, 1, 5
    chdheads = [25.]
    nper = len(chdheads)
    perlen = nper * [0.01]
    nstp = nper * [1]
    tsmult = nper * [1.]

    delr = delc = 1.
    strt = [[[25., 25., 75., 25., 25.], [25., 25., 75., 25., 25.]]]
    strt = np.array(strt, dtype=float)

    nouter, ninner = 100, 300
    hclose, rclose, relax = 1e-9, 1e-3, 0.97

    tdis_rc = []
    for i in range(nper):
        tdis_rc.append((perlen[i], nstp[i], tsmult[i]))

    name = 'rch'

    # build MODFLOW 6 files
    ws = dir
    sim = flopy.mf6.MFSimulation(sim_name=name, version='mf6',
                                 exe_name='mf6',
                                 sim_ws=ws)
    # create tdis package
    tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                                 nper=nper, perioddata=tdis_rc)

    # set ims csv files
    csv0 = '{}.outer.ims.csv'.format(name)
    csv1 = '{}.inner.ims.csv'.format(name)

    # create iterative model solution and register the gwf model with it
    ims = flopy.mf6.ModflowIms(sim,
                               print_option='ALL',
                               csv_outer_output_filerecord=csv0,
                               csv_inner_output_filerecord=csv1,
                               outer_dvclose=hclose,
                               outer_maximum=nouter,
                               under_relaxation='DBD',
                               inner_maximum=ninner,
                               inner_dvclose=hclose, rcloserecord=rclose,
                               linear_acceleration='BICGSTAB',
                               scaling_method='NONE',
                               reordering_method='NONE',
                               relaxation_factor=relax)

    # create gwf model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name, save_flows=True)

    dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                  delr=delr, delc=delc,
                                  top=100., botm=[50., 0.])

    # initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

    # node property flow
    npf = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True,
                                  icelltype=1,
                                  k=1.0)

    sto = flopy.mf6.ModflowGwfsto(gwf, ss=1.e-5, sy=0.1)

    # chd files
    chdspd = {}
    for kper, chdval in enumerate(chdheads):
        chdspd[kper] = [[(nlay - 1, 0, 0), chdval], [(nlay - 1, 0, ncol - 1), chdval]]
    chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chdspd)

    rch = flopy.mf6.ModflowGwfrcha(gwf, recharge=0.1, irch=irch[idx])

    # output control
    oc = flopy.mf6.ModflowGwfoc(gwf,
                                budget_filerecord='{}.cbc'.format(name),
                                head_filerecord='{}.hds'.format(name),
                                headprintrecord=[
                                    ('COLUMNS', 10, 'WIDTH', 15,
                                     'DIGITS', 6, 'GENERAL')],
                                saverecord=[('HEAD', 'ALL'),
                                            ('BUDGET', 'ALL')],
                                printrecord=[('HEAD', 'ALL'),
                                             ('BUDGET', 'ALL')],
                                filename='{}.oc'.format(name))

    return sim


def build_models():
    for idx, dir in enumerate(exdirs):
        sim = get_model(idx, dir)
        sim.write_simulation()
    return


def eval_model(sim):
    print('evaluating model...')

    fpth = os.path.join(sim.simpath, 'rch.cbc')
    bobj = flopy.utils.CellBudgetFile(fpth, precision='double')
    records = bobj.get_data(text='rch')[0]

    answer = np.array([( 6, 1, 0. ), ( 7, 2, 0.1), ( 3, 3, 0.1), ( 9, 4, 0.1),
                       (10, 5, 0. )], dtype=records.dtype)
    assert np.allclose(records['node'], answer['node'])
    assert np.allclose(records['node2'], answer['node2'])
    assert np.allclose(records['q'], answer['q'])

    fpth = os.path.join(sim.simpath, 'rch.hds')
    hobj = flopy.utils.HeadFile(fpth, precision='double')
    heads = hobj.get_alldata()

    return


# - No need to change any code below
def test_mf6model():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        yield test.run_mf6, Simulation(dir, exfunc=eval_model, idxsim=idx)

    return


def main():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        sim = Simulation(dir, exfunc=eval_model, idxsim=idx)
        test.run_mf6(sim)

    return


if __name__ == "__main__":
    # print message
    print('standalone run of {}'.format(os.path.basename(__file__)))

    # run main routine
    main()
