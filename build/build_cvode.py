from pathlib import Path
from subprocess import check_call
from fmpy.util import download_file
import tarfile
import argparse


parser = argparse.ArgumentParser()
parser.add_argument(
    'platform',
    choices={'x86-windows', 'x86_64-windows', 'x86_64-linux', 'aarch64-linux', 'x86_64-darwin', 'aarch64-darwin', 'universal64-darwin'},
    help="Platform to build for, e.g. x86_64-windows"
)
parser.add_argument(
    '--cmake-generator',
    choices={'Visual Studio 17 2022', 'Visual Studio 16 2019'},
    default='Visual Studio 17 2022',
    help="CMake generator for Windows"
)
args, _ = parser.parse_known_args()

archive = download_file('https://github.com/LLNL/sundials/releases/download/v7.1.1/cvode-7.1.1.tar.gz',
                        checksum='36eb0ccea5e223ff4fbc528ef996bfb292ec8a1238019b929290ae5d444520ff')

root = Path(__file__).parent

with tarfile.open(archive) as file:
    file.extractall(root)

build_dir = root / f'cvode-{args.platform}' / 'build'

install_prefix = root / f'cvode-{args.platform}' / 'install'

cmake_args = []

fmi_platform = args.platform
fmi_architecture, fmi_system = fmi_platform.split('-')

if fmi_system == 'windows':

    cmake_args = [
        '-G', args.cmake_generator,
        '-D', 'CMAKE_POLICY_DEFAULT_CMP0091=NEW',
        '-D', 'CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded'
    ]

    if fmi_architecture == 'x86':
        cmake_args += ['-A', 'Win32']
    elif fmi_architecture == 'x86_64':
        cmake_args += ['-A', 'x64']

elif fmi_platform == 'aarch64-linux':

    toolchain_file = root / 'aarch64-linux-toolchain.cmake'
    cmake_args += ['-D', f'CMAKE_TOOLCHAIN_FILE={toolchain_file}']

elif fmi_platform == 'x86_64-darwin':

    cmake_args += ['-D', 'CMAKE_OSX_ARCHITECTURES=x86_64']

elif fmi_platform == 'aarch64-darwin':

    cmake_args += ['-D', 'CMAKE_OSX_ARCHITECTURES=arm64']

elif fmi_platform == 'universal64-darwin':

    cmake_args += ['-D', 'CMAKE_OSX_ARCHITECTURES=arm64;x86_64']

check_call(
    ['cmake'] +
    cmake_args +
    ['-B', build_dir,
    '-D', 'BUILD_SHARED_LIBS=OFF',
    '-D', 'BUILD_TESTING=OFF',
    '-D', 'EXAMPLES_INSTALL=OFF',
    '-D', 'SUNDIALS_ENABLE_ERROR_CHECKS=OFF',
    '-D', f'CMAKE_INSTALL_PREFIX={ install_prefix }',
    root / 'cvode-7.1.1']
)

check_call([
    'cmake',
    '--build', build_dir,
    '--config', 'Release',
    '--target', 'install'
])
