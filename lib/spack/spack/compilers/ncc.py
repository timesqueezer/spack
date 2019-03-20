from spack.compiler import Compiler, get_compiler_version


class Ncc(Compiler):
    # Subclasses use possible names of C compiler
    cc_names = ['ncc']

    # Subclasses use possible names of C++ compiler
    cxx_names = ['nc++']

    # Subclasses use possible names of Fortran 77 compiler
    f77_names = ['nfort']

    # Subclasses use possible names of Fortran 90 compiler
    fc_names = ['nfort']

    # Named wrapper links within build_env_path
    link_paths = {'cc': 'ncc/ncc',
                  'cxx': 'ncc/nc++',
                  'f77': 'ncc/nfort',
                  'fc': 'ncc/nfort'}

    # PrgEnv = 'PrgEnv-ncc'
    # PrgEnv_compiler = 'ncc'

    @property
    def openmp_flag(self):
        return "-fopenmp"

    @property
    def cxx11_flag(self):
        return "-std=c++11"

    @property
    def cxx14_flag(self):
        return "-std=c++14"

    """
    @property
    def pic_flag(self):
        return "-fpic"
    """

    @classmethod
    def default_version(cls, comp):
        """Output of ``--version`` looks like this::

            ncc (NCC) 2.1.0 (Build 10:58:49 Feb  1 2019)
            Copyright (C) 2018,2019 NEC Corporation.

        on x86-64
        """
        return get_compiler_version(
            comp, '--version', r'ncc \(NCC\) (\d\.\d\.\d)')
