# Get executables and build targets

# to use ifort on windows, run this
# python test000_setup.py -fc ifort

# can compile only mf6 directly using this command:
#  python -c "import test000_setup; test000_setup.test_build_modflow6()"

import os
import sys
import shutil
import pymake

from framework import running_on_CI

if running_on_CI():
    print('running on CI environment')
    os.environ['PYMAKE_DOUBLE'] = '1'

# paths to executables for  previous versions of MODFLOW
ebindir = os.path.abspath(
    os.path.join(os.path.expanduser('~'), '.local', 'bin'))
if not os.path.exists(ebindir):
    os.makedirs(ebindir)

# make sure exe extension is used on windows
eext = ''
soext = '.so'
if sys.platform.lower() == 'win32':
    eext = '.exe'
    soext = '.dll'

mfexe_pth = 'temp/mfexes'

# some flags to check for errors in the code
# add -Werror for compilation to terminate if errors are found
strict_flags = ('-Wtabs -Wline-truncation -Wunused-label '
                '-Wunused-variable -pedantic -std=f2008')


def relpath_fallback(pth):
    try:
        # throws ValueError on Windows if pth is on a different drive
        return os.path.relpath(pth)
    except ValueError:
        return os.path.abspath(pth)


def create_dir(pth):
    # remove pth directory if it exists
    if os.path.exists(pth):
        print('removing... {}'.format(os.path.abspath(pth)))
        shutil.rmtree(pth)
    # create pth directory
    print('creating... {}'.format(os.path.abspath(pth)))
    os.makedirs(pth)

    msg = 'could not create... {}'.format(os.path.abspath(pth))
    assert os.path.exists(pth), msg

    return


def build_mf6():
    pm = pymake.Pymake()
    pm.target = "mf6" + eext
    pm.srcdir = os.path.join('..', 'src')
    pm.appdir = os.path.join('..', 'bin')
    pm.include_subdirs = True
    pm.inplace = True
    pm.makeclean = True
    if pm.fc == "gfortran":
        pm.fflags = strict_flags

    # build the application
    pm.build()

    msg = '{} does not exist.'.format(pm.target)
    assert pm.returncode == 0, msg


def build_mf6_so():
    pm = pymake.Pymake(verbose=True)
    pm.target = "libmf6" + soext
    pm.srcdir = os.path.join('..', 'srcbmi')
    pm.srcdir2 = os.path.join('..', 'src')
    pm.appdir = os.path.join('..', 'bin')
    pm.excludefiles = [os.path.join(pm.srcdir2, 'mf6.f90')]
    pm.include_subdirs = True
    pm.sharedobject = True
    pm.inplace = True
    pm.makeclean = True
    if pm.fc == "gfortran":
        pm.fflags = strict_flags

    # build the application
    pm.build()

    msg = '{} does not exist.'.format(pm.target)
    assert pm.returncode == 0, msg


def build_mf5to6():
    # define default compilers
    fc = "gfortran"
    cc = None

    # determine if fortran compiler specified on the command line
    for idx, arg in enumerate(sys.argv):
        if arg == '-fc':
            fc = sys.argv[idx + 1]
            break

    # set source and target paths
    srcdir = os.path.join('..', 'utils', 'mf5to6', 'src')
    target = os.path.join('..', 'bin', 'mf5to6')
    target += eext
    extrafiles = os.path.join('..', 'utils', 'mf5to6', 'pymake',
                              'extrafiles.txt')

    # build modflow 5 to 6 converter
    pymake.main(srcdir, target, fc=fc, cc=cc, include_subdirs=True,
                extrafiles=extrafiles, inplace=True)

    msg = '{} does not exist.'.format(relpath_fallback(target))
    assert os.path.isfile(target), msg


def build_zbud6():
    pm = pymake.Pymake()
    pm.target = "zbud6" + eext
    pm.srcdir = os.path.join('..', 'utils', 'zonebudget', 'src')
    pm.appdir = os.path.join('..', 'bin')
    pm.extrafiles = os.path.join('..', 'utils', 'zonebudget', 'pymake',
                                 'extrafiles.txt')
    pm.inplace = True
    pm.makeclean = True
    if pm.fc == "gfortran":
        pm.fflags = strict_flags

    # build the application
    pm.build()

    msg = '{} does not exist.'.format(pm.target)
    assert pm.returncode == 0, msg


def test_create_dirs():
    pths = [os.path.join('..', 'bin'),
            os.path.join('temp')]

    for pth in pths:
        create_dir(pth)

    return


def test_getmfexes(verify=True):
    pymake.getmfexes(mfexe_pth, verify=verify)
    for target in os.listdir(mfexe_pth):
        srcpth = os.path.join(mfexe_pth, target)
        if os.path.isfile(srcpth):
            dstpth = os.path.join(ebindir, target)
            print('copying {} -> {}'.format(srcpth, dstpth))
            shutil.copy(srcpth, dstpth)
    return


def test_build_modflow6():
    build_mf6()


def test_build_modflow6_so():
    build_mf6_so()


def test_build_mf5to6():
    build_mf5to6()


def test_build_zbud6():
    build_zbud6()


if __name__ == "__main__":
    test_create_dirs()
    test_getmfexes(verify=False)
    test_build_modflow6()
    test_build_modflow6_so()
    test_build_mf5to6()
    test_build_zbud6()
