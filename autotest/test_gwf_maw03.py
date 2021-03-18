"""
MODFLOW 6 Autotest
Test the MAW HEAD_LIMIT and RATE_SCALING options for injection wells.  These
options were not originally supported in MODFLOW 6.  They were added for
version 6.0.4.

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

ex = ['maw03a', 'maw03b', 'maw03c']
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))

# maw settings for runs a, b, and c
mawsetting_a = [(0, 'rate', 2000.), ]
mawsetting_b = [(0, 'rate', 2000.), (0, 'head_limit', 0.4)]
mawsetting_c = [(0, 'rate', 2000.), (0, 'rate_scaling', 0.0, 1.0)]
mawsettings = [mawsetting_a, mawsetting_b, mawsetting_c]

def get_model(idx, dir):

    nlay, nrow, ncol = 1, 101, 101
    nper = 1
    perlen = [1000.]
    nstp = [50]
    tsmult = [1.2]
    delr = delc = 142.
    top = 0.
    botm = [-1000.]
    strt = 0.
    hk = 10.

    nouter, ninner = 100, 100
    hclose, rclose, relax = 1e-6, 1e-6, 1.

    tdis_rc = []
    for i in range(nper):
        tdis_rc.append((perlen[i], nstp[i], tsmult[i]))

    name = ex[idx]

    # build MODFLOW 6 files
    ws = dir
    sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws)

    # create tdis package
    tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                                 nper=nper, perioddata=tdis_rc)

    # create gwf model
    gwf = flopy.mf6.MFModel(sim, model_type='gwf6', modelname=name,
                            model_nam_file='{}.nam'.format(name))

    # create iterative model solution and register the gwf model with it
    ims = flopy.mf6.ModflowIms(sim, print_option='SUMMARY',
                               outer_dvclose=hclose,
                               outer_maximum=nouter,
                               under_relaxation='NONE',
                               inner_maximum=ninner,
                               inner_dvclose=hclose, rcloserecord=rclose,
                               linear_acceleration='CG',
                               scaling_method='NONE',
                               reordering_method='NONE',
                               relaxation_factor=relax)
    sim.register_ims_package(ims, [gwf.name])

    dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                  delr=delr, delc=delc,
                                  top=top, botm=botm,
                                  idomain=1,
                                  filename='{}.dis'.format(name))

    # initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt,
                                filename='{}.ic'.format(name))

    # node property flow
    npf = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True,
                                  icelltype=1,
                                  k=hk,
                                  k33=hk,
                                  filename='{}.npf'.format(name))

    # storage
    sto = flopy.mf6.ModflowGwfsto(gwf, save_flows=True,
                                  iconvert=0,
                                  ss=1.e-5, sy=0.1,
                                  steady_state={0: False},
                                  transient={0: True},
                                  filename='{}.sto'.format(name))

    # MAW
    opth = '{}.maw.obs'.format(name)
    wellbottom = -1000
    wellrecarray = [[0, 0.15, wellbottom, 0., 'THIEM', 1]]
    wellconnectionsrecarray = [[0, 0, (0, 50, 50), 0., wellbottom, 0., 0.0]]
    wellperiodrecarray = mawsettings[idx]
    mawo_dict = {}
    mawo_dict['{}.maw.obs.csv'.format(name)] = [('m1head', 'head', (0,)),
                                                ('m1rate', 'rate', (0,))]       #is this index one-based? Not if in a tuple
    maw = flopy.mf6.ModflowGwfmaw(gwf, filename='{}.maw'.format(name),
                                  print_input=True, print_head=True,
                                  print_flows=True, save_flows=True,
                                  observations=mawo_dict,
                                  packagedata=wellrecarray,
                                  connectiondata=wellconnectionsrecarray,
                                  perioddata=wellperiodrecarray)

    # output control
    oc = flopy.mf6.ModflowGwfoc(gwf,
                                budget_filerecord='{}.cbc'.format(name),
                                head_filerecord='{}.hds'.format(name),
                                headprintrecord=[
                                    ('COLUMNS', ncol, 'WIDTH', 15,
                                     'DIGITS', 6, 'GENERAL')],
                                saverecord=[('HEAD', 'ALL')],
                                printrecord=[('HEAD', 'ALL'),
                                             ('BUDGET', 'ALL')],
                                filename='{}.oc'.format(name))

    # head observations
    obs_data0 = [('head_well_cell', 'HEAD', (0, 0, 0))]
    obs_recarray = {'{}.obs.csv'.format(name): obs_data0}
    obs = flopy.mf6.ModflowUtlobs(gwf, pname='head_obs',
                                  filename='{}.obs'.format(name),
                                  digits=15, print_input=True,
                                  continuous=obs_recarray)


    return sim


def build_models():
    for idx, dir in enumerate(exdirs):
        sim = get_model(idx, dir)
        sim.write_simulation()
    return


def eval_maw(sim):
    print('evaluating MAW heads...')

    # MODFLOW 6 maw results
    idx = sim.idxsim
    name = ex[idx]
    fpth = os.path.join(sim.simpath, '{}.maw.obs.csv'.format(name))
    try:
        tc = np.genfromtxt(fpth, names=True, delimiter=',')
    except:
        assert False, 'could not load data from "{}"'.format(fpth)


    if idx == 0:

        # M1RATE should be 2000.
        msg = 'The injection rate should be 2000. for all times'
        assert tc['M1RATE'].min() == tc['M1RATE'].max() == 2000, msg

    elif idx == 1:

        # M1RATE should have a minimum value less than 200 and
        # M1HEAD should not exceed 0.400001
        msg = ('Injection rate should fall below 200 and the head should not'
              'exceed 0.4')
        assert tc['M1RATE'].min() < 200., msg
        assert tc['M1HEAD'].max() < 0.400001, msg

    elif idx == 2:

        # M1RATE should have a minimum value less than 800
        # M1HEAD should not exceed 1.0.
        msg = ('Min injection rate should be less than 800 and well '
               'head should not exceed 1.0')
        assert tc['M1RATE'].min() < 800. and tc['M1HEAD'].max() < 1., msg

    else:

        assert False, 'Test error.  idx {} not being tested.'.format(idx)

    return


# - No need to change any code below
def test_mf6model():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        yield test.run_mf6, Simulation(dir, exfunc=eval_maw, idxsim=idx)

    return


def main():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        sim = Simulation(dir, exfunc=eval_maw, idxsim=idx)
        test.run_mf6(sim)

    return


if __name__ == "__main__":
    # print message
    print('standalone run of {}'.format(os.path.basename(__file__)))

    # run main routine
    main()
