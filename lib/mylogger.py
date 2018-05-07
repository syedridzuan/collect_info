import os
import logging
import __main__

class MyLogger:

    def __init__(self, folder, filename):
        """Init File."""
        self.folder = folder
        self.filename = filename

    def getlogger(self):
        """Set logger."""
        sfolder = os.path.dirname(os.path.realpath(__main__.__file__))
        log_file_list = [sfolder, self.folder, self.filename]
        logfile = os.path.join(*log_file_list)
        logging.basicConfig(level=logging.INFO,
                            filename=logfile,  # log to this file.
                            format='%(asctime)s %(message)s')
        return logging