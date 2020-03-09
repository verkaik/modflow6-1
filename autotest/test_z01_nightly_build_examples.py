import os
import sys
import subprocess

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

from simulation import Simulation

# find path to modflow6-examples or modflow6-examples.git directory
home = os.path.expanduser('~')
fdir = 'modflow6-examples'
exdir = None
for root, dirs, files in os.walk(home):
    for d in dirs:
        if d.startswith(fdir):
            exdir = os.path.join(root, d, 'mf6')
            break
    if exdir is not None:
        break
testpaths = os.path.join('..', exdir)
assert os.path.isdir(testpaths)


def get_branch():
    try:
        # determine current buildstat branch
        b = subprocess.Popen(("git", "status"),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT).communicate()[0]
        if isinstance(b, bytes):
            b = b.decode('utf-8')

        # determine current buildstat branch
        for line in b.splitlines():
            if 'On branch' in line:
                branch = line.replace('On branch ', '').rstrip()
    except:
        branch = None

    return branch


def get_mf6_models():
    """
        Get a list of test models
    """
    # determine if running on travis
    is_travis = 'TRAVIS' in os.environ

    # get current branch
    if is_travis:
        branch = os.environ['BRANCH']
    else:
        branch = get_branch()
    print('On branch {}'.format(branch))

    # tuple of example files to exclude
    exclude = (None,)

    # update exclude
    if is_travis:
        exclude_travis = ('test022_MNW2_Fig28',
                          'test007_751x751_confined')
        exclude = exclude + exclude_travis
    exclude = list(exclude)

    # write a summary of the files to exclude
    print('list of tests to exclude:')
    for idx, ex in enumerate(exclude):
        print('    {}: {}'.format(idx + 1, ex))

    # build list of directories with valid example files
    dirs = [d for d in os.listdir(exdir)
            if 'test' in d and d not in exclude]

    # exclude dev examples on master or release branches
    if 'master' in branch.lower() or 'release' in branch.lower():
        drmv = []
        for d in dirs:
            if '_dev' in d.lower():
                drmv.append(d)
        for d in drmv:
            dirs.remove(d)

    # sort in numerical order for case sensitive os
    dirs = sorted(dirs, key=lambda v: (v.upper(), v[0].islower()))

    # determine if only a selection of models should be run
    select_dirs = None
    select_packages = None
    for idx, arg in enumerate(sys.argv):
        if arg.lower() == '--sim':
            if len(sys.argv) > idx + 1:
                select_dirs = sys.argv[idx + 1:]
                break
        elif arg.lower() == '--pak':
            if len(sys.argv) > idx + 1:
                select_packages = sys.argv[idx + 1:]
                select_packages = [item.upper() for item in select_packages]
                break
        elif arg.lower() == '--match':
            if len(sys.argv) > idx + 1:
                like = sys.argv[idx + 1]
                dirs = [item for item in dirs if like in item]
                break

    # determine if the selection of model is in the test models to evaluate
    if select_dirs is not None:
        found_dirs = []
        for d in select_dirs:
            if d in dirs:
                found_dirs.append(d)
        dirs = found_dirs
        if len(dirs) < 1:
            msg = 'Selected models not available in test'
            print(msg)

    # determine if the specified package(s) is in the test models to evaluate
    if select_packages is not None:
        found_dirs = []
        for d in dirs:
            pth = os.path.join(exdir, d)
            namefiles = pymake.get_namefiles(pth)
            ftypes = []
            for namefile in namefiles:
                ftype = pymake.autotest.get_mf6_ftypes(namefile,
                                                       select_packages)
                if ftype not in ftypes:
                    ftypes += ftype
            if len(ftypes) > 0:
                ftypes = [item.upper() for item in ftypes]
                for pak in select_packages:
                    if pak in ftypes:
                        found_dirs.append(d)
                        break
        dirs = found_dirs
        if len(dirs) < 1:
            msg = 'Selected packages not available ['
            for pak in select_packages:
                msg += ' {}'.format(pak)
            msg += ']'
            print(msg)

    return dirs


def run_mf6(sim):
    """
    Run the MODFLOW 6 simulation and compare to existing head file or
    appropriate MODFLOW-2005, MODFLOW-NWT, MODFLOW-USG, or MODFLOW-LGR run.

    """
    print(os.getcwd())
    src = os.path.join(exdir, sim.name)
    dst = os.path.join('temp', sim.name)
    sim.setup(src, dst)
    sim.run()
    sim.compare()
    sim.teardown()


def test_mf6model():
    # determine if test directory exists
    dirtest = dir_avail()
    if not dirtest:
        return

    # get a list of test models to run
    dirs = get_mf6_models()

    # run the test models
    for dir in dirs:
        yield run_mf6, Simulation(dir)

    return


def dir_avail():
    avail = False
    if exdir is not None:
        avail = os.path.isdir(exdir)
    if not avail:
        print('"{}" does not exist'.format(exdir))
        print('no need to run {}'.format(os.path.basename(__file__)))
    return avail


def main():
    # write message
    tnam = os.path.splitext(os.path.basename(__file__))[0]
    msg = 'Running {} test'.format(tnam)
    print(msg)

    # determine if test directory exists
    dirtest = dir_avail()
    if not dirtest:
        return

    # get a list of test models to run
    dirs = get_mf6_models()

    # run the test models
    for dir in dirs:
        sim = Simulation(dir)
        run_mf6(sim)

    return


if __name__ == "__main__":

    print('standalone run of {}'.format(os.path.basename(__file__)))

    delFiles = True
    for idx, arg in enumerate(sys.argv):
        if arg.lower() == '--keep':
            if len(sys.argv) > idx + 1:
                delFiles = False
                break

    # run main routine
    main()
