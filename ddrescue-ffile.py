#!/usr/bin/env python

import dataclasses
import subprocess
import tempfile
import os
import hashlib
from pathlib import Path
from typing import Iterator
from tqdm import tqdm
import getopt
import sys
import time
import json

@dataclasses.dataclass
class MountInfo:
    identifier: str
    source: Path
    target: Path = Path(tempfile.mkdtemp())
    offset: int = None
    size: int = None


class DdrescueFfile(object):
    mounted = {}

    def __init__(self, filesystem: Path, logfile: Path):
        self.logfile = logfile.absolute()
        self.filesystem = filesystem.absolute()
        self.app_logfile = open('ddrescue-ffile-{}.log'.format(time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime())), 'w')

        if not self.logfile.is_file():
            raise Exception('ddrescue log file {} not found'.format(self.logfile))

        if not self.filesystem.is_file():
            raise Exception('ddrescue filesystem file {} not found'.format(self.filesystem))

    def mount(self, mount_info: MountInfo) -> None:
        if mount_info.identifier not in self.mounted:
            try:
                self.log('Mounting filesystem {} to {}'.format(mount_info.identifier, mount_info.target))
                self.command(['mount', '-o', 'ro', '-t', 'auto', str(mount_info.source), str(mount_info.target)])
                self.log('Done.')
                self.mounted[mount_info.identifier] = mount_info
            except:
                self.log('Mounting filesystem failed')
                raise

    def umount(self, mount_info: MountInfo) -> None:
        if mount_info.identifier in self.mounted:
            try:
                self.log('Umounting filesystem {} mounted in {}'.format(mount_info.identifier, mount_info.target))
                self.command(['umount', str(mount_info.target)])
                self.log('Done.')
                del self.mounted[mount_info.identifier]
            except:
                self.log('Umounting filesystem failed')
                raise

    def mounted2md5list(self, mounted: Path) -> dict:
        md5list = {}
        self.log('Scaning filesystem...')
        files = list(mounted.rglob('*'))
        self.log('Done.')

        self.log('Building MD5 checksum list...')

        for file in tqdm(files):
            list_name = str(file.absolute()).replace(str(mounted.absolute()), '')
            if file.is_file():
                md5list[list_name] = self.checksum(Path(file))
            elif file.is_dir():
                # We ignore dirs in sumlist
                pass
            else:
                md5list[list_name] = False

        self.log('Done.')
        return md5list

    def checksum(self, path: Path, hash_factory=hashlib.md5, chunk_num_blocks=128) -> bytes:
        h = hash_factory()
        with path.open('rb') as f:
            while chunk := f.read(chunk_num_blocks * h.block_size):
                h.update(chunk)
        return h.digest()

    def command(self, command: list) -> None:
        if subprocess.call(command) > 0:
            raise Exception('Running command {} failed'.format(command))

    def ddrescue(self, filesystem: Path, logfile: Path, fill: bool = False) -> None:
        try:
            handle, bytevalue_file = tempfile.mkstemp()

            f = open(bytevalue_file, 'wb')
            if fill:
                self.log('Filling bad-sector blocks with non-zero bytevalue...')
                f.write(b'1')
            else:
                self.log('Restoring bad-sector blocks to zero bytevalue...')
                f.write(b'\x00')
            f.close()

            self.command(['ddrescue', '--fill=-', bytevalue_file, str(filesystem), str(logfile)])
            os.remove(bytevalue_file)
            self.log('Done.')
        except:
            self.log('ddrescue command failed')
            raise

    def log(self, message: str) -> None:
        print(message)
        self.app_logfile.write(message + "\n")
        self.app_logfile.flush()

    def get_file_system_info(self, path: Path) -> dict:
        json_output = subprocess.check_output(['sfdisk', '-d', str(path), '-J'])
        return json.loads(json_output)

    def check_file_system(self, path: Path) -> Iterator[MountInfo]:
        part_info = self.get_file_system_info(path)
        partition_table = part_info.get('partitiontable')
        self.log('Partition table "{}" was found in "{}"'.format(partition_table.get('label'), partition_table.get('device')))

        partitions = partition_table.get('partitions', [])
        number_of_partitions = len(partitions)

        self.log('{} partition was found:'.format(number_of_partitions))

        # print info
        for partition_number, partition in enumerate(partitions):
            self.log('{}: "{}" of type "{}" '.format(
                partition_number,
                partition.get('node'),
                partition.get('type')
            ))

        for partition in partitions:
            yield MountInfo(partition.get('node'), path, offset=partition.get('start'), size=partition.get('size'))


    def start(self):

        ### First step - mount -> md5sum list -> umount ###
        try:
            md5list_original_by_partition = {}
            md5list_modified_by_partition = {}
            # Check filesystem
            mount_infos = list(self.check_file_system(self.filesystem))
            for mount_info in mount_infos:
                # Mount every partition we have found
                self.mount(mount_info)

                # Calculate md5s for given mount point
                md5list_original_by_partition[mount_info.identifier] = self.mounted2md5list(mount_info.target)

                # Umount filesystem
                self.umount(mount_info)
                self.log('')

            ### Second step - modify bad blocks -> mount -> md5sum list -> umount -> modify bad blocks to previous state ###
            # Change fill bad blocks by different data, so we can detect changes
            self.ddrescue(self.filesystem, self.logfile, True)

            for mount_info in mount_infos:
                # Mount filesystem again
                self.mount(mount_info)

                # Calculate md5s again
                md5list_modified_by_partition[mount_info.identifier] = self.mounted2md5list(mount_info.target)

                # Umount filesystem again
                self.umount(mount_info)
                self.log('')

            # Revert changes to filesystem
            self.ddrescue(self.filesystem, self.logfile, False)

            ### Third step - check diff ###
            for partition_identifier, md5list_original in md5list_original_by_partition.items():
                md5list_modified = md5list_modified_by_partition.get(partition_identifier)
                if not md5list_modified:
                    raise Exception('Modified md5list is empty!')
                self.log('=================================')
                self.log('==== Diff for partition "{}" ===='.format(partition_identifier))
                self.log('=================================')
                corrupted = 0
                for patho in md5list_original:
                    if md5list_modified[patho] != md5list_original[patho]:
                        corrupted += 1
                        self.log('File {} seems corrupted, {} != {}'.format(patho, md5list_original[patho], md5list_modified[patho]))
                    elif md5list_modified[patho] == False and md5list_original[patho] == False:
                        self.log('Failed to create md5sum for {}'.format(patho))
                    elif md5list_modified[patho] == False or md5list_original[patho] == False:
                        corrupted += 1
                        self.log('File {} seems corrupted, {} != {}'.format(patho, md5list_original[patho], md5list_modified[patho]))

                if corrupted > 0:
                    self.log('{} corupted files has been found :-('.format(corrupted))
                else:
                    self.log('All files are OK!')

                self.log('')
                self.log('---------------------------------------')
                self.log('')

        except:
            raise
        finally:
            # Umount all mounted
            clear_mounts = self.mounted.copy()
            for mount_identifier, mount_info in clear_mounts.items():
                self.umount(mount_info)

            self.app_logfile.close()


def usage():
    print('Usage:')
    print('ddfrescue [image] [logfile]')
    print('-h --help for this help')


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()

    if len(args) != 2:
        usage()
        sys.exit()

    ddr = DdrescueFfile(Path(args[0]), Path(args[1]))
    ddr.start()
