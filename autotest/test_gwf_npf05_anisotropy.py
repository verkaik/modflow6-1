"""
MODFLOW 6 Autotest
Test to make sure that NPF anisotropy ratio options are read and processed
correctly.
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

ex = ['npf05a']
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))


def get_model(idx, dir):

    nlay, nrow, ncol = 2, 1, 5
    chdheads = [100.]
    nper = len(chdheads)
    perlen = nper * [1.]
    nstp = nper * [1]
    tsmult = nper * [1.]

    delr = delc = 1.
    strt = 100.

    nouter, ninner = 100, 300
    hclose, rclose, relax = 1e-9, 1e-3, 0.97

    tdis_rc = []
    for i in range(nper):
        tdis_rc.append((perlen[i], nstp[i], tsmult[i]))

    name = 'npf'

    # build MODFLOW 6 files
    ws = dir
    sim = flopy.mf6.MFSimulation(sim_name=name, version='mf6',
                                 exe_name='mf6',
                                 sim_ws=ws)
    # create tdis package
    tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                                 nper=nper, perioddata=tdis_rc)

    # create gwf model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name, save_flows=True)

    # create iterative model solution and register the gwf model with it
    ims = flopy.mf6.ModflowIms(sim, print_option='SUMMARY',
                               outer_hclose=hclose,
                               outer_maximum=nouter,
                               under_relaxation='DBD',
                               inner_maximum=ninner,
                               inner_hclose=hclose, rcloserecord=rclose,
                               linear_acceleration='BICGSTAB',
                               scaling_method='NONE',
                               reordering_method='NONE',
                               relaxation_factor=relax)
    sim.register_ims_package(ims, [gwf.name])

    dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                  delr=delr, delc=delc,
                                  top=100., botm=[50., 0.])

    # initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

    # node property flow
    hk = 5.
    k22 = .5
    k33 = 0.05
    k22overk = False
    k33overk = False
    aniso = True
    if aniso:
        k22 = k22 / hk
        k33 = k33 / hk
        k22overk = True
        k33overk = True
    npf = flopy.mf6.ModflowGwfnpf(gwf,
                                  k22overk=k22overk,
                                  k33overk=k33overk,
                                  save_flows=True,
                                  icelltype=0,
                                  k=hk, k22=k22, k33=k33)

    # chd files
    chdspd = {}
    for kper, chdval in enumerate(chdheads):
        chdspd[kper] = [[(0, 0, 0), 100], [(nlay - 1, 0, ncol - 1), 110.]]
    chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chdspd)

    rcha = flopy.mf6.ModflowGwfrcha(gwf, recharge=0.01)

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
    fpth = os.path.join(sim.simpath, 'npf.hds')
    hobj = flopy.utils.HeadFile(fpth, precision='double')
    heads = hobj.get_alldata()
    # answer was obtained from running problem without anistropy
    answer = [100., 100.00031999, 100.00055998, 100.00071997, 100.00079997,
              109.99960002, 109.99964002, 109.99972002, 109.99984001, 110.]
    answer = np.array(answer)
    assert np.allclose(heads.flatten(), answer)
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
