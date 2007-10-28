###
# Copyright (c) 2002-2005, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import md5
import sha
import time
import random
import shutil
import os.path
from iter import ifilter

def contents(filename):
    return file(filename).read()

def open(filename, mode='wb', *args, **kwargs):
    """filename -> file object.

    Returns a file object for filename, creating as many directories as may be
    necessary.  I.e., if the filename is ./foo/bar/baz, and . exists, and ./foo
    exists, but ./foo/bar does not exist, bar will be created before opening
    baz in it.
    """
    if mode not in ('w', 'wb'):
        raise ValueError, 'utils.file.open expects to write.'
    (dirname, basename) = os.path.split(filename)
    os.makedirs(dirname)
    return file(filename, mode, *args, **kwargs)

def copy(src, dst):
    """src, dst -> None

    Copies src to dst, using this module's 'open' function to open dst.
    """
    srcfd = file(src)
    dstfd = open(dst, 'wb')
    shutil.copyfileobj(srcfd, dstfd)
    
def writeLine(fd, line):
    fd.write(line)
    if not line.endswith('\n'):
        fd.write('\n')

def readLines(filename):
    fd = file(filename)
    try:
        return [line.rstrip('\r\n') for line in fd.readlines()]
    finally:
        fd.close()

def touch(filename):
    fd = file(filename, 'w')
    fd.close()
        
def mktemp(suffix=''):
    """Gives a decent random string, suitable for a filename."""
    r = random.Random()
    m = md5.md5(suffix)
    r.seed(time.time())
    s = str(r.getstate())
    period = random.random()
    now = start = time.time()
    while start + period < now:
        time.sleep() # Induce a context switch, if possible.
        now = time.time()
        m.update(str(random.random()))
        m.update(s)
        m.update(str(now))
        s = m.hexdigest()
    return sha.sha(s + str(time.time())).hexdigest() + suffix

def nonCommentLines(fd):
    for line in fd:
        if not line.startswith('#'):
            yield line

def nonEmptyLines(fd):
    return ifilter(str.strip, fd)

def nonCommentNonEmptyLines(fd):
    return nonEmptyLines(nonCommentLines(fd))

def chunks(fd, size):
    return iter(lambda : fd.read(size), '')
##     chunk = fd.read(size)
##     while chunk:
##         yield chunk
##         chunk = fd.read(size)

class AtomicFile(file):
    """Used for files that need to be atomically written -- i.e., if there's a
    failure, the original file remains, unmodified.  mode must be 'w' or 'wb'"""
    class default(object): # Holder for values.
        # Callables?
        tmpDir = None
        backupDir = None
        makeBackupIfSmaller = True
        allowEmptyOverwrite = True
    def __init__(self, filename, mode='w', allowEmptyOverwrite=None,
                 makeBackupIfSmaller=None, tmpDir=None, backupDir=None):
        if tmpDir is None:
            tmpDir = force(self.default.tmpDir)
        if backupDir is None:
            backupDir = force(self.default.backupDir)
        if makeBackupIfSmaller is None:
            makeBackupIfSmaller = force(self.default.makeBackupIfSmaller)
        if allowEmptyOverwrite is None:
            allowEmptyOverwrite = force(self.default.allowEmptyOverwrite)
        if mode not in ('w', 'wb'):
            raise ValueError, format('Invalid mode: %q', mode)
        self.rolledback = False
        self.allowEmptyOverwrite = allowEmptyOverwrite
        self.makeBackupIfSmaller = makeBackupIfSmaller
        self.filename = filename
        self.backupDir = backupDir
        if tmpDir is None:
            # If not given a tmpDir, we'll just put a random token on the end
            # of our filename and put it in the same directory.
            self.tempFilename = '%s.%s' % (self.filename, mktemp())
        else:
            # If given a tmpDir, we'll get the basename (just the filename, no
            # directory), put our random token on the end, and put it in tmpDir
            tempFilename = '%s.%s' % (os.path.basename(self.filename), mktemp())
            self.tempFilename = os.path.join(tmpDir, tempFilename)
        # This doesn't work because of the uncollectable garbage effect.
        # self.__parent = super(AtomicFile, self)
        super(AtomicFile, self).__init__(self.tempFilename, mode)

    def rollback(self):
        if not self.closed:
            super(AtomicFile, self).close()
            if os.path.exists(self.tempFilename):
                os.remove(self.tempFilename)
            self.rolledback = True

    def close(self):
        if not self.rolledback:
            super(AtomicFile, self).close()
            # We don't mind writing an empty file if the file we're overwriting
            # doesn't exist.
            newSize = os.path.getsize(self.tempFilename)
            originalExists = os.path.exists(self.filename)
            if newSize or self.allowEmptyOverwrite or not originalExists:
                if originalExists:
                    oldSize = os.path.getsize(self.filename)
                    if self.makeBackupIfSmaller and newSize < oldSize:
                        now = int(time.time())
                        backupFilename = '%s.backup.%s' % (self.filename, now)
                        if self.backupDir is not None:
                            backupFilename = os.path.basename(backupFilename)
                            backupFilename = os.path.join(self.backupDir,
                                                          backupFilename)
                        shutil.copy(self.filename, backupFilename)
                # We use shutil.move here instead of os.rename because
                # the latter doesn't work on Windows when self.filename
                # (the target) already exists.  shutil.move handles those
                # intricacies for us.

                # This raises IOError if we can't write to the file.  Since
                # in *nix, it only takes write perms to the *directory* to
                # rename a file (and shutil.move will use os.rename if
                # possible), we first check if we have the write permission
                # and only then do we write.
                fd = file(self.filename, 'a')
                fd.close()
                shutil.move(self.tempFilename, self.filename)
                
        else:
            raise ValueError, 'AtomicFile.close called after rollback.'

    def __del__(self):
        # We rollback because if we're deleted without being explicitly closed,
        # that's bad.  We really should log this here, but as of yet we've got
        # no logging facility in utils.  I've got some ideas for this, though.
        self.rollback()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
