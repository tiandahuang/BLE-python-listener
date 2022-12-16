import json
import os




class ConfigParser():
    """
    Load, store, and convert config/init files.

    Loaded config files use dictionaries, and saved config files are 
    *.json or *.init (custom) file formats.
    """

    default_init_directory = r'C:\Users\Tienda\Documents\Projects\Research\inits'

    def __init__(self, default_init_dir=None) -> None:
        if default_init_dir is not None: ConfigParser.default_init_directory = default_init_dir

    def read(self, file_name : str) -> dict:
        full_file_name = self.get_full_file_name(file_name)
        if full_file_name is None: raise self.InvalidFileError(file_name, "invalid file name")

        with open(full_file_name) as f:
            for line in f:
                print(line[:-1])

    def convert_init_to_json(self, file_name : str) -> None:
        raise NotImplementedError

    def convert_json_to_init(self, file_name=None, destination=None) -> None:
        raise NotImplementedError

    @classmethod
    def get_full_file_name(self, file_name : str) -> bool:
        full_path = os.path.join(ConfigParser.default_init_directory, file_name)
        if os.path.isfile(file_name): return os.path.abspath(file_name)
        elif os.path.isfile(full_path): return full_path
        else: return None

    class InvalidFileError(Exception):
        """ Raised when a loaded file is missing or invalid """
        def __init__(self, fname, message):
            self.fname = fname
            self.message = message
        def __str__(self):
            return f'error {self.fname}: {self.message}'

def main():
    cfg = ConfigParser()
    cfg.read('ear_v2.init')


if __name__ == '__main__':
    main()

