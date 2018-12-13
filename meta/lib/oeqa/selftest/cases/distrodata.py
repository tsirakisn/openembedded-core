from oeqa.selftest.case import OESelftestTestCase
from oeqa.utils.commands import runCmd, bitbake, get_bb_var, get_bb_vars
from oeqa.utils.decorators import testcase
from oeqa.utils.ftools import write_file
from oeqa.core.decorator.oeid import OETestID

class Distrodata(OESelftestTestCase):

    @OETestID(1902)
    def test_checkpkg(self):
        """
        Summary:     Test that upstream version checks do not regress
        Expected:    Upstream version checks should succeed except for the recipes listed in the exception list.
        Product:     oe-core
        Author:      Alexander Kanavin <alex.kanavin@gmail.com>
        """
        feature = 'INHERIT += "distrodata"\n'
        feature += 'LICENSE_FLAGS_WHITELIST += " commercial"\n'
        self.write_config(feature)
        bitbake('-c checkpkg world')

        checkpkg_result = open(os.path.join(get_bb_var("LOG_DIR"), "checkpkg.csv")).readlines()[1:]
        regressed_failures = [pkg_data[0] for pkg_data in [pkg_line.split('\t') for pkg_line in checkpkg_result] if pkg_data[11] == 'UNKNOWN_BROKEN']
        regressed_successes = [pkg_data[0] for pkg_data in [pkg_line.split('\t') for pkg_line in checkpkg_result] if pkg_data[11] == 'KNOWN_BROKEN']
        msg = ""
        if len(regressed_failures) > 0:
            msg = msg + """
The following packages failed upstream version checks. Please fix them using UPSTREAM_CHECK_URI/UPSTREAM_CHECK_REGEX
(when using tarballs) or UPSTREAM_CHECK_GITTAGREGEX (when using git). If an upstream version check cannot be performed
(for example, if upstream does not use git tags), you can set UPSTREAM_VERSION_UNKNOWN to '1' in the recipe to acknowledge
that the check cannot be performed.
""" + "\n".join(regressed_failures)
        if len(regressed_successes) > 0:
            msg = msg + """
The following packages have been checked successfully for upstream versions,
but their recipes claim otherwise by setting UPSTREAM_VERSION_UNKNOWN. Please remove that line from the recipes.
""" + "\n".join(regressed_successes)
        self.assertTrue(len(regressed_failures) == 0 and len(regressed_successes) == 0, msg)

    def test_maintainers(self):
        """
        Summary:     Test that oe-core recipes have a maintainer
        Expected:    All oe-core recipes (except a few special static/testing ones) should have a maintainer listed in maintainers.inc file.
        Product:     oe-core
        Author:      Alexander Kanavin <alex.kanavin@gmail.com>
        """
        def is_exception(pkg):
            exceptions = ["packagegroup-", "initramfs-", "systemd-machine-units", "target-sdk-provides-dummy"]
            for i in exceptions:
                 if i in pkg:
                     return True
            return False

        feature = 'require conf/distro/include/maintainers.inc\n'
        self.write_config(feature)

        with bb.tinfoil.Tinfoil() as tinfoil:
            tinfoil.prepare(config_only=False)

            with_maintainer_list = []
            no_maintainer_list = []
            # We could have used all_recipes() here, but this method will find
            # every recipe if we ever move to setting RECIPE_MAINTAINER in recipe files
            # instead of maintainers.inc
            for fn in tinfoil.all_recipe_files(variants=False):
                if not '/meta/recipes-' in fn:
                    # We are only interested in OE-Core
                    continue
                rd = tinfoil.parse_recipe_file(fn, appends=False)
                pn = rd.getVar('PN')
                if is_exception(pn):
                    continue
                if rd.getVar('RECIPE_MAINTAINER'):
                    with_maintainer_list.append((pn, fn))
                else:
                    no_maintainer_list.append((pn, fn))

        if no_maintainer_list:
            self.fail("""
The following recipes do not have a maintainer assigned to them. Please add an entry to meta/conf/distro/include/maintainers.inc file.
""" + "\n".join(['%s (%s)' % i for i in no_maintainer_list]))

        if not with_maintainer_list:
            self.fail("""
The list of oe-core recipes with maintainers is empty. This may indicate that the test has regressed and needs fixing.
""")
