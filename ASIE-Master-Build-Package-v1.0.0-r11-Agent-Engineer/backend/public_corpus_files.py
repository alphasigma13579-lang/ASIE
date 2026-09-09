"""Handle-based guards for an operator-provisioned service-private directory.

No network or ACL changes. Host administrators and the service OS identity are
trusted: code running as either can already replace the process or its database.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat


class UnsafeStorePath(OSError):
    pass


class StoreFiles:
    """Keep directory/file guards alive until AFTER SQLite closes."""

    def __init__(self, directory):
        self.path = Path(directory).absolute()
        self._fds = []
        self._directories = []
        self._win = None
        self._root_fd = None
        self._files = {}

    def open(self):
        if ".." in self.path.parts:
            raise UnsafeStorePath()
        try:
            if os.name == "nt":
                self._win = _Windows()
                # Each already-open parent is pinned against rename/deletion.
                # OPEN_REPARSE_POINT inspects the entry, never its target.
                for part in (*reversed(self.path.parents), self.path):
                    handle = self._win.open(part, directory=True)
                    self._directories.append(handle)
                self._win.private(self._directories[-1])
            else:
                if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
                    raise UnsafeStorePath()
                fd = os.open(self.path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
                self._fds.append(fd)
                for part in self.path.parts[1:]:
                    parent = os.fstat(fd)
                    # Shared sticky parents (e.g. /tmp) cannot remove another
                    # user's child. Other group/world-writable parents are denied.
                    if parent.st_uid not in (0, os.geteuid()) or (
                            parent.st_mode & 0o022 and not parent.st_mode & stat.S_ISVTX):
                        raise UnsafeStorePath()
                    fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY |
                                 os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                    self._fds.append(fd)
                self._root_fd = fd
                root = os.fstat(fd)
                if root.st_uid != os.geteuid() or root.st_mode & 0o077:
                    raise UnsafeStorePath()
            return self
        except OSError:
            self.close()
            raise UnsafeStorePath() from None

    def file(self, name):
        if name not in ("public_knowledge.lock", "public_knowledge.sqlite3",
                        "public_knowledge.sqlite3-wal", "public_knowledge.sqlite3-shm",
                        "public_knowledge.sqlite3-journal"):
            raise UnsafeStorePath()
        if name in self._files:
            return self._files[name]
        try:
            if self._win:
                import msvcrt
                handle = self._win.open(self.path / name, directory=False,
                                        transient=name.endswith("-journal"))
                try:
                    self._win.private(handle)
                    fd = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
                except BaseException:
                    self._win.close(handle)
                    raise
            else:
                fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                             os.O_CLOEXEC | os.O_NONBLOCK, 0o600, dir_fd=self._root_fd)
            self._fds.append(fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise UnsafeStorePath()
            if not self._win and (info.st_uid != os.geteuid() or info.st_mode & 0o077):
                raise UnsafeStorePath()
            self._files[name] = fd
            self.validate()
            return fd
        except OSError:
            raise UnsafeStorePath() from None

    def validate(self):
        # lstat/dir_fd no-follow checks detect substitution rather than comparing
        # two handles which both followed the same symlink.
        if self._win:
            self._win.private(self._directories[-1])
        else:
            root = os.fstat(self._root_fd)
            if root.st_uid != os.geteuid() or root.st_mode & 0o077:
                raise UnsafeStorePath()
            if not os.path.samestat(root, self.path.lstat()):
                raise UnsafeStorePath()
        for name, fd in self._files.items():
            entry = (self.path / name).lstat() if self._win else os.stat(
                name, dir_fd=self._root_fd, follow_symlinks=False)
            actual = os.fstat(fd)
            if (stat.S_ISLNK(entry.st_mode) or getattr(entry, "st_file_attributes", 0) & 0x400
                    or entry.st_nlink != 1 or not os.path.samestat(actual, entry)):
                raise UnsafeStorePath()

    def database(self):
        # The rollback journal is included because a newly created SQLite file
        # enters WAL via a short rollback-mode initialization.
        for suffix in (".sqlite3", ".sqlite3-wal", ".sqlite3-shm", ".sqlite3-journal"):
            self.file("public_knowledge" + suffix)
        self.validate()
        return self.path / "public_knowledge.sqlite3"

    def close(self):
        failed = False
        for fd in reversed(self._fds):
            try:
                os.close(fd)
            except OSError:
                failed = True
        self._fds.clear()
        if self._win:
            for handle in reversed(self._directories):
                try:
                    self._win.close(handle)
                except OSError:
                    failed = True
        self._directories.clear()
        if failed:
            raise UnsafeStorePath()


class _Windows:
    """Win32 handle/ACL boundary; loaded only on Windows, without third-party DLLs."""

    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.advapi = c.WinDLL("advapi32", use_last_error=True)
        self.kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p,
                                           w.DWORD, w.DWORD, w.HANDLE]
        self.kernel.CreateFileW.restype = w.HANDLE
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        self.kernel.GetCurrentProcess.restype = w.HANDLE
        self.kernel.LocalFree.argtypes = [c.c_void_p]
        self.kernel.LocalFree.restype = c.c_void_p
        self.kernel.GetFileInformationByHandle.argtypes = [w.HANDLE, c.c_void_p]
        self.kernel.GetFileInformationByHandle.restype = w.BOOL
        self.kernel.GetDriveTypeW.argtypes = [w.LPCWSTR]
        self.kernel.GetDriveTypeW.restype = w.UINT
        self.advapi.GetSecurityInfo.argtypes = [w.HANDLE, c.c_int, w.DWORD,
            c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p), c.c_void_p,
            c.POINTER(c.c_void_p)]
        self.advapi.GetSecurityInfo.restype = w.DWORD
        self.advapi.GetAce.argtypes = [c.c_void_p, w.DWORD, c.POINTER(c.c_void_p)]
        self.advapi.GetAce.restype = w.BOOL
        self.advapi.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(w.LPWSTR)]
        self.advapi.ConvertSidToStringSidW.restype = w.BOOL
        self.advapi.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
        self.advapi.OpenProcessToken.restype = w.BOOL
        self.advapi.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p,
                                                   w.DWORD, c.POINTER(w.DWORD)]
        self.advapi.GetTokenInformation.restype = w.BOOL
        token = w.HANDLE()
        if not self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(), 8, c.byref(token)):
            raise UnsafeStorePath()
        try:
            size = w.DWORD()
            self.advapi.GetTokenInformation(token, 1, None, 0, c.byref(size))
            buffer = c.create_string_buffer(size.value)
            if not self.advapi.GetTokenInformation(token, 1, buffer, size, c.byref(size)):
                raise UnsafeStorePath()
            self.user = self.sid(c.c_void_p.from_buffer(buffer).value)
        finally:
            self.close(token)

    def sid(self, pointer):
        text = self.w.LPWSTR()
        if not self.advapi.ConvertSidToStringSidW(pointer, self.c.byref(text)):
            raise UnsafeStorePath()
        try:
            return text.value
        finally:
            self.kernel.LocalFree(text)

    def open(self, path, *, directory, transient=False):
        if self.kernel.GetDriveTypeW(str(path.anchor)) != 3:  # fixed local disk only
            raise UnsafeStorePath()
        # Pin persistent entries against replacement. The rollback journal alone
        # shares deletion: SQLite retires it during WAL initialization, inside
        # the verified service-private directory (not an untrusted namespace).
        access = 0x20080 if directory else 0xC0020080
        handle = self.kernel.CreateFileW(str(path), access, 7 if transient else 3, None,
                                        3 if directory else 4, 0x02200000, None)
        if handle == self.c.c_void_p(-1).value:
            raise UnsafeStorePath()
        info = (self.w.DWORD * 13)()  # BY_HANDLE_FILE_INFORMATION: 52 bytes
        if not self.kernel.GetFileInformationByHandle(handle, self.c.byref(info)):
            self.close(handle)
            raise UnsafeStorePath()
        attributes = info[0]
        if (attributes & 0x400 or bool(attributes & 0x10) != directory
                or not directory and info[10] != 1):
            self.close(handle)
            raise UnsafeStorePath()
        return handle

    def private(self, handle):
        c = self.c
        owner, acl, descriptor = c.c_void_p(), c.c_void_p(), c.c_void_p()
        result = self.advapi.GetSecurityInfo(handle, 1, 5, c.byref(owner), None,
                                           c.byref(acl), None, c.byref(descriptor))
        if result:
            raise UnsafeStorePath()
        try:
            trusted = {self.user, "S-1-5-18", "S-1-5-32-544"}
            if not owner.value or self.sid(owner) not in trusted or not acl.value:
                raise UnsafeStorePath()
            # ACL header contains AceCount at byte offset 4.
            count = c.c_ushort.from_address(acl.value + 4).value
            for index in range(count):
                ace = c.c_void_p()
                if not self.advapi.GetAce(acl, index, c.byref(ace)):
                    raise UnsafeStorePath()
                header = (c.c_ubyte * 4).from_address(ace.value)
                if header[1] & 8:  # INHERIT_ONLY: no grant on this object
                    continue
                if header[0] == 1:  # deny ACE cannot increase authority
                    continue
                # Reject callback/object/unknown grant types rather than guessing.
                if header[0] != 0 or self.sid(ace.value + 8) not in trusted:
                    raise UnsafeStorePath()
        finally:
            self.kernel.LocalFree(descriptor)

    def close(self, handle):
        if not self.kernel.CloseHandle(handle):
            raise UnsafeStorePath()
