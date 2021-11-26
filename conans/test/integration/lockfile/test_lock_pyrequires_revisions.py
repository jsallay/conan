import textwrap

from conans.test.assets.genconanfile import GenConanfile
from conans.test.utils.tools import TestClient


def test_transitive_py_requires_revisions():
    # https://github.com/conan-io/conan/issues/5529
    client = TestClient()
    python_req = textwrap.dedent("""
        from conans import ConanFile
        some_var = {}
        class PackageInfo(ConanFile):
            pass
        """)
    conanfile = textwrap.dedent("""
        from conans import ConanFile
        class PackageInfo(ConanFile):
            python_requires = "dep/0.1@user/channel"
        """)
    consumer = textwrap.dedent("""
        from conans import ConanFile
        class MyConanfileBase(ConanFile):
            python_requires = "pkg/0.1@user/channel"
            def generate(self):
                self.output.info("VAR={}!!!".format(self.python_requires["dep"].module.some_var))
        """)
    client.save({"dep/conanfile.py": python_req.format("42"),
                 "pkg/conanfile.py": conanfile,
                 "consumer/conanfile.py": consumer})

    client.run("export dep dep/0.1@user/channel")
    client.run("export pkg pkg/0.1@user/channel")
    client.run("lock create consumer/conanfile.py --lockfile-out=conan.lock")

    client.save({"dep/conanfile.py": python_req.format("123")})
    client.run("export dep dep/0.1@user/channel")

    client.run("install consumer/conanfile.py --lockfile=conan.lock")
    assert "conanfile.py: VAR=42!!!" in client.out

    client.run("install consumer/conanfile.py")
    assert "conanfile.py: VAR=123!!!" in client.out


def test_transitive_matching_revisions():
    client = TestClient()
    dep = textwrap.dedent("""
       from conans import ConanFile
       some_var = {}
       class PackageInfo(ConanFile):
           pass
       """)
    tool = textwrap.dedent("""
        from conans import ConanFile
        class PackageInfo(ConanFile):
            python_requires = "dep/{}"
            def package_id(self):
                self.output.info("VAR={{}}!!!".format(self.python_requires["dep"].module.some_var))
        """)
    pkg = textwrap.dedent("""
        from conans import ConanFile
        class MyConanfileBase(ConanFile):
            python_requires = "{}/0.1"
            def package_id(self):
                self.output.info("VAR={{}}!!!".format(self.python_requires["dep"].module.some_var))
        """)
    client.save({"dep/conanfile.py": dep.format(42),
                 "toola/conanfile.py": tool.format("0.1"),
                 "toolb/conanfile.py": tool.format("0.2"),
                 "pkga/conanfile.py": pkg.format("toola"),
                 "pkgb/conanfile.py": pkg.format("toolb"),
                 "app/conanfile.py": GenConanfile().with_requires("pkga/0.1", "pkgb/0.1")})

    client.run("export dep dep/0.1@")
    client.run("export dep dep/0.2@")
    client.run("export toola toola/0.1@")
    client.run("export toolb toolb/0.1@")
    client.run("create pkga pkga/0.1@")
    client.run("create pkgb pkgb/0.1@")
    client.run("lock create app/conanfile.py --lockfile-out=conan.lock")

    client.save({"dep/conanfile.py": dep.format(123)})
    client.run("export dep dep/0.1@")
    client.run("export dep dep/0.2@")

    client.run("install app/conanfile.py --lockfile=conan.lock")
    assert "pkga/0.1: VAR=42!!!" in client.out
    assert "pkgb/0.1: VAR=42!!!" in client.out
    assert "VAR=123" not in client.out

    client.run("install app/conanfile.py")
    assert "pkga/0.1: VAR=123!!!" in client.out
    assert "pkgb/0.1: VAR=123!!!" in client.out
    assert "VAR=42" not in client.out
