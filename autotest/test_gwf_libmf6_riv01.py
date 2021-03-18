"""
MODFLOW 6 Autotest
Test the bmi which is used update to set the river stages to
the same values as they are in the non-bmi simulation.
"""
import os
import numpy as np
from xmipy import XmiWrapper

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
from simulation import Simulation, bmi_return

ex = ['libgwf_riv01']
exdirs = []
for s in ex:
    exdirs.append(os.path.join('temp', s))


# temporal discretization
nper = 10
tdis_rc = []
for i in range(nper):
    tdis_rc.append((1., 1, 1))

# model spatial dimensions
nlay, nrow, ncol = 1, 1, 10

# cell spacing
delr = 50.
delc = 1.
area = delr * delc

# top of the aquifer
top = 25.

# bottom of the aquifer
botm = 0.

# hydraulic conductivity
hk = 50.

# boundary heads
h1 = 11.
h2 = 11.

# build chd stress period data
chd_spd = {0: [[(0, 0, 0), h1],
               [(0, 0, ncol - 1), h2]]}

strt = np.linspace(h1, h2, num=ncol)


# solver data
nouter, ninner = 100, 300
hclose, rclose, relax = 1e-9, 1e-3, 0.97

# uniform river stage
riv_stage = 15.
riv_stage2 = 20.
riv_bot = 12.
riv_cond = 35.
riv_packname = "MYRIV"

def build_model(ws, name, riv_spd):
    sim = flopy.mf6.MFSimulation(sim_name=name,
                                 version='mf6',
                                 exe_name='mf6',
                                 sim_ws=ws,
                                 memory_print_option='all')
    # create tdis package
    tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS',
                                 nper=nper, perioddata=tdis_rc)

    # create iterative model solution and register the gwf model with it
    ims = flopy.mf6.ModflowIms(sim,
                               print_option='SUMMARY',
                               outer_dvclose=hclose,
                               outer_maximum=nouter,
                               under_relaxation='DBD',
                               inner_maximum=ninner,
                               inner_dvclose=hclose, rcloserecord=rclose,
                               linear_acceleration='BICGSTAB',
                               relaxation_factor=relax)

    # create gwf model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name, save_flows=True)

    dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                                  delr=delr, delc=delc,
                                  top=top, botm=botm)

    # initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

    # node property flow
    npf = flopy.mf6.ModflowGwfnpf(gwf, save_flows=True,
                                  icelltype=1,
                                  k=hk)
    # storage
    sto = flopy.mf6.ModflowGwfsto(gwf,
                                  save_flows=True,
                                  iconvert=1,
                                  ss=0., sy=0.2,
                                  transient={0: True})

    # chd file
    chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_spd)

    # riv package
    riv = flopy.mf6.ModflowGwfriv(gwf, stress_period_data=riv_spd, pname=riv_packname)

    # output control
    oc = flopy.mf6.ModflowGwfoc(gwf,
                                head_filerecord='{}.hds'.format(name),
                                headprintrecord=[
                                    ('COLUMNS', 10, 'WIDTH', 15,
                                     'DIGITS', 6, 'GENERAL')],
                                saverecord=[('HEAD', 'ALL')],
                                printrecord=[('HEAD', 'ALL'),
                                             ('BUDGET', 'ALL')])
    return sim


def get_model(idx, dir):
    # build MODFLOW 6 files
    ws = dir
    name = ex[idx]   
    
    # create river data
    rd = [[(0, 0, icol), riv_stage, riv_cond, riv_bot] for icol in range(1, ncol-1)]
    rd2 = [[(0, 0, icol), riv_stage2, riv_cond, riv_bot] for icol in range(1, ncol-1)]
    sim = build_model(ws, name, riv_spd={0 : rd, 5: rd2})

    # build comparison model with zeroed values   
    ws = os.path.join(dir, 'libmf6')
    rd_bmi = [[(0, 0, icol), 999.0, 999.0, 0.0] for icol in range(1, ncol-1)]
    mc = build_model(ws, name, riv_spd={0 : rd_bmi})

    return sim, mc


def build_models():
    for idx, dir in enumerate(exdirs):
        sim, mc = get_model(idx, dir)
        sim.write_simulation()
        if mc is not None:
            mc.write_simulation()
    return


def bmifunc(exe, idx, model_ws=None):
    success = False

    name = ex[idx].upper()
    init_wd = os.path.abspath(os.getcwd())
    if model_ws is not None:
        os.chdir(model_ws)

    mf6_config_file = os.path.join(model_ws, 'mfsim.nam')
    try:
        mf6 = XmiWrapper(exe)
    except Exception as e:
        print("Failed to load " + exe)
        print("with message: " + str(e))
        return bmi_return(success, model_ws)
    
    # initialize the model
    try:
        mf6.initialize(mf6_config_file)
    except:
        return bmi_return(success, model_ws)

    # time loop
    current_time = mf6.get_current_time()
    end_time = mf6.get_end_time()

    # get copy of (multi-dim) array with river parameters
    riv_tag = mf6.get_var_address("BOUND" , name, riv_packname)
    new_spd = mf6.get_value(riv_tag)
    
    # model time loop
    idx = 0
    while current_time < end_time:

        # get dt        
        dt = mf6.get_time_step()
        
        # prepare... and reads the RIV data from file!
        mf6.prepare_time_step(dt)
        
        # set the RIV data through the BMI
        if current_time < 5:
            # set columns of BOUND data (we're setting entire columns of the
            # 2D array for convenience, setting only the value for the active
            # stress period should work too)
            new_spd[:] = [riv_stage, riv_cond, riv_bot]
            mf6.set_value(riv_tag, new_spd)
        else:
            # change only stage data
            new_spd[:] = [riv_stage2, riv_cond, riv_bot]
            mf6.set_value(riv_tag, new_spd)
            
        kiter = 0
        mf6.prepare_solve(1)

        while kiter < nouter:
            has_converged = mf6.solve(1)
            kiter += 1

            if has_converged:
                msg = "Component {}".format(1) + \
                      " converged in {}".format(kiter) + " outer iterations"
                print(msg)
                break

        if not has_converged:
            return bmi_return(success, model_ws)

        # finalize time step
        mf6.finalize_solve(1)

        # finalize time step and update time
        mf6.finalize_time_step()
        current_time = mf6.get_current_time()

        # increment counter
        idx += 1

    # cleanup
    try:
        mf6.finalize()
        success = True
    except:
        return bmi_return(success, model_ws)

    if model_ws is not None:
        os.chdir(init_wd)

    # cleanup and return
    return bmi_return(success, model_ws)


# - No need to change any code below
def test_mf6model():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        yield test.run_mf6, Simulation(dir, idxsim=idx, bmifunc=bmifunc)

    return


def main():
    # initialize testing framework
    test = testing_framework()

    # build the models
    build_models()

    # run the test models
    for idx, dir in enumerate(exdirs):
        sim = Simulation(dir, idxsim=idx, bmifunc=bmifunc)
        test.run_mf6(sim)

    return


if __name__ == "__main__":
    # print message
    print('standalone run of {}'.format(os.path.basename(__file__)))

    # run main routine
    main()
