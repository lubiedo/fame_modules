import os
from shutil import copyfile

from fame.core.module import ProcessingModule, ModuleInitializationError
from fame.common.utils import tempdir

import threading

try:
    from unipacker.core import Sample, SimpleClient, UnpackerEngine
    HAVE_UNIPACKER = True
except ImportError:
    HAVE_UNIPACKER = False


class Unipacker(ProcessingModule):
    name = "unipacker"
    description = "Unpacker for Windows binaries based on emulation"
    acts_on = "executable"

    config = [
        {
            "name": "auto_default_unpacker",
            "type": "bool",
            "description": "Enable auto default unpacker",
            "default": True,
            "option": True
        }
    ]

    def initialize(self):
        if not HAVE_UNIPACKER:
            raise ModuleInitializationError(self, "Missing dependency: unipacker")
        return True


    def unpack(self, file):
        event = threading.Event()
        client = SimpleClient(event)
        sample = Sample(file, auto_default_unpacker=self.auto_default_unpacker)

        if sample.unpacker.name == 'unknown':
            # self.log('warning', 'Packer unknown!')
            return False
        self.log('info', f'Packer is {sample.unpacker.name}')

        unpacked = 'unpacked_' + os.path.basename(file)
        unpacked = os.path.join(self.results_dir, unpacked)
        engine = UnpackerEngine(sample, unpacked)

        engine.register_client(client)
        threading.Thread(target=engine.emu).start()
        event.wait()
        engine.stop()

        if not os.path.exists(unpacked):
            self.log('warning', 'Unable to unpack the binary')
            return False
        self.add_extracted_file(unpacked)
        return True

    def each(self, target):
        # Create temporary directory to get results
        self.outdir = tempdir()

        self.results_dir = os.path.join(self.outdir, "output")

        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)

        copyfile(target, os.path.join(self.outdir, os.path.basename(target)))
        return self.unpack(target)
