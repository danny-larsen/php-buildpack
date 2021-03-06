import os
import tempfile
import shutil
from nose.tools import eq_
from dingus import Dingus
from dingus import patch
from build_pack_utils import utils


class TestComposer(object):

    def __init__(self):
        self.extension_module = utils.load_extension('extensions/composer')

    def setUp(self):
        os.environ['COMPOSER_GITHUB_OAUTH_TOKEN'] = ""
        assert(os.getenv('COMPOSER_GITHUB_OAUTH_TOKEN') == "")

    def test_composer_tool_should_compile(self):
        ctx = utils.FormattedDict({
            'DOWNLOAD_URL': 'http://server/bins',
            'BUILD_DIR': 'tests/data/composer',
            'CACHE_DIR': '/cache/dir',
            'PHP_VM': 'will_default_to_php_strategy',
            'WEBDIR': 'htdocs',
            'LIBDIR': 'lib'
        })
        ct = self.extension_module.ComposerExtension(ctx)
        assert ct._should_compile()

    def test_composer_tool_should_compile_not_found(self):
        ctx = utils.FormattedDict({
            'DOWNLOAD_URL': 'http://server/bins',
            'BUILD_DIR': 'lib',
            'CACHE_DIR': '/cache/dir',
            'PHP_VM': 'will_default_to_php_strategy',
            'WEBDIR': 'htdocs',
            'LIBDIR': 'lib'
        })
        ct = self.extension_module.ComposerExtension(ctx)
        assert not ct._should_compile()

    def test_composer_tool_install(self):
        ctx = utils.FormattedDict({
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'PHP_VM': 'will_default_to_php_strategy',
            'BUILD_DIR': '/build/dir',
            'CACHE_DIR': '/cache/dir'
        })
        builder = Dingus(_ctx=ctx)
        installer = Dingus()
        cfInstaller = Dingus()
        builder.install = Dingus(_installer=cfInstaller,
                                 return_value=installer)
        ct = self.extension_module.ComposerExtension(ctx)
        ct._builder = builder
        ct.install()
        eq_(2, len(builder.install.calls()))
        # make sure PHP cli is installed
        assert installer.modules.calls().once()
        eq_('PHP', installer.modules.calls()[0].args[0])
        call = installer.modules.calls()[0]
        assert call.return_value.calls().once()
        eq_('cli', call.return_value.calls()[0].args[0])
        assert installer.calls().once()
        # make sure composer is installed
        assert installer._installer.calls().once()
        assert installer._installer.calls()[0].args[0] == \
            'http://server/bins/composer/1.0.0-alpha9/composer.phar', \
            "was %s" % installer._installer.calls()[0].args[0]

    def test_composer_tool_install_latest(self):
        ctx = utils.FormattedDict({
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'PHP_VM': 'will_default_to_php_strategy',
            'BUILD_DIR': '/build/dir',
            'CACHE_DIR': '/cache/dir',
            'COMPOSER_VERSION': 'latest'
        })
        builder = Dingus(_ctx=ctx)
        installer = Dingus()
        cfInstaller = Dingus()
        builder.install = Dingus(_installer=cfInstaller,
                                 return_value=installer)
        ct = self.extension_module.ComposerExtension(ctx)
        ct._builder = builder
        ct.install()
        eq_(2, len(builder.install.calls()))
        # make sure PHP cli is installed
        assert installer.modules.calls().once()
        eq_('PHP', installer.modules.calls()[0].args[0])
        call = installer.modules.calls()[0]
        assert call.return_value.calls().once()
        eq_('cli', call.return_value.calls()[0].args[0])
        assert installer.calls().once()
        # make sure composer is installed
        assert installer._installer.calls().once()
        assert installer._installer.calls()[0].args[0] == \
            'https://getcomposer.org/composer.phar', \
            "was %s" % installer._installer.calls()[0].args[0]
        assert installer._installer.calls()[0].args[1] == \
            'ignored', \
            "was %s" % installer._installer.calls()[0].args[1]

    def test_composer_run_streams_output(self):
        ctx = utils.FormattedDict({
            'PHP_VM': 'hhvm',  # PHP strategy does other stuff
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'BUILD_DIR': '/build/dir',
            'CACHE_DIR': '/cache/dir',
            'TMPDIR': tempfile.gettempdir(),
            'WEBDIR': 'htdocs',
            'LIBDIR': 'lib'
        })
        builder = Dingus(_ctx=ctx)
        # patch stream_output method
        old_stream_output = self.extension_module.stream_output
        co = Dingus()
        self.extension_module.stream_output = co
        try:
            ct = self.extension_module.ComposerExtension(ctx)
            ct._builder = builder
            ct.composer_runner = \
                self.extension_module.ComposerCommandRunner(ctx, builder)
            ct.run()
            assert co.calls().once()
            instCmd = co.calls()[0].args[1]
            assert instCmd.find('/build/dir/php/bin/composer.phar') > 0
            assert instCmd.find('install') > 0
            assert instCmd.find('--no-progress') > 0
            assert instCmd.find('--no-interaction') > 0
            assert instCmd.find('--no-dev') > 0
        finally:
            self.extension_module.stream_output = old_stream_output

    def test_composer_run_streams_debug_output(self):
        ctx = utils.FormattedDict({
            'PHP_VM': 'hhvm',  # PHP strategy does other stuff
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'BUILD_DIR': '/build/dir',
            'CACHE_DIR': '/cache/dir',
            'TMPDIR': tempfile.gettempdir(),
            'WEBDIR': 'htdocs',
            'LIBDIR': 'lib',
            'BP_DEBUG': 'True'
        })
        builder = Dingus(_ctx=ctx)
        # patch stream_output method
        old_stream_output = self.extension_module.stream_output
        co = Dingus()
        self.extension_module.stream_output = co
        try:
            ct = self.extension_module.ComposerExtension(ctx)
            ct._builder = builder
            ct.composer_runner = \
                self.extension_module.ComposerCommandRunner(ctx, builder)
            ct.run()
            assert 2 == len(co.calls())
            # first is called `composer -V`
            verCmd = co.calls()[0].args[1]
            assert verCmd.find('composer.phar -V')
            # then composer install
            instCmd = co.calls()[1].args[1]
            assert instCmd.find('/build/dir/php/bin/composer.phar') > 0
            assert instCmd.find('install') > 0
            assert instCmd.find('--no-progress') > 0
            assert instCmd.find('--no-interaction') > 0
            assert instCmd.find('--no-dev') > 0
        finally:
            self.extension_module.stream_output = old_stream_output

    def test_composer_tool_run_custom_composer_opts(self):
        ctx = utils.FormattedDict({
            'PHP_VM': 'php',
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'BUILD_DIR': '/build/dir',
            'CACHE_DIR': '/cache/dir',
            'TMPDIR': tempfile.gettempdir(),
            'WEBDIR': 'htdocs',
            'LIBDIR': 'lib',
            'COMPOSER_INSTALL_OPTIONS': ['--optimize-autoloader']
        })
        builder = Dingus(_ctx=ctx)
        # patch stream_output method
        old_stream_output = self.extension_module.stream_output
        co = Dingus()
        self.extension_module.stream_output = co
        # patch utils.rewrite_cfg method
        old_rewrite = self.extension_module.utils.rewrite_cfgs
        rewrite = Dingus()
        self.extension_module.utils.rewrite_cfgs = rewrite
        try:
            ct = self.extension_module.ComposerExtension(ctx)
            ct._builder = builder
            ct.composer_runner = \
                self.extension_module.ComposerCommandRunner(ctx, builder)
            ct.run()
            eq_(2, len(builder.move.calls()))
            eq_(1, len(builder.copy.calls()))
            assert rewrite.calls().once()
            rewrite_args = rewrite.calls()[0].args
            assert rewrite_args[0].endswith('php.ini')
            assert 'HOME' in rewrite_args[1]
            assert 'TMPDIR' in rewrite_args[1]
            assert co.calls().once()
            instCmd = co.calls()[0].args[1]
            assert instCmd.find('install') > 0
            assert instCmd.find('--no-progress') > 0
            assert instCmd.find('--no-interaction') == -1
            assert instCmd.find('--no-dev') == -1
            assert instCmd.find('--optimize-autoloader') > 0
        finally:
            self.extension_module.stream_output = old_stream_output
            self.extension_module.utils.rewrite_cfgs = old_rewrite

    def test_composer_tool_run_sanity_checks(self):
        context = utils.FormattedDict({
            'PHP_VM': 'php',
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'BUILD_DIR': '/build/dir',
            'CACHE_DIR': '/cache/dir',
            'TMPDIR': tempfile.gettempdir(),
            'LIBDIR': 'lib'
        })
        builder = Dingus(_ctx=context)

        # patch stream_output method
        old_stream_output = self.extension_module.stream_output
        stream_output_stub = Dingus()
        self.extension_module.stream_output = stream_output_stub

        # patch utils.rewrite_cfg method
        old_rewrite = self.extension_module.utils.rewrite_cfgs
        rewrite_stub = Dingus()
        self.extension_module.utils.rewrite_cfgs = rewrite_stub

        try:
            composer_extension = \
                self.extension_module.ComposerExtension(context)
            composer_extension._log = Dingus()
            composer_extension._builder = builder
            composer_extension.composer_runner = \
                self.extension_module.ComposerCommandRunner(context, builder)
            composer_extension.run()

            composer_extension_calls = composer_extension._log.warning.calls()
            assert len(composer_extension_calls) > 0
            assert composer_extension_calls[0].args[0].find('PROTIP:') == 0
            exists = Dingus(return_value=True)
            with patch('os.path.exists', exists):
                composer_extension._log = Dingus()
                composer_extension.run()
            assert len(exists.calls()) == 1
            assert len(composer_extension._log.warning.calls()) == 0
        finally:
            self.extension_module.stream_output = old_stream_output
            self.extension_module.utils.rewrite_cfgs = old_rewrite

    def test_process_commands(self):
        eq_(0, len(self.extension_module.preprocess_commands({
            'BUILD_DIR': '',
            'PHP_VM': ''
            })))

    def test_service_commands(self):
        eq_(0, len(self.extension_module.service_commands({
            'BUILD_DIR': '',
            'PHP_VM': ''
            })))

    def test_service_environment(self):
        eq_(0, len(self.extension_module.service_environment({
            'BUILD_DIR': '',
            'PHP_VM': ''
            })))

    def test_configure_composer_with_php_version(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': 'tests/data/composer',
            'PHP_54_LATEST': '5.4.31'
        })
        config = self.extension_module.ComposerConfiguration(ctx)
        config.configure()
        assert 'PHP_EXTENSIONS' in ctx.keys()
        assert list == type(ctx['PHP_EXTENSIONS'])
        assert 4 == len(ctx['PHP_EXTENSIONS'])
        assert 'openssl' == ctx['PHP_EXTENSIONS'][0]
        assert 'zip' == ctx['PHP_EXTENSIONS'][1]
        assert 'fileinfo' == ctx['PHP_EXTENSIONS'][2]
        assert 'gd' == ctx['PHP_EXTENSIONS'][3]
        assert '5.4.31' == ctx['PHP_VERSION']
        assert 'php' == ctx['PHP_VM']

    def test_configure_composer_with_php_version_and_base_extensions(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': 'tests/data/composer',
            'PHP_EXTENSIONS': ['a', 'b'],
            'PHP_54_LATEST': '5.4.31'
        })
        config = self.extension_module.ComposerConfiguration(ctx)
        config.configure()
        assert 'PHP_EXTENSIONS' in ctx.keys()
        assert list == type(ctx['PHP_EXTENSIONS'])
        assert 6 == len(ctx['PHP_EXTENSIONS'])
        assert 'a' == ctx['PHP_EXTENSIONS'][0]
        assert 'b' == ctx['PHP_EXTENSIONS'][1]
        assert 'openssl' == ctx['PHP_EXTENSIONS'][2]
        assert 'zip' == ctx['PHP_EXTENSIONS'][3]
        assert 'fileinfo' == ctx['PHP_EXTENSIONS'][4]
        assert 'gd' == ctx['PHP_EXTENSIONS'][5]
        assert '5.4.31' == ctx['PHP_VERSION']
        assert 'php' == ctx['PHP_VM']

    def test_configure_composer_without_php_version(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': 'tests/data/composer-no-php',
            'PHP_VERSION': '5.4.31'  # uses bp default
        })
        config = self.extension_module.ComposerConfiguration(ctx)
        config.configure()
        assert '5.4.31' == ctx['PHP_VERSION']
        assert 'php' == ctx['PHP_VM']
        assert 'PHP_EXTENSIONS' in ctx.keys()
        assert list == type(ctx['PHP_EXTENSIONS'])
        assert 3 == len(ctx['PHP_EXTENSIONS'])
        assert 'openssl' == ctx['PHP_EXTENSIONS'][0]
        assert 'zip' == ctx['PHP_EXTENSIONS'][1]
        assert 'fileinfo' == ctx['PHP_EXTENSIONS'][2]

    def test_configure_composer_with_hhvm_version(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': 'tests/data/composer-with-hhvm',
            'HHVM_VERSION': '3.2.0'
        })
        config = self.extension_module.ComposerConfiguration(ctx)
        config.configure()
        assert '3.2.0' == ctx['HHVM_VERSION']
        assert 'hhvm' == ctx['PHP_VM']

    def test_configure_does_not_run_when_no_composer_json(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': 'tests/data/app-1',
            'PHP_EXTENSIONS': ['a', 'b']
        })
        config = self.extension_module.ComposerConfiguration(ctx)
        config.configure()
        assert 'PHP_EXTENSIONS' in ctx.keys()
        assert list == type(ctx['PHP_EXTENSIONS'])
        assert 2 == len(ctx['PHP_EXTENSIONS'])
        assert 'a' in ctx['PHP_EXTENSIONS']
        assert 'b' in ctx['PHP_EXTENSIONS']
        assert 'openssl' not in ctx['PHP_EXTENSIONS']

    def test_configure_paths_missing(self):
        def fcp_test_json(path):
            tmp = fcp_orig(path)
            return (tmp[0], None)

        def fcp_test_lock(path):
            tmp = fcp_orig(path)
            return (None, tmp[1])

        def fcp_test_none(path):
            return (None, None)
        ctx = utils.FormattedDict({
            'BUILD_DIR': 'tests/data/composer',
            'PHP_54_LATEST': '5.4.31'
        })
        fcp_orig = self.extension_module.find_composer_paths
        # test when no composer.json or composer.lock files found
        self.extension_module.find_composer_paths = fcp_test_none
        try:
            self.extension_module.ComposerConfiguration(ctx).configure()
            assert 'PHP_EXTENSIONS' not in ctx.keys()
        finally:
            self.extension_module.find_composer_paths = fcp_orig
        # test when composer.json found, but no composer.lock
        self.extension_module.find_composer_paths = fcp_test_json
        try:
            self.extension_module.ComposerConfiguration(ctx).configure()
            assert 'PHP_EXTENSIONS' in ctx.keys()
            assert 3 == len(ctx['PHP_EXTENSIONS'])
            assert 'openssl' in ctx['PHP_EXTENSIONS']
            assert 'fileinfo' in ctx['PHP_EXTENSIONS']
            assert 'zip' in ctx['PHP_EXTENSIONS']
        finally:
            self.extension_module.find_composer_paths = fcp_orig
        # test when composer.lock found, but no composer.json
        self.extension_module.find_composer_paths = fcp_test_lock
        try:
            self.extension_module.ComposerConfiguration(ctx).configure()
            assert 'PHP_EXTENSIONS' in ctx.keys()
            assert 4 == len(ctx['PHP_EXTENSIONS'])
            assert 'openssl' in ctx['PHP_EXTENSIONS']
            assert 'gd' in ctx['PHP_EXTENSIONS']
            assert 'fileinfo' in ctx['PHP_EXTENSIONS']
            assert 'zip' in ctx['PHP_EXTENSIONS']
        finally:
            self.extension_module.find_composer_paths = fcp_orig

    def test_find_composer_paths(self):
        (json_path, lock_path) = \
            self.extension_module.find_composer_paths('tests')
        assert json_path is not None
        assert lock_path is not None
        eq_('tests/data/composer/composer.json', json_path)
        eq_('tests/data/composer/composer.lock', lock_path)

    def test_find_composer_paths_not_in_vendor(self):
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="test_composer-")
            vendor = os.path.join(tmpdir, 'vendor')
            utils.safe_makedirs(vendor)
            with open(os.path.join(vendor, 'composer.json'), 'wt') as fp:
                fp.write("{}")
            (json_path, lock_path) = \
                self.extension_module.find_composer_paths(tmpdir)
            assert json_path is None, "Found [%s]" % json_path
            assert lock_path is None, "Found [%s]" % lock_path
        finally:
            shutil.rmtree(tmpdir)

    def test_find_composer_php_version(self):
        ctx = {'BUILD_DIR': 'tests'}
        config = self.extension_module.ComposerConfiguration(ctx)
        php_version = config.read_version_from_composer_json('php')
        eq_('>=5.3', php_version)
        # check lock file
        php_version = config.read_version_from_composer_lock('php')
        eq_('>=5.3', php_version)

    def test_pick_php_version(self):
        ctx = {
            'PHP_VERSION': '5.4.31',
            'PHP_54_LATEST': '5.4.31',
            'BUILD_DIR': '',
            'PHP_55_LATEST': '5.5.15'
        }
        pick_php_version = \
            self.extension_module.ComposerConfiguration(ctx).pick_php_version
        # no PHP 5.3, default to 5.4
        eq_('5.4.31', pick_php_version('>=5.3'))
        eq_('5.4.31', pick_php_version('5.3.*'))
        # latest PHP 5.4 version
        eq_('5.4.31', pick_php_version('>=5.4'))
        eq_('5.4.31', pick_php_version('5.4.*'))
        # extact PHP 5.4 versions
        eq_('5.4.31', pick_php_version('5.4.31'))
        eq_('5.4.30', pick_php_version('5.4.30'))
        eq_('5.4.29', pick_php_version('5.4.29'))
        # latest PHP 5.5 version
        eq_('5.5.15', pick_php_version('>=5.5'))
        eq_('5.5.15', pick_php_version('5.5.*'))
        # exact PHP 5.5 versions
        eq_('5.5.15', pick_php_version('5.5.15'))
        eq_('5.5.14', pick_php_version('5.5.14'))
        # not understood, should default to PHP_VERSION
        eq_('5.4.31', pick_php_version(''))
        eq_('5.4.31', pick_php_version(None))
        eq_('5.4.31', pick_php_version('5.6.1'))
        eq_('5.4.31', pick_php_version('<5.5'))
        eq_('5.4.31', pick_php_version('<5.4'))

    def test_empty_platform_section(self):
        exts = self.extension_module.ComposerConfiguration({
            'BUILD_DIR': ''
        }).read_exts_from_path(
            'tests/data/composer/composer-phalcon.lock')
        eq_(2, len(exts))
        eq_('curl', exts[0])
        eq_('tokenizer', exts[1])

    def test_none_for_extension_reading(self):
        exts = self.extension_module.ComposerConfiguration({
            'BUILD_DIR': ''
        }).read_exts_from_path(None)
        eq_(0, len(exts))

    def test_with_extensions(self):
        exts = self.extension_module.ComposerConfiguration({
            'BUILD_DIR': ''
        }).read_exts_from_path(
            'tests/data/composer/composer.json')
        eq_(2, len(exts))
        eq_('zip', exts[0])
        eq_('fileinfo', exts[1])

    def test_with_oddly_formatted_composer_file(self):
        exts = self.extension_module.ComposerConfiguration({
            'BUILD_DIR': ''
        }).read_exts_from_path(
            'tests/data/composer/composer-format.json')
        eq_(1, len(exts))
        eq_('mysqli', exts[0])

    def test_composer_defaults(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/tmp/build',
            'CACHE_DIR': '/tmp/cache',
            'PHP_VM': 'will_default_to_php_strategy',
            'LIBDIR': 'lib'
        })
        ct = self.extension_module.ComposerExtension(ctx)
        eq_('/tmp/build/lib/vendor', ct._ctx['COMPOSER_VENDOR_DIR'])
        eq_('/tmp/build/php/bin', ct._ctx['COMPOSER_BIN_DIR'])
        eq_('/tmp/cache/composer', ct._ctx['COMPOSER_CACHE_DIR'])

    def test_composer_custom_values(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/tmp/build',
            'CACHE_DIR': '/tmp/cache',
            'LIBDIR': 'lib',
            'COMPOSER_VENDOR_DIR': '{BUILD_DIR}/vendor',
            'COMPOSER_BIN_DIR': '{BUILD_DIR}/bin',
            'PHP_VM': 'will_default_to_php_strategy',
            'COMPOSER_CACHE_DIR': '{CACHE_DIR}/custom'
        })
        ct = self.extension_module.ComposerExtension(ctx)
        eq_('/tmp/build/vendor', ct._ctx['COMPOSER_VENDOR_DIR'])
        eq_('/tmp/build/bin', ct._ctx['COMPOSER_BIN_DIR'])
        eq_('/tmp/cache/custom', ct._ctx['COMPOSER_CACHE_DIR'])

    def test_binary_path_for_hhvm(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome/',
            'PHP_VM': 'hhvm'
        })
        stg = self.extension_module.HHVMComposerStrategy(ctx)
        path = stg.binary_path()
        eq_('/usr/awesome/hhvm/usr/bin/hhvm', path)

    def test_binary_path_for_php(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php'
        })
        stg = self.extension_module.PHPComposerStrategy(ctx)
        path = stg.binary_path()
        eq_('/usr/awesome/php/bin/php', path)

    def test_build_composer_environment_inherits_from_ctx(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHPRC': '/usr/awesome/phpini',
            'PHP_VM': 'php',
            'TMPDIR': 'tmp',
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
            'OUR_SPECIAL_KEY': 'SPECIAL_VALUE'
        })
        oldenv = os.environ
        old_write_cfg = self.extension_module.PHPComposerStrategy.write_config
        try:
            os.environ = {'OUR_SPECIAL_KEY': 'ORIGINAL_SPECIAL_VALUE'}
            self.extension_module.PHPComposerStrategy.write_config = Dingus()

            self.extension_module.ComposerExtension(ctx)
            cr = self.extension_module.ComposerCommandRunner(ctx, None)

            built_environment = cr._build_composer_environment()
        finally:
            os.environ = oldenv
            self.extension_module.PHPComposerStrategy.write_config = \
                old_write_cfg

        assert 'OUR_SPECIAL_KEY' in built_environment, \
            'OUR_SPECIAL_KEY was not found in the built_environment variable'

    def test_build_composer_environment_sets_composer_env_vars(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/tmp/build',
            'CACHE_DIR': '/tmp/cache',
            'LIBDIR': 'lib',
            'TMPDIR': '/tmp',
            'PHP_VM': 'php'
        })

        old_write_cfg = self.extension_module.PHPComposerStrategy.write_config
        self.extension_module.PHPComposerStrategy.write_config = Dingus()

        try:
            self.extension_module.ComposerExtension(ctx)
            cr = self.extension_module.ComposerCommandRunner(ctx, None)

            built_environment = cr._build_composer_environment()
        finally:
            self.extension_module.PHPComposerStrategy.write_config = \
                old_write_cfg

        assert 'COMPOSER_VENDOR_DIR' in built_environment, \
            'Expect to find COMPOSER_VENDOR_DIR in built_environment'
        assert 'COMPOSER_BIN_DIR' in built_environment, \
            'Expect to find COMPOSER_BIN_DIR in built_environment'
        assert 'COMPOSER_CACHE_DIR' in built_environment, \
            'Expect to find COMPOSER_CACHE_DIR in built_environment'

    def test_build_composer_environment_forbids_overwriting_key_vars(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': 'tmp',
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
            'PHPRC': '/usr/awesome/phpini',
        })

        old_write_cfg = self.extension_module.PHPComposerStrategy.write_config
        self.extension_module.PHPComposerStrategy.write_config = Dingus()

        try:
            self.extension_module.ComposerExtension(ctx)
            cr = self.extension_module.ComposerCommandRunner(ctx, None)

            built_environment = cr._build_composer_environment()
        finally:
            self.extension_module.PHPComposerStrategy.write_config = \
                old_write_cfg

        eq_(built_environment['LD_LIBRARY_PATH'], '/usr/awesome/php/lib')
        eq_(built_environment['PHPRC'], 'tmp')

    def test_build_composer_environment_converts_vars_to_str(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': 'tmp',
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
            'PHPRC': '/usr/awesome/phpini',
            'MY_DICTIONARY': {'KEY': 'VALUE'},
        })

        old_write_cfg = self.extension_module.PHPComposerStrategy.write_config
        self.extension_module.PHPComposerStrategy.write_config = Dingus()

        try:
            self.extension_module.ComposerExtension(ctx)
            cr = self.extension_module.ComposerCommandRunner(ctx, None)

            built_environment = cr._build_composer_environment()
        finally:
            self.extension_module.PHPComposerStrategy.write_config = \
                old_write_cfg

        for key, val in built_environment.iteritems():
            assert type(val) == str, \
                "Expected [%s]:[%s] to be type `str`, but found type [%s]" % (
                    key, val, type(val))

    def test_build_composer_environment_has_missing_key(self):
        os.environ['SOME_KEY'] = 'does not matter'
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': 'tmp',
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
            'SOME_KEY': utils.wrap('{exact_match}')
        })
        old_write_cfg = self.extension_module.PHPComposerStrategy.write_config
        self.extension_module.PHPComposerStrategy.write_config = Dingus()

        try:
            self.extension_module.ComposerExtension(ctx)
            cr = self.extension_module.ComposerCommandRunner(ctx, None)

            try:
                built_environment = cr._build_composer_environment()
                assert "{exact_match}" == built_environment['SOME_KEY'], \
                    "value should match"
            except KeyError, e:
                assert 'exact_match' != e.message, \
                    "Should not try to evaluate value [%s]" % e
                raise
        finally:
            self.extension_module.PHPComposerStrategy.write_config = \
                old_write_cfg

    def test_build_composer_environment_no_path(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': 'tmp',
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache'
        })
        old_write_cfg = self.extension_module.PHPComposerStrategy.write_config
        self.extension_module.PHPComposerStrategy.write_config = Dingus()

        try:
            self.extension_module.ComposerExtension(ctx)
            cr = self.extension_module.ComposerCommandRunner(ctx, None)

            built_environment = cr._build_composer_environment()
        finally:
            self.extension_module.PHPComposerStrategy.write_config = \
                old_write_cfg

        assert 'PATH' in built_environment, "should have PATH set"
        assert "/usr/awesome/php/bin" == built_environment['PATH'], \
            "PATH should contain path to PHP, found [%s]" \
            % built_environment['PATH']

    def test_build_composer_environment_existing_path(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': 'tmp',
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
            'PATH': '/bin:/usr/bin'
        })
        old_write_cfg = self.extension_module.PHPComposerStrategy.write_config
        self.extension_module.PHPComposerStrategy.write_config = Dingus()

        try:
            self.extension_module.ComposerExtension(ctx)
            cr = self.extension_module.ComposerCommandRunner(ctx, None)

            built_environment = cr._build_composer_environment()
        finally:
            self.extension_module.PHPComposerStrategy.write_config = \
                old_write_cfg

        assert 'PATH' in built_environment, "should have PATH set"
        assert built_environment['PATH'].endswith(":/usr/awesome/php/bin"), \
            "PATH should contain path to PHP, found [%s]" \
            % built_environment['PATH']

    def test_ld_library_path_for_hhvm(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome/',
            'PHP_VM': 'hhvm'
        })
        stg = self.extension_module.HHVMComposerStrategy(ctx)
        path = stg.ld_library_path()
        eq_('/usr/awesome/hhvm/usr/lib/hhvm', path)

    def test_ld_library_path_for_php(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php'
        })
        stg = self.extension_module.PHPComposerStrategy(ctx)
        path = stg.ld_library_path()
        eq_('/usr/awesome/php/lib', path)

    def test_run_sets_github_oauth_token_if_present(self):
        ctx = utils.FormattedDict({
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': tempfile.gettempdir(),
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
            'COMPOSER_GITHUB_OAUTH_TOKEN': 'MADE_UP_TOKEN_VALUE'
        })

        stream_output_stub = Dingus()
        old_stream_output = self.extension_module.stream_output
        self.extension_module.stream_output = stream_output_stub

        old_rewrite = self.extension_module.utils.rewrite_cfgs
        rewrite = Dingus()
        self.extension_module.utils.rewrite_cfgs = rewrite

        old_environment = os.environ
        os.environ = {'COMPOSER_GITHUB_OAUTH_TOKEN': 'MADE_UP_TOKEN_VALUE'}

        try:
            ct = self.extension_module.ComposerExtension(ctx)

            builder_stub = Dingus(_ctx=ctx)
            ct._builder = builder_stub
            ct.composer_runner = \
                self.extension_module.ComposerCommandRunner(ctx, builder_stub)

            github_oauth_token_is_valid_stub = Dingus(
                'test_run_sets_github_oauth_token_if_present:'
                'github_oauth_token_is_valid_stub')
            github_oauth_token_is_valid_stub._set_return_value(True)
            ct._github_oauth_token_is_valid = github_oauth_token_is_valid_stub

            ct.run()

            executed_command = stream_output_stub.calls()[0].args[1]
        finally:
            self.extension_module.stream_output = old_stream_output
            self.extension_module.utils.rewrite_cfgs = old_rewrite
            os.environ = old_environment

        assert executed_command.find('config') > 0, 'did not see "config"'
        assert executed_command.find('-g') > 0, 'did not see "-g"'
        assert executed_command.find('github-oauth.github.com') > 0, \
            'did not see "github-oauth.github.com"'
        assert executed_command.find('"MADE_UP_TOKEN_VALUE"') > 0, \
            'did not see "MADE_UP_TOKEN_VALUE"'

    def test_run_does_not_set_github_oauth_if_missing(self):
        ctx = utils.FormattedDict({
            'DOWNLOAD_URL': 'http://server/bins',
            'CACHE_HASH_ALGORITHM': 'sha1',
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': tempfile.gettempdir(),
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
        })

        stream_output_stub = Dingus()
        old_stream_output = self.extension_module.stream_output
        self.extension_module.stream_output = stream_output_stub

        old_rewrite = self.extension_module.utils.rewrite_cfgs
        rewrite = Dingus()
        self.extension_module.utils.rewrite_cfgs = rewrite

        try:
            ct = self.extension_module.ComposerExtension(ctx)

            builder_stub = Dingus(_ctx=ctx)
            ct._builder = builder_stub
            ct.composer_runner = \
                self.extension_module.ComposerCommandRunner(ctx, builder_stub)

            ct.run()
        finally:
            self.extension_module.stream_output = old_stream_output
            self.extension_module.utils.rewrite_cfgs = old_rewrite

        assert stream_output_stub.calls().once(), \
            'stream_output() was called more than once'

    def test_github_oauth_token_is_valid_uses_curl(self):
        ctx = utils.FormattedDict({
            'BUILD_DIR': '/usr/awesome',
            'PHP_VM': 'php',
            'TMPDIR': tempfile.gettempdir(),
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
        })

        instance_stub = Dingus()
        instance_stub._set_return_value("""{"resources": {}}""")

        stream_output_stub = Dingus(
            'test_github_oauth_token_uses_curl : stream_output')

        with patch('StringIO.StringIO.getvalue', instance_stub):
            with patch('composer.extension.stream_output', stream_output_stub):
                ct = self.extension_module.ComposerExtension(ctx)
                ct._github_oauth_token_is_valid('MADE_UP_TOKEN_VALUE')
                executed_command = stream_output_stub.calls()[0].args[1]

        assert stream_output_stub.calls().once(), \
            'stream_output() was called more than once'
        assert executed_command.find('curl') == 0, \
            'Curl was not called, executed_command was %s' % executed_command
        assert executed_command.find(
            '-H "Authorization: token MADE_UP_TOKEN_VALUE"') > 0, \
            'No token was passed to curl. Command was: %s' % executed_command
        assert executed_command.find('https://api.github.com/rate_limit') > 0,\
            'No URL was passed to curl. Command was: %s' % executed_command

    def test_github_oauth_token_is_valid_interprets_github_api_200_as_true(self):  # noqa
        ctx = utils.FormattedDict({
            'BUILD_DIR': tempfile.gettempdir(),
            'PHP_VM': 'php',
            'TMPDIR': tempfile.gettempdir(),
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
        })

        instance_stub = Dingus()
        instance_stub._set_return_value("""{"resources": {}}""")

        stream_output_stub = Dingus(
            'test_github_oauth_token_uses_curl : stream_output')

        with patch('StringIO.StringIO.getvalue', instance_stub):
            with patch('composer.extension.stream_output', stream_output_stub):
                ct = self.extension_module.ComposerExtension(ctx)
                result = ct._github_oauth_token_is_valid('MADE_UP_TOKEN_VALUE')

        assert result is True, \
            '_github_oauth_token_is_valid returned %s, expected True' % result

    def test_github_oauth_token_is_valid_interprets_github_api_401_as_false(self):  # noqa
        ctx = utils.FormattedDict({
            'BUILD_DIR': tempfile.gettempdir(),
            'PHP_VM': 'php',
            'TMPDIR': tempfile.gettempdir(),
            'LIBDIR': 'lib',
            'CACHE_DIR': 'cache',
        })

        instance_stub = Dingus()
        instance_stub._set_return_value("""{}""")

        stream_output_stub = Dingus(
            'test_github_oauth_token_uses_curl : stream_output')

        with patch('StringIO.StringIO.getvalue', instance_stub):
            with patch('composer.extension.stream_output', stream_output_stub):
                ct = self.extension_module.ComposerExtension(ctx)
                result = ct._github_oauth_token_is_valid('MADE_UP_TOKEN_VALUE')

        assert result is False, \
            '_github_oauth_token_is_valid returned %s, expected False' % result
