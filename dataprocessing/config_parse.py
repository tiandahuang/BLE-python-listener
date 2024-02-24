import json
import os

class ConfigParser():
    """
    Load, store, and convert config/init files.

    Loaded config files use dictionaries, and saved config files are 
    *.json or *.init (custom) file formats.

    TODO: deprecate init files
    """

    default_init_directory = None

    def __init__(self, default_init_dir=None) -> None:
        ConfigParser.default_init_directory = (default_init_dir 
                                               if default_init_dir is not None
                                               else os.getcwd())

    def read(self, file_name : str) -> dict:
        full_file_name = self._get_full_file_name(file_name)
        if full_file_name is None: raise self.InvalidFileError(full_file_name, 'invalid file name')

        ext = os.path.splitext(full_file_name)[1]
        if ext == '.init': parsed_dict = self._init_to_dict(full_file_name)
        elif ext == '.json': parsed_dict = self._json_to_dict(full_file_name)
        else: raise self.InvalidFileError(full_file_name, 'invalid file extension')

        return parsed_dict

    def convert_init_to_json(self, file_name : str, dest=None) -> None:
        full_file_name = self._get_full_file_name(file_name)
        if full_file_name is None: raise self.InvalidFileError(full_file_name, 'invalid file name')
        file_no_ext, ext = os.path.splitext(full_file_name)
        if ext != '.init': raise self.InvalidFileError(full_file_name, 'invalid file extension')

        full_file_name_json = file_no_ext + '.json'
        with open(full_file_name_json, 'w') as f:
            json.dump(self._init_to_dict(full_file_name), f, indent=4)

    def convert_json_to_init(self, file_name : str, destination=None) -> None:
        full_file_name = self._get_full_file_name(file_name)
        if full_file_name is None: raise self.InvalidFileError(full_file_name, 'invalid file name')
        file_no_ext, ext = os.path.splitext(full_file_name)[1]
        if ext != '.init': raise self.InvalidFileError(full_file_name, 'invalid file extension')

        full_file_name_json = file_no_ext + '.init'
        with open(full_file_name_json, 'w') as f:
            raise NotImplementedError

    def _init_to_dict(self, full_file_name : str) -> dict:
        with open(full_file_name) as f:

            # initialize empty dictionary
            parsed_dict = {
                'Packet Information':None,
                'Signals Information':[],
                'Biometric Settings':None,
                'Packet Structure':[]
            }
            
            section_idx = 0
            signal_subsect = ''
            curr_signal_ref = None

            for line_num, line in enumerate(f):
                cleaned_line = line.strip('\n\r\t ')
                if cleaned_line[0].isdigit():   # start a hierarchical unit
                    vals = cleaned_line.split(', ')
                    if section_idx == 0:    # Packet Information
                        labels = ('frequency', 'bytes')
                        convert = (int, int)
                        parsed_dict['Packet Information'] = {labels[i]:convert[i](vals[i]) for i in range(len(labels))}
                    elif section_idx == 1:  # Signals Information
                        labels = ('id', 'name', 'bytes-per-data', 'frequency', 'bits-per-data', 'datatype')
                        convert = (int, str, int, int, int, str)
                        parsed_dict['Signals Information'].append({labels[i]:convert[i](vals[i]) for i in range(len(labels))})
                        curr_signal_ref = parsed_dict['Signals Information'][-1]
                    elif section_idx == 2:  # Biometric Settings
                        # TODO:
                        pass
                    elif section_idx == 3:  # Packet Structure
                        parsed_dict['Packet Structure'].append(int(cleaned_line))
                elif cleaned_line[0] == '.' and cleaned_line[1] != '.':    # signal subsection
                    signal_subsect = cleaned_line[1:]
                    curr_signal_ref[signal_subsect] = {}
                elif cleaned_line[0:2] == '..' and cleaned_line[2] != '.': # signal sub-subsection
                    vals = cleaned_line[2:].split(': ')
                    if signal_subsect == 'graphable':
                        curr_signal_ref[signal_subsect] = {'color':tuple(map(int, vals[1].split(' ')))}
                    elif signal_subsect == 'digdisplay':
                        curr_signal_ref[signal_subsect][vals[0]] = vals[1]
                    elif signal_subsect == 'filter':
                        curr_signal_ref[signal_subsect][vals[0]] = list(map(float, vals[1].split(', ')))
                elif cleaned_line == 'end':
                    section_idx += 1
            
            return parsed_dict

    def _json_to_dict(self, full_file_name : str) -> dict:
        with open(full_file_name) as f:
            parsed_dict = json.load(f)
        return parsed_dict

    @classmethod
    def _get_full_file_name(self, file_name : str) -> bool:
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


# for testing

def main():
    fname = 'ear_v1.json'
    cfg = ConfigParser()
    print(json.dumps(cfg.read(fname), indent=4))
    cfg.convert_init_to_json(fname)

if __name__ == '__main__':
    main()

