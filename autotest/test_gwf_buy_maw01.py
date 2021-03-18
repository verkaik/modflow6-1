# Test the buoyancy package and the variable density flows between maw
# and the gwf model.  This model has 4 layers with a single maw.
# The model is transient and has heads in the aquifer higher than the initial
# stage in the well.  As the model runs, the well and aquifer equalize and
# should end up at the same level.  The test ensures that the initial and
# final water volumes in the entire system are the same.  There are three
# different cases:
#  1.  No buoyancy package
#  2.  Buoyancy package with maw and aquifer density = 1000.
#  3.  Buoyancy package with maw and aquifer density = 1024.5

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

ex = ['buy_maw_01a'] #, 'buy_maw_01b', 'buy_maw_01c']
buy_on_list = [False] #, True, True]
concbuylist = [0.] #, 0., 35.]
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))


def get_model(idx, dir):
    lx = 7.
    lz = 4.
    nlay = 4
    nrow = 1
    ncol = 7
    nper = 1
    delc = 1.
    delr = lx / ncol
    delz = lz / nlay
    top = 4.
    botm = [3., 2., 1., 0.]

    perlen = [10.0]
    nstp = [50]
    tsmult = [1.]

    Kh = 1.
    Kv = 1.

    tdis_rc = []
    for i in range(nper):
        tdis_rc.append((perlen[i], nstp[i], tsmult[i]))

    nouter, ninner = 700, 10
    hclose, rclose, relax = 1e-8, 1e-6, 0.97

    name = ex[idx]

    # build MODFLOW 6 files
    ws = dir
    sim = flopy.mf6.MFSimulation(sim_name=name, version='mf6',
                                 exe_name='mf6',
                                 sim_ws=ws)
    # create tdis package
    tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                                 nper=nper, perioddata=tdis_rc)

    # create gwf model
    gwfname = 'gwf_' + name

    newtonoptions = ['NEWTON', 'UNDER_RELAXATION']
    gwf = flopy.mf6.ModflowGwf(sim, modelname=gwfname,
                               newtonoptions=newtonoptions)

    imsgwf = flopy.mf6.ModflowIms(sim, print_option='ALL',
                                  outer_dvclose=hclose,
                                  outer_maximum=nouter,
                                  under_relaxation='NONE',
                                  inner_maximum=ninner,
                                  inner_dvclose=hclose, rcloserecord=rclose,
                                  linear_acceleration='BICGSTAB',
                                  scaling_method='NONE',
                                  reordering_method='NONE',
                                  relaxation_factor=relax,
                                  filename='{}.ims'.format(gwfname))

    dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                  delr=delr, delc=delc,
                                  top=top, botm=botm)

    # initial conditions
    strt = 4.
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

    # node property flow
    npf = flopy.mf6.ModflowGwfnpf(gwf, xt3doptions=False,
                                  save_flows=True,
                                  save_specific_discharge=True,
                                  icelltype=1,
                                  k=Kh, k33=Kv)

    sto = flopy.mf6.ModflowGwfsto(gwf, sy=0.3, ss=0., iconvert=1)

    c = concbuylist[idx]
    mawdense = 1000. + 0.7 * c
    buy_on = buy_on_list[idx]
    if buy_on:
        pd = [(0, 0.7, 0., 'none', 'none')]
        buy = flopy.mf6.ModflowGwfbuy(gwf, packagedata=pd,
                                      denseref=1000.,
                                      concentration=c)

    mawradius = 0.1
    mawbottom = 0.
    mawstrt = 3.5
    mawcondeqn = 'THIEM'
    mawngwfnodes = nlay
    # <wellno> <radius> <bottom> <strt> <condeqn> <ngwfnodes>
    mawpackagedata = [[0, mawradius, mawbottom, mawstrt, mawcondeqn, mawngwfnodes, mawdense]]
    # <wellno> <icon> <cellid(ncelldim)> <scrn_top> <scrn_bot> <hk_skin> <radius_skin>
    mawconnectiondata = [[0, icon, (icon, 0, 0), top, mawbottom, -999., -999.] for icon in range(nlay)]
    # <wellno> <mawsetting>
    mawperioddata = [[0, 'STATUS', 'ACTIVE']]
    maw = flopy.mf6.ModflowGwfmaw(gwf,
                                  print_input=True,
                                  print_head=True,
                                  print_flows=True,
                                  save_flows=True,
                                  head_filerecord='{}.maw.bin'.format(gwfname),
                                  budget_filerecord='{}.maw.bud'.format(gwfname),
                                  packagedata=mawpackagedata,
                                  connectiondata=mawconnectiondata,
                                  perioddata=mawperioddata,
                                  auxiliary=['DENSITY'],
                                  pname='MAW-1',
                                  )

    # output control
    oc = flopy.mf6.ModflowGwfoc(gwf,
                                budget_filerecord='{}.cbc'.format(gwfname),
                                head_filerecord='{}.hds'.format(gwfname),
                                headprintrecord=[
                                    ('COLUMNS', 10, 'WIDTH', 15,
                                     'DIGITS', 6, 'GENERAL')],
                                saverecord=[('HEAD', 'ALL',),
                                            ('BUDGET', 'ALL',)],
                                printrecord=[('HEAD', 'ALL',),
                                             ('BUDGET', 'ALL',)])

    return sim


def build_models():
    for idx, dir in enumerate(exdirs):
        sim = get_model(idx, dir)
        sim.write_simulation()
    return


def eval_results(sim):
    print('evaluating results...')

    # calculate volume of water and make sure it is conserved
    name = ex[sim.idxsim]
    gwfname = 'gwf_' + name
    fname = gwfname + '.maw.bin'
    fname = os.path.join(sim.simpath, fname)
    assert os.path.isfile(fname)
    bobj = flopy.utils.HeadFile(fname, text='HEAD')
    stage = bobj.get_alldata().flatten()

    fname = gwfname + '.hds'
    fname = os.path.join(sim.simpath, fname)
    assert os.path.isfile(fname)
    hobj = flopy.utils.HeadFile(fname)
    head = hobj.get_alldata()

    # calculate initial volume of water in well and aquifer
    v0maw = 3.5 * np.pi * 0.1 ** 2
    v0gwf = 4 * 7 * 0.3
    v0 = v0maw + v0gwf
    top = [4., 3., 2., 1.]
    botm = [3., 2., 1., 0.]
    nlay = 4
    ncol = 7

    # calculate current volume of water in well and aquifer and compare with
    # initial volume
    for kstp, mawstage in enumerate(stage):

        vgwf = 0
        for k in range(nlay):
            for j in range(ncol):
                tp = min(head[kstp, k, 0, j], top[k])
                dz =  tp - botm[k]
                vgwf += 0.3 * max(0., dz)
        vmaw = stage[kstp] * np.pi * 0.1 ** 2
        vnow = vmaw + vgwf
        errmsg = 'kstp {}: current volume ({}) not equal initial volume ({})'.format(kstp, v0, vnow)
        assert np.allclose(v0, vnow), errmsg

    # compare the maw-gwf flows in maw budget file with the gwf-maw flows in
    # gwf budget file.  Values should be the same but reversed in sign
    fname = gwfname + '.maw.bud'
    fname = os.path.join(sim.simpath, fname)
    assert os.path.isfile(fname)
    mbud = flopy.utils.CellBudgetFile(fname, precision='double')
    maw_gwf = mbud.get_data(text='GWF')

    fname = gwfname + '.cbc'
    fname = os.path.join(sim.simpath, fname)
    assert os.path.isfile(fname)
    gbud = flopy.utils.CellBudgetFile(fname, precision='double')
    gwf_maw = gbud.get_data(text='MAW')

    assert len(maw_gwf) == len(gwf_maw), 'number of budget records not equal'

    for istp, (ra_maw, ra_gwf) in enumerate(zip(maw_gwf, gwf_maw)):
        for i in range(ra_maw.shape[0]):
            qmaw = ra_maw[i]['q']
            qgwf = ra_gwf[i]['q']
            msg = 'step {} record {} comparing qmaw with qgwf: {} {}'.format(istp, i, qmaw, qgwf)
            print(msg)
            assert np.allclose(qmaw, -qgwf), msg

    return


# - No need to change any code below
def test_mf6model():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        yield test.run_mf6, Simulation(dir, exfunc=eval_results, idxsim=idx)

    return


def main():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        sim = Simulation(dir, exfunc=eval_results, idxsim=idx)
        test.run_mf6(sim)

    return


if __name__ == "__main__":
    # print message
    print('standalone run of {}'.format(os.path.basename(__file__)))

    # run main routine
    main()
