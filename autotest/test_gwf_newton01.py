import os
import sys
import numpy as np

try:
    import flopy
except:
    msg = 'Error. FloPy package is not available.\n'
    msg += 'Try installing using the following command:\n'
    msg += ' pip install flopy'
    raise Exception(msg)

from framework import testing_framework
from simulation import Simulation

ex = ['newton01']
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))
ddir = 'data'

nlay = 2
nrow, ncol = 3, 3
top = 20
botm = [10, 0]
laytyp = 1
hk = 10.
delr = delc = 1.
chdloc = [(1, i, j) for i in range(nrow) for j in range(ncol)]
chd = 7.
strt = chd

# recharge data
rch = 1.

oname = 'head_obs.csv'
obs_recarray = {oname: [('h1', 'HEAD', (0, 1, 1)),
                        ('h2', 'HEAD', (1, 1, 1))]}


def build_mf6(idx, ws):
    c6 = []
    for loc in chdloc:
        c6.append([loc, chd])
    cd6 = {0: c6}

    nper = 1
    tdis_rc = [(1., 1, 1.)]

    name = ex[idx]

    # build MODFLOW 6 files
    sim = flopy.mf6.MFSimulation(sim_name=name, version='mf6',
                                 exe_name='mf6',
                                 sim_ws=ws)
    # create tdis package
    flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                          nper=nper, perioddata=tdis_rc)

    # create iterative model solution and register the gwf model with it
    flopy.mf6.ModflowIms(sim, print_option='SUMMARY', complexity='COMPLEX',
                         inner_dvclose=1e-9, outer_dvclose=1e-9)

    # create gwf model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name,
                               save_flows=True,
                               newtonoptions='')


    flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                            delr=delr, delc=delc,
                            top=top, botm=botm)

    # initial conditions
    flopy.mf6.ModflowGwfic(gwf, strt=strt)

    # node property flow
    flopy.mf6.ModflowGwfnpf(gwf, icelltype=1, k=hk)

    # gwf observation
    flopy.mf6.ModflowUtlobs(gwf, digits=10, print_input=True,
                            continuous=obs_recarray)

    # chd files
    flopy.mf6.modflow.ModflowGwfchd(gwf, stress_period_data=cd6)

    # rch files
    flopy.mf6.modflow.ModflowGwfrcha(gwf, recharge={0: rch})

    # output control
    flopy.mf6.ModflowGwfoc(gwf,
                           budget_filerecord='{}.cbc'.format(name),
                           head_filerecord='{}.hds'.format(name),
                           headprintrecord=[('COLUMNS', 10, 'WIDTH', 15,
                                             'DIGITS', 6, 'GENERAL')],
                           saverecord=[('HEAD', 'LAST')],
                           printrecord=[('HEAD', 'LAST'),
                                        ('BUDGET', 'LAST')])

    return sim


def get_model(idx, dir):
    ws = dir
    # build mf6 with storage package but steady state stress periods
    sim = build_mf6(idx, ws)

    return sim


def build_models():
    for idx, dir in enumerate(exdirs):
        sim = get_model(idx, dir)
        sim.write_simulation()
    return


def eval_head(sim):
    print('evaluating heads...')
    fpth = os.path.join(sim.simpath, oname)
    v = np.genfromtxt(fpth, delimiter=',', names=True)

    msg = 'head in layer 1 != 8.'
    assert np.allclose(v['H1'], 8.), msg

    msg = 'head in layer 2 != 7.'
    assert np.allclose(v['H2'], 7.), msg

    return


# - No need to change any code below
def test_mf6model():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for dir in exdirs:
        yield test.run_mf6, Simulation(dir, exfunc=eval_head)

    return


def main():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for dir in exdirs:
        sim = Simulation(dir, exfunc=eval_head)
        test.run_mf6(sim)

    return


if __name__ == "__main__":
    # print message
    print('standalone run of {}'.format(os.path.basename(__file__)))

    # run main routine
    main()
