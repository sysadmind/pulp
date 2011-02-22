# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import hashlib
from pulp.client.api.base import PulpAPI


class Momento:
    """
    Upload momento contains an upload uuid.
    """

    ROOT = '~/.pulp/upload'

    def __init__(self, path, checksum):
        fn = os.path.basename(path)
        root = os.path.expanduser(self.ROOT)
        path = path = os.path.join(root, str(checksum))
        self.path = os.path.join(path, fn)
        self.__mkdir(path)

    def write(self, uuid):
        f = open(self.path, 'w')
        f.write(uuid)
        f.close()

    def read(self):
        try:
            f = open(self.path)
            uuid = f.read()
            f.close()
            return uuid
        except:
            pass

    def delete(self):
        try:
            os.unlink(self.path)
            os.rmdir(os.path.dirname(self.path))
        except:
            pass

    def __mkdir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)



class UploadAPI(PulpAPI):
    """
    Connection class to access upload related calls
    """

    def upload(self, path, chunksize=0xA00000):
        """
        Upload a file at the specified path.
        @param path: The abs path to a file to upload.
        @type path: str
        @param checksize: The upload chunking size.  Default=10M.
        @type chunksize: int
        @return: The file upload ID.
        @rtype: str
        """
        md5 = self.__md5(path)
        momento = Momento(path, md5)
        uuid = momento.read()
        try:
            uuid, offset = self.__start(path, md5, uuid)
            if offset < 0:
                # already uploaded
                return uuid
            momento.write(uuid)
            self.__upload(path, offset, uuid, chunksize)
            momento.delete()
        except SystemExit, KeyboardInterrupt:
            pass # resume later
        except Exception:
            momento.delete()
        return uuid

    def __start(self, path, md5, uuid):
        fn = os.path.basename(path)
        size = os.path.getsize(path)
        d = dict(name=fn, checksum=md5, size=size, uuid=uuid)
        path = '/services/upload/'
        d = self.server.POST(path, d)[1]
        return (d['uuid'], int(d['offset']))

    def __upload(self, path, offset, uuid, bufsize):
        f = open(path)
        f.seek(offset)
        while(1):
            buf = f.read(bufsize)
            if buf:
                self.__append(uuid, buf)
            else:
                break
        f.close()
        return self

    def __append(self, id, buf):
        path = '/services/upload/append/%s/' % id
        return self.server.PUT(path, buf)[1]

    def __md5(self, path):
        f = open(path)
        checksum = hashlib.md5()
        while(1):
            buf = f.read(8196)
            if buf:
                checksum.update(buf)
            else:
                break
        f.close()
        return checksum.hexdigest()
    
    def import_content(self, metadata, uploadid):
        uploadinfo = {'metadata': metadata,
                      'uploadid': uploadid}
        path = "/services/upload/import/"
        return self.server.POST(path, uploadinfo)[1]
