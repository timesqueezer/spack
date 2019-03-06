from spack import *
import os
import platform


class HpcgNec(Package):
    """NEC version of HPCG."""

    homepage = "https://www.hpcg-benchmark.org/index.html"
    url      = "http://www.hpcg-benchmark.org/downloads/hpcg-3.0.tar.gz"

    version('3.0', sha256='e2b9bb6e0e83c3a707c27e92a6b087082e6d7033f94c000a40aebf2c05881519')

    depends_on('mpi')

    phases = ['configure', 'build', 'install']

    arch = '{0}-{1}'.format(platform.system(), platform.processor())
    build_targets = ['arch={0}'.format(arch)]

    def configure(self, spec, prefix):
        config = []

        config.extend([
            # Shell
            'SHELL        = /bin/sh',
            'CD           = cd',
            'CP           = cp',
            'LN_S         = ln -fs',
            'MKDIR        = mkdir -p',
            'RM           = /bin/rm -f',
            'TOUCH        = touch',
            # HPCG Directory Structure / HPCG library
            'TOPdir       = {0}'.format(os.getcwd()),
            'INCdir       = $(TOPdir)/src',
            'SRCdir       = $(TOPdir)/src',
            'BINdir       = $(TOPdir)/bin',
            # Message Passing library (MPI)
            'MPinc        = {0}'.format(spec['mpi'].prefix.include),
            'MPlib        = -L{0}'.format(spec['mpi'].prefix.lib),
            # HPCG includes / libraries / specifics
            'HPCG_INCLUDES = -I$(INCdir) -I$(arch) -I$(MPinc)',
            'HPCG_LIBS    = ',
            'HPCG_OPTS    = -DHPCG_NO_OPENMP',
            'HPCG_DEFS    = $(HPCG_OPTS) $(HPCG_INCLUDES)',
            # Compilers / linkers - Optimization flags
            'CXX          = {0}'.format(spec['mpi'].mpicxx),
            'CXXFLAGS      = $(HPCG_DEFS) -O3 -ffast-math -ftree-vectorize -ftree-vectorizer-verbose=0',
            'LINKER       = $(CXX)',
            'LINKFLAGS    = $(CXXFLAGS)',
            'ARCHIVER     = ar',
            'ARFLAGS      = r',
            'RANLIB       = echo'
        ])

        build_path = join_path(os.getcwd(), 'build')

        os.mkdir(build_path)

        # Write configuration options to include file
        with open('setup/Make.{0}'.format(self.arch), 'w') as makefile:
            for var in config:
                makefile.write('{0}\n'.format(var))

        configure = Executable(join_path(self.stage.source_path, 'configure'))
        with working_dir(build_path):
            configure(self.arch)

    def build(self, spec, prefix):
        build_path = join_path(os.getcwd(), 'build')
        with working_dir(build_path):
            make('arch={}'.format(self.arch))


    def install(self, spec, prefix):
        # manual install
        install_tree('build/bin', prefix.bin)

