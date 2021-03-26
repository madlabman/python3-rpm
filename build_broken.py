import os

import binwalk

EMPTY_RPM = "empty.rpm"
ONLY_HEADER_RPM = "only-header.rpm"
BROKEN_HEADER_RPM = "broken-header.rpm"
INVALID_SIGNED_RPM = "invalid-signed.rpm"
WRONG_PAYLOAD_RPM = "wrong-payload.rpm"
BROKEN_ARCHIVE_RPM = "broken-archive.rpm"

HEADER_MAGIC = b"\x8e\xad\xe8\x01\x00\x00\x00\x00"


def find_payload_offset(filename: str) -> int:
    """
    return decimal offset of payload
    """
    l_res = binwalk.scan(filename, signature=True, quiet=True)
    if len(l_res) == 0:
        return -1

    for sig in l_res:
        for sig_res in sig.results:
            if "gzip compressed data" in sig_res.description:
                return sig_res.offset

    return -1


def build_empty(filename: str):
    """
    create new file and use as RPM archive
    """
    d = os.open(filename, os.O_CREAT)
    os.close(d)


def build_only_with_header(filename: str):
    """
    extract header from the correct RPM archive
    write header to the file and use as RPM archive
    """
    donor_filename = "foo-1.0-1.noarch.rpm"
    donor_payload_offset = find_payload_offset(donor_filename)
    with open(donor_filename, "rb") as donor:
        buf = donor.read(donor_payload_offset)
        with open(filename, "wb") as file:
            file.write(buf)


def build_wrong_payload(filename: str):
    """
    get the correct RPM archive
    extract payload
    get another one correct RPM archive
    get data before payload
    append payload from the first archive
    """
    donor_filename = "hello-2.0-1.i686.rpm"
    recipient_filename = "hello-2.0-1.x86_64.rpm"
    donor_payload_offset = find_payload_offset(donor_filename)
    recipient_payload_offset = find_payload_offset(recipient_filename)
    buf = b""
    with open(recipient_filename, "rb") as file:
        buf += file.read(recipient_payload_offset)
    with open(donor_filename, "rb") as file:
        file.seek(donor_payload_offset)
        buf += file.read()
    with open(filename, "wb") as file:
        file.write(buf)


def build_missed_magic_header_sequence(filename: str):
    """
    there is a magic byte sequence in the header
    remove that sequence from the file
    """
    donor_filename = "hello-2.0-1.x86_64.rpm"
    buf = b""
    with open(donor_filename, "rb") as file:
        count_of_bytes = len(HEADER_MAGIC)
        while seq := file.read(count_of_bytes):
            if seq == HEADER_MAGIC:
                buf += file.read()
                break
            buf += seq
    with open(filename, "wb") as file:
        file.write(buf)


def build_invalid_signature():
    """
    using a file signed with unknown public key
    no need to build
    """
    pass


def build_broken_file_in_archive(filename: str):
    """
    open the correct RPM archive
    identify file in archive payload
    write random bytes (possible cause broken CPIO)
    """

    donor_filename = "hello-2.0-1.x86_64.rpm"
    bytes_to_find = b"\x35\x41\xf3\xcf\xcc\xa0\xb9\x55"
    bytes_as_replace = b"\xcc\xa0\xb9\x55\x35\x41\xf3\xcf"
    buf = b""
    with open(donor_filename, "rb") as file:
        while seq := file.read(8):
            if seq == bytes_to_find:
                buf += bytes_as_replace
                buf += file.read()
                break
            buf += seq
    with open(filename, "wb") as file:
        file.write(buf)


if __name__ == "__main__":
    build_empty(EMPTY_RPM)
    build_only_with_header(ONLY_HEADER_RPM)
    build_missed_magic_header_sequence(BROKEN_HEADER_RPM)
    build_broken_file_in_archive(BROKEN_ARCHIVE_RPM)
    build_wrong_payload(WRONG_PAYLOAD_RPM)
