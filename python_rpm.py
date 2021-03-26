import os
import random
import string
import tempfile
import time
from os.path import dirname

import rpm
import jinja2


class RPMReader:
    @staticmethod
    def read_rpm(filename):
        rpm.addMacro("_dbpath", os.path.join(dirname(__file__), "fake_pkg_db"))
        rpm.addMacro("_topdir", dirname(__file__))
        ts = rpm.TransactionSet(".", rpm.RPMVSF_MASK_NODIGESTS | rpm.RPMVSF_MASK_NOSIGNATURES)
        fd = rpm.fd.open(filename)
        header = ts.hdrFromFdno(fd)
        # hdr[rpm.RPMTAG_NAME] = "test_rpm"
        # fo = os.fdopen(fd, "w+")
        # hdr.write(fd)
        print(header[rpm.RPMTAG_NAME])
        files = rpm.files(header)
        payload = rpm.fd.open(fd, flags=header["payloadcompressor"])
        archive = files.archive(payload, write=False)
        for t in archive:
            if t.fflags & rpm.RPMFILE_SPECFILE:
                od = os.open(t.name, os.O_RDWR | os.O_CREAT)
                archive.readto(od)
            print(t.name)


class RPMBuilder:
    TEMPLATE_NAME = "blueprint.spec.j2"
    DEFAULT_SECTION_TEXT = "# let's skip this for now"
    DEFAULT_SPEC_DATA = {
        "name": "blueprint",
        "version": "1.0",
        "summary": "blueprint package",
        "release": "1",
        "license": "unknown",
        "arch": "noarch",
        "buildroot": "",
        "description": DEFAULT_SECTION_TEXT,
        "prep": DEFAULT_SECTION_TEXT,
        "build": DEFAULT_SECTION_TEXT,
        "install": DEFAULT_SECTION_TEXT,
        "clean": DEFAULT_SECTION_TEXT,
        "files": DEFAULT_SECTION_TEXT,
    }

    def __init__(self):
        # Prepare spec template
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=dirname(__file__))
        )
        self.template = self.env.get_template(self.TEMPLATE_NAME)
        # Prepare dirs
        self.tmp_dir = tempfile.mkdtemp()
        self._prepare_rpm_root()
        self._init_rpm()
        self.ts = rpm.TransactionSet(".", rpm.RPMVSF_MASK_NODIGESTS | rpm.RPMVSF_MASK_NOSIGNATURES)

    def _abs_path(self, *path):
        return os.path.join(self.tmp_dir, *path)

    def _prepare_rpm_root(self):
        for p in ["RPMS", "SRPMS", "BUILD", "SPECS"]:
            os.makedirs(self._abs_path(p))

    def _init_rpm(self):
        rpm.addMacro("_topdir", self.tmp_dir)
        rpm.addMacro("_tmppath", self.tmp_dir)
        rpm.addMacro("_dbpath", self.tmp_dir)
        # rpm.setVerbosity(rpm.RPMLOG_DEBUG)
        rpm.setVerbosity(rpm.RPMLOG_CRIT)

    def build_rpm(self):
        package_name = "".join(random.choice(string.ascii_lowercase) for _ in range(12))

        # Fill template
        spec_data = self.DEFAULT_SPEC_DATA
        spec_data["name"] = package_name
        spec_data["files"] = f"/{package_name}.bin"

        # Create spec
        rendered = self.template.render(**spec_data)
        tmp_spec_path = os.path.join(self.tmp_dir, "SPECS", f"{package_name}.spec")
        with open(tmp_spec_path, "w") as tmp_spec:
            tmp_spec.write(rendered)

        # Create build dirs
        build_root = rpm.expandMacro("%{buildroot}")
        if not os.path.exists(build_root):
            os.makedirs(build_root)

        # Writing binary file
        tmp_bin_path = os.path.join(build_root, f"{package_name}.bin")
        with open(tmp_bin_path, "wb") as tmp_bin:
            tmp_bin.write(os.urandom(1024 * 1024))  # size in bytes

        # Generating rpm
        build_amount = rpm.RPMBUILD_PACKAGEBINARY | rpm.RPMBUILD_RMBUILD | rpm.RPMBUILD_CLEAN
        sp = rpm.spec(specfile=tmp_spec_path)
        sp._doBuild(ts=self.ts, buildAmount=build_amount)


if __name__ == "__main__":
    st = time.time()
    builder = RPMBuilder()
    for _ in range(300):
        builder.build_rpm()
    et = time.time()
    print(et - st)
    print(builder.tmp_dir)
    #
    # RPMReader.read_rpm("binwalk-2.2.0-4.fc33.src.rpm")
