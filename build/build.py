# build FMUs and fmusim for all FMI versions

import os
import shutil
import subprocess
from pathlib import Path
import argparse


parent_dir = Path(__file__).parent

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


def get_version():
    try:
        cwd = os.path.dirname(__file__)

        changed_files = subprocess.check_output(['git', 'status', '--porcelain', '--untracked=no'],
                                                cwd=cwd).decode('ascii').strip()

        if changed_files:
            return None

        version = subprocess.check_output(['git', 'tag', '--contains'], cwd=cwd).decode('ascii').strip()

        if not version:
            version = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=cwd).decode(
                'ascii').strip()

        return version
    except:
        return None


def build_fmus(fmi_version, fmi_type=None):

    if fmi_type is not None:
        build_dir = parent_dir / f'fmi{fmi_version}-{fmi_type}-{args.platform}'
    else:
        build_dir = parent_dir / f'fmi{fmi_version}-{args.platform}'

    if build_dir.exists():
        shutil.rmtree(build_dir)

    os.makedirs(build_dir)

    cmake_args = []

    version = get_version()

    if not version:
        version = 'development build'

    cmake_args += ['-D', f'FMUSIM_VERSION="{version}"']

    fmi_platform = args.platform
    fmi_architecture, fmi_system = fmi_platform.split('-')

    if fmi_system == 'windows':

        cmake_args += ['-G', args.cmake_generator]

        if fmi_architecture == 'x86':
            cmake_args += ['-A', 'Win32']
        elif fmi_architecture == 'x86_64':
            cmake_args += ['-A', 'x64']

    elif fmi_platform == 'aarch64-linux':

        toolchain_file = parent_dir / 'aarch64-linux-toolchain.cmake'
        cmake_args += ['-D', f'CMAKE_TOOLCHAIN_FILE={ toolchain_file }']

    elif fmi_platform == 'x86_64-darwin':

        cmake_args += ['-D', 'CMAKE_OSX_ARCHITECTURES=x86_64']

    elif fmi_platform == 'aarch64-darwin':

        cmake_args += ['-D', 'CMAKE_OSX_ARCHITECTURES=arm64']

    elif fmi_platform == 'universal64-darwin':
        cmake_args += ['-D', 'CMAKE_OSX_ARCHITECTURES=arm64;x86_64']

    install_dir = build_dir / 'install'

    if fmi_type is not None:
        cmake_args += ['-D', f'FMI_TYPE={fmi_type.upper()}']

    cmake_args += [
        '-D', f'CMAKE_INSTALL_PREFIX={install_dir}',
        '-D', f'FMI_VERSION={fmi_version}',
        '-D', f'FMI_ARCHITECTURE={fmi_architecture}',
        '-D', 'WITH_FMUSIM=ON',
        '-B', build_dir,
        parent_dir.parent
    ]

    subprocess.check_call(['cmake'] + cmake_args)
    subprocess.check_call(['cmake', '--build', build_dir, '--target', 'install', '--config', 'Release'])

    fmus_dir = parent_dir / 'fmus' / f'{fmi_version}.0'

    if fmi_type is not None:
        fmus_dir = fmus_dir / fmi_type

    if fmus_dir.exists():
        shutil.rmtree(fmus_dir)

    os.makedirs(fmus_dir)

    fmusim_dir = parent_dir / 'fmus' / f'fmusim-{args.platform}'

    if fmusim_dir.exists():
        shutil.rmtree(fmusim_dir)

    os.makedirs(fmusim_dir)

    for root, dirs, files in os.walk(install_dir):
        for file in files:
            if file.endswith('.fmu'):
                shutil.copyfile(src=install_dir / file, dst=fmus_dir / file)
            elif file.startswith('fmusim'):
                shutil.copyfile(src=install_dir / file, dst=fmusim_dir / file)


if __name__ == '__main__':

    if args.platform in {'x86_64-linux', 'x86-windows', 'x86_64-windows', 'x86_64-darwin', 'universal64-darwin'}:
        build_fmus(fmi_version=1, fmi_type='me')
        build_fmus(fmi_version=1, fmi_type='cs')
        build_fmus(fmi_version=2)
    if args.platform not in {'universal64-darwin'}:
        build_fmus(fmi_version=3)
