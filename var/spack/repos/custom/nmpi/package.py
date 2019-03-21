import os
import sys

class Nmpi(Package):
    homepage = "http://www.open-mpi.org"
    url = "https://www.open-mpi.org/software/ompi/v4.0/downloads/openmpi-4.0.0.tar.bz2"
    list_url = "http://www.open-mpi.org/software/ompi/"
    git = "https://github.com/open-mpi/ompi.git"

    provides('mpi')

    depends_on('autoconf', type='build', when='@develop')
    depends_on('automake', type='build', when='@develop')
    depends_on('libtool',  type='build', when='@develop')
    depends_on('m4',       type='build', when='@develop')
    depends_on('perl',     type='build', when='@develop')

    depends_on('hwloc')
    # ompi@:3.0.0 doesn't support newer hwloc releases:
    # "configure: error: OMPI does not currently support hwloc v2 API"
    # Future ompi releases may support it, needs to be verified.
    # See #7483 for context.
    depends_on('hwloc@:1.999')

    depends_on('hwloc +cuda', when='+cuda')
    depends_on('java', when='+java')
    depends_on('sqlite', when='+sqlite3@:1.11')
    depends_on('zlib', when='@3.0.0:')
    depends_on('valgrind~mpi', when='+memchecker')
    depends_on('ucx', when='fabrics=ucx')
    depends_on('libfabric', when='fabrics=libfabric')
    depends_on('slurm', when='schedulers=slurm')
    depends_on('binutils+libiberty', when='fabrics=mxm')

    conflicts('+cuda', when='@:1.6')  # CUDA support was added in 1.7
    conflicts('fabrics=psm2', when='@:1.8')  # PSM2 support was added in 1.10.0
    conflicts('fabrics=mxm', when='@:1.5.3')  # MXM support was added in 1.5.4
    conflicts('+pmi', when='@:1.5.4')  # PMI support was added in 1.5.5
    conflicts('schedulers=slurm ~pmi', when='@1.5.4:',
              msg='+pmi is required for openmpi(>=1.5.5) to work with SLURM.')

    # filter_compiler_wrappers('openmpi/*-wrapper-data*', relative_root='share')
    conflicts('fabrics=libfabric', when='@:1.8')  # libfabric support was added in 1.10.0
    # It may be worth considering making libfabric an exclusive fabrics choice

    def url_for_version(self, version):
        url = "http://www.open-mpi.org/software/ompi/v{0}/downloads/openmpi-{1}.tar.bz2"
        return url.format(version.up_to(2), version)

    @property
    def headers(self):
        hdrs = HeaderList(find(self.prefix.include, 'mpi.h', recursive=False))
        if not hdrs:
            hdrs = HeaderList(find(self.prefix, 'mpi.h', recursive=True))
        return hdrs or None

    @property
    def libs(self):
        query_parameters = self.spec.last_query.extra_parameters
        libraries = ['libmpi', 'libmpi_mem']

        if 'cxx' in query_parameters:
            libraries = ['libmpi_cxx'] + libraries

        return find_libraries(
            libraries, root=self.prefix, shared=True, recursive=True
        )

    def setup_dependent_environment(self, spack_env, run_env, dependent_spec):
        spack_env.set('MPICC',  join_path(self.prefix.bin, 'mpincc'))
        spack_env.set('MPICXX', join_path(self.prefix.bin, 'mpinc++'))
        spack_env.set('MPIF77', join_path(self.prefix.bin, 'mpif77'))
        spack_env.set('MPIF90', join_path(self.prefix.bin, 'mpif90'))

        spack_env.set('OMPI_CC', spack_cc)
        spack_env.set('OMPI_CXX', spack_cxx)
        spack_env.set('OMPI_FC', spack_fc)
        spack_env.set('OMPI_F77', spack_f77)

    def setup_dependent_package(self, module, dependent_spec):
        self.spec.mpicc = join_path(self.prefix.bin, 'mpincc')
        self.spec.mpicxx = join_path(self.prefix.bin, 'mpinc++')
        self.spec.mpifc = join_path(self.prefix.bin, 'mpif90')
        self.spec.mpif77 = join_path(self.prefix.bin, 'mpif77')
        self.spec.mpicxx_shared_libs = [
            join_path(self.prefix.lib, 'libmpi_cxx.{0}'.format(dso_suffix)),
            join_path(self.prefix.lib, 'libmpi.{0}'.format(dso_suffix))
        ]

    def with_or_without_verbs(self, activated):
        # Up through version 1.6, this option was previously named
        # --with-openib
        opt = 'openib'
        # In version 1.7, it was renamed to be --with-verbs
        if self.spec.satisfies('@1.7:'):
            opt = 'verbs'
        # If the option has not been activated return
        # --without-openib or --without-verbs
        if not activated:
            return '--without-{0}'.format(opt)
        line = '--with-{0}'.format(opt)
        path = _verbs_dir()
        if (path is not None) and (path not in ('/usr', '/usr/local')):
            line += '={0}'.format(path)
        return line

    def with_or_without_mxm(self, activated):
        opt = 'mxm'
        # If the option has not been activated return --without-mxm
        if not activated:
            return '--without-{0}'.format(opt)
        line = '--with-{0}'.format(opt)
        path = _mxm_dir()
        if (path is not None):
            line += '={0}'.format(path)
        return line

    @run_before('autoreconf')
    def die_without_fortran(self):
        # Until we can pass variants such as +fortran through virtual
        # dependencies depends_on('mpi'), require Fortran compiler to
        # avoid delayed build errors in dependents.
        if (self.compiler.f77 is None) or (self.compiler.fc is None):
            raise InstallError(
                'OpenMPI requires both C and Fortran compilers!'
            )

    @when('@develop')
    def autoreconf(self, spec, prefix):
        perl = which('perl')
        perl('autogen.pl')

    def configure_args(self):
        spec = self.spec
        config_args = [
            '--enable-shared',
        ]

        # Add extra_rpaths dirs from compilers.yaml into link wrapper
        rpaths = [self.compiler.cc_rpath_arg + path
                  for path in self.compiler.extra_rpaths]
        config_args.extend([
            '--with-wrapper-ldflags={0}'.format(' '.join(rpaths))
        ])

        # According to this comment on github:
        #
        # https://github.com/open-mpi/ompi/issues/4338#issuecomment-383982008
        #
        # adding --enable-static silently disables slurm support via pmi/pmi2
        # for versions older than 3.0.3,3.1.3,4.0.0
        # Presumably future versions after 11/2018 should support slurm+static
        if spec.satisfies('schedulers=slurm'):
            config_args.append('--with-pmi={0}'.format(spec['slurm'].prefix))
            if spec.satisfies('@3.1.3:') or spec.satisfies('@3.0.3'):
                config_args.append('--enable-static')
        else:
            config_args.append('--enable-static')
            config_args.extend(self.with_or_without('pmi'))

        if spec.satisfies('@2.0:'):
            # for Open-MPI 2.0:, C++ bindings are disabled by default.
            config_args.extend(['--enable-mpi-cxx'])

        if spec.satisfies('@3.0.0:', strict=True):
            config_args.append('--with-zlib={0}'.format(spec['zlib'].prefix))

        # Fabrics
        config_args.extend(self.with_or_without('fabrics'))
        # Schedulers
        config_args.extend(self.with_or_without('schedulers'))

        config_args.extend(self.enable_or_disable('memchecker'))
        if spec.satisfies('+memchecker', strict=True):
            config_args.extend([
                '--enable-debug',
                '--with-valgrind={0}'.format(spec['valgrind'].prefix),
            ])

        # Hwloc support
        if spec.satisfies('@1.5.2:'):
            config_args.append('--with-hwloc={0}'.format(spec['hwloc'].prefix))

        # Java support
        if spec.satisfies('@1.7.4:'):
            if '+java' in spec:
                config_args.extend([
                    '--enable-java',
                    '--enable-mpi-java',
                    '--with-jdk-dir={0}'.format(spec['java'].home)
                ])
            else:
                config_args.extend([
                    '--disable-java',
                    '--disable-mpi-java'
                ])

        # SQLite3 support
        if spec.satisfies('@1.7.3:1.999'):
            if '+sqlite3' in spec:
                config_args.append('--with-sqlite3')
            else:
                config_args.append('--without-sqlite3')

        # VampirTrace support
        if spec.satisfies('@1.3:1.999'):
            if '+vt' not in spec:
                config_args.append('--enable-contrib-no-build=vt')

        # Multithreading support
        if spec.satisfies('@1.5.4:2.999'):
            if '+thread_multiple' in spec:
                config_args.append('--enable-mpi-thread-multiple')
            else:
                config_args.append('--disable-mpi-thread-multiple')

        # CUDA support
        # See https://www.open-mpi.org/faq/?category=buildcuda
        if spec.satisfies('@1.7:'):
            if '+cuda' in spec:
                # OpenMPI dynamically loads libcuda.so, requires dlopen
                config_args.append('--enable-dlopen')
                # Searches for header files in DIR/include
                config_args.append('--with-cuda={0}'.format(
                    spec['cuda'].prefix))
                if spec.satisfies('@1.7:1.7.2'):
                    # This option was removed from later versions
                    config_args.append('--with-cuda-libdir={0}'.format(
                        spec['cuda'].libs.directories[0]))
                if spec.satisfies('@1.7.2'):
                    # There was a bug in 1.7.2 when --enable-static is used
                    config_args.append('--enable-mca-no-build=pml-bfo')
                if spec.satisfies('%pgi^cuda@7.0:7.999'):
                    # OpenMPI has problems with CUDA 7 and PGI
                    config_args.append(
                        '--with-wrapper-cflags=-D__LP64__ -ta:tesla')
                    if spec.satisfies('%pgi@:15.8'):
                        # With PGI 15.9 and later compilers, the
                        # CFLAGS=-D__LP64__ is no longer needed.
                        config_args.append('CFLAGS=-D__LP64__')
            else:
                config_args.append('--without-cuda')

        if '+cxx_exceptions' in spec:
            config_args.append('--enable-cxx-exceptions')
        else:
            config_args.append('--disable-cxx-exceptions')
        return config_args

    @run_after('install')
    def delete_mpirun_mpiexec(self):
        # The preferred way to run an application when Slurm is the
        # scheduler is to let Slurm manage process spawning via PMI.
        #
        # Deleting the links to orterun avoids users running their
        # applications via mpirun or mpiexec, and leaves srun as the
        # only sensible choice (orterun is still present, but normal
        # users don't know about that).
        if '@1.6: ~legacylaunchers schedulers=slurm' in self.spec:
            os.remove(self.prefix.bin.mpirun)
            os.remove(self.prefix.bin.mpiexec)
            os.remove(self.prefix.bin.shmemrun)
            os.remove(self.prefix.bin.oshrun)
