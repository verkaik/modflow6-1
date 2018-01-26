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

ex = ['dsp02']
top = [1.]
laytyp = [0]
ss = [0.]
sy = [0.1]
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))
ddir = 'data'


def build_models():
    nlay, nrow, ncol = 1, 21, 21
    nper = 1
    perlen = [5.0]
    nstp = [200]
    tsmult = [1.]
    steady = [True]
    delr = 1.
    delc = 1.
    botm = [0.]
    strt = 1.
    hnoflo = 1e30
    hdry = -1e30
    hk = 1.0

    chdlist = []
    ib = np.ones((nlay, nrow, ncol), dtype=np.int)
    ib[:, 1:nrow-1, 1:ncol-1] = 0
    idx = np.where(ib > 0)
    for k, i, j in zip(idx[0], idx[1], idx[2]):
        chdlist.append([(k, i, j), 0.])
    chdspdict = {0: chdlist}

    nouter, ninner = 100, 300
    hclose, rclose, relax = 1e-6, 1e-6, 1.

    tdis_rc = []
    for idx in range(nper):
        tdis_rc.append((perlen[idx], nstp[idx], tsmult[idx]))

    for idx, dir in enumerate(exdirs):
        name = ex[idx]

        # build MODFLOW 6 files
        ws = dir
        sim = flopy.mf6.MFSimulation(sim_name=name, version='mf6',
                                     exe_name='mf6',
                                     sim_ws=ws,
                                     sim_tdis_file='simulation.tdis')
        # create tdis package
        tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                                     nper=nper, tdisrecarray=tdis_rc)

        # create gwf model
        gwfname = 'gwf_' + name
        gwf = flopy.mf6.MFModel(sim, model_type='gwf6', model_name=gwfname,
                                model_nam_file='{}.nam'.format(gwfname),
                                ims_file_name='{}.ims'.format(gwfname))

        # create iterative model solution and register the gwf model with it
        imsgwf = flopy.mf6.ModflowIms(sim, print_option='SUMMARY',
                                      outer_hclose=hclose,
                                      outer_maximum=nouter,
                                      under_relaxation='NONE',
                                      inner_maximum=ninner,
                                      inner_hclose=hclose, rcloserecord=rclose,
                                      linear_acceleration='CG',
                                      scaling_method='NONE',
                                      reordering_method='NONE',
                                      relaxation_factor=relax,
                                      fname='{}.ims'.format(gwfname))
        sim.register_ims_package(imsgwf, [gwf.name])

        dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                      delr=delr, delc=delc,
                                      top=top[idx], botm=botm,
                                      idomain=np.ones((nlay, nrow, ncol), dtype=np.int),
                                      fname='{}.dis'.format(gwfname))

        # initial conditions
        ic = flopy.mf6.ModflowGwfic(gwf, strt=strt,
                                    fname='{}.ic'.format(gwfname))

        # node property flow
        npf = flopy.mf6.ModflowGwfnpf(gwf, save_flows=False,
                                      icelltype=laytyp[idx],
                                      k=hk,
                                      k33=hk)
        # storage
        #sto = flopy.mf6.ModflowGwfsto(gwf, save_flows=False,
        #                              iconvert=laytyp[idx],
        #                              ss=ss[idx], sy=sy[idx],
        #                              steady_state={0: True, 2: True},
        #                              transient={1: True})

        # chd files
        chd = flopy.mf6.ModflowGwfchd(gwf,
                                      periodrecarray=chdspdict,
                                      save_flows=False,
                                      pname='CHD-1')

        # output control
        oc = flopy.mf6.ModflowGwfoc(gwf,
                                    budget_filerecord='{}.cbc'.format(gwfname),
                                    head_filerecord='{}.hds'.format(gwfname),
                                    headprintrecord=[
                                        ('COLUMNS', 10, 'WIDTH', 15,
                                         'DIGITS', 6, 'GENERAL')],
                                    saverecord=[('HEAD', 'LAST')],
                                    printrecord=[('HEAD', 'LAST'),
                                                 ('BUDGET', 'LAST')])

        # create gwt model
        gwtname = 'gwt_' + name
        gwt = flopy.mf6.MFModel(sim, model_type='gwt6', model_name=gwtname,
                                model_nam_file='{}.nam'.format(gwtname),
                                ims_file_name='{}.ims'.format(gwtname))

        # create iterative model solution and register the gwt model with it
        imsgwt = flopy.mf6.ModflowIms(sim, print_option='SUMMARY',
                                      outer_hclose=hclose,
                                      outer_maximum=nouter,
                                      under_relaxation='NONE',
                                      inner_maximum=ninner,
                                      inner_hclose=hclose, rcloserecord=rclose,
                                      linear_acceleration='BICGSTAB',
                                      scaling_method='NONE',
                                      reordering_method='NONE',
                                      relaxation_factor=relax,
                                      fname='{}.ims'.format(gwtname))
        sim.register_ims_package(imsgwt, [gwt.name])

        dis = flopy.mf6.ModflowGwtdis(gwt, nlay=nlay, nrow=nrow, ncol=ncol,
                                      delr=delr, delc=delc,
                                      top=top[idx], botm=botm,
                                      idomain=1,
                                      fname='{}.dis'.format(gwtname))

        # initial conditions
        ic = flopy.mf6.ModflowGwtic(gwt, strt=0.,
                                    fname='{}.ic'.format(gwtname))

        # advection
        adv = flopy.mf6.ModflowGwtadv(gwt, scheme='UPSTREAM',
                                    fname='{}.adv'.format(gwtname))

        # advection
        dsp = flopy.mf6.ModflowGwtdsp(gwt, diffc=100.,
                                    fname='{}.dsp'.format(gwtname))

        # constant concentration
        cncs = {0: [[(0, int(nrow / 2), int(ncol / 2)), 1.0]]}
        cnc = flopy.mf6.ModflowGwtcnc(gwt,
                                      periodrecarray=cncs,
                                      save_flows=False,
                                      pname='CNC-1')

        # storage
        sto = flopy.mf6.ModflowGwtsto(gwt, porosity=0.1,
                                    fname='{}.sto'.format(gwtname))

        # sources
        #sourcerecarray = [['WEL-1, 1, CONCENTRATION']]
        #ssm = flopy.mf6.ModflowGwtssm(gwt, sourcerecarray=sourcerecarray,
        #                            fname='{}.ssm'.format(gwtname))

        # output control
        oc = flopy.mf6.ModflowGwtoc(gwt,
                                    budget_filerecord='{}.cbc'.format(gwtname),
                                    concentration_filerecord='{}.ucn'.format(gwtname),
                                    concentrationprintrecord=[
                                        ('COLUMNS', 10, 'WIDTH', 15,
                                         'DIGITS', 6, 'GENERAL')],
                                    saverecord=[('CONCENTRATION', 'LAST')],
                                    printrecord=[('CONCENTRATION', 'LAST'),
                                                 ('BUDGET', 'LAST')])

        # GWF GWT exchange
        gwfgwt = flopy.mf6.ModflowGwfgwt(sim, exgtype='GWF6-GWT6',
                                         exgmnamea=gwfname, exgmnameb=gwtname,
                                         fname='{}.gwfgwt'.format(name))

        # write MODFLOW 6 files
        sim.write_simulation()

    return


def eval_transport(sim):
    print('evaluating transport...')

    name = ex[sim.idxsim]
    gwtname = 'gwt_' + name

    fpth = os.path.join(sim.simpath, '{}.ucn'.format(gwtname))
    try:
        cobj = flopy.utils.HeadFile(fpth, precision='double',
                                    text='CONCENTRATION')
        conc = cobj.get_data()
    except:
        assert False, 'could not load data from "{}"'.format(fpth)

    # Check to make sure that the concentrations are symmetric in both the
    # up-down and left-right directions
    concud = np.flipud(conc)
    assert np.allclose(concud, conc), ('simulated concentrations are not '
                                       'symmetric in up-down direction.')

    conclr = np.fliplr(conc)
    assert np.allclose(conclr, conc), ('simulated concentrations are not '
                                       'symmetric in left-right direction.')

    return


# - No need to change any code below
def test_mf6model():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        yield test.run_mf6, Simulation(dir, exfunc=eval_transport, idxsim=idx)

    return


def main():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        sim = Simulation(dir, exfunc=eval_transport, idxsim=idx)
        test.run_mf6(sim)

    return


if __name__ == "__main__":
    # print message
    print('standalone run of {}'.format(os.path.basename(__file__)))

    # run main routine
    main()