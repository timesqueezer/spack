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
            'MPinc        = /opt/nec/ve/mpi/2.0.0/include',
            'MPlib        = /opt/nec/ve/mpi/2.0.0/lib/ve',
            # HPCG includes / libraries / specifics
            'HPCG_INCLUDES = -I$(INCdir) -I$(arch) -I$(MPinc)',
            'HPCG_LIBS    = -pthread -Wl,-rpath -Wl,$(MPlib) -Wl,--enable-new-dtags -L$(MPlib) -lmpi -lmpi_mem -lrt',
            'HPCG_OPTS    = -DHPCG_NO_OPENMP',
            'HPCG_DEFS    = $(HPCG_OPTS) $(HPCG_INCLUDES) $(HPCG_LIBS)',
            # Compilers / linkers - Optimization flags
            'CXX          = /opt/nec/ve/bin/nc++',
            'CXXFLAGS     = $(HPCG_DEFS) -O3 -ffast-math',
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
            make('arch={0}'.format(self.arch))


    def install(self, spec, prefix):
        # manual install
        mkdir(prefix.bin)
        install('build/bin/xhpcg', join_path(prefix.bin, 'xhpcg-nec'))
