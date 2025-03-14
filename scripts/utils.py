import os
import errno
import subprocess
import glob


def set_logger(log_file):
    import logging
    # check if log_file exists, if so rename
    if os.path.exists(log_file):
        os.rename(log_file, log_file + '.old')
    logger = logging.getLogger(log_file)
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(file_handler)

    return logger

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def check_dependency(config:dict):
    # check if workload name is valid
    if config['program'].count('-') != 2:
        raise ValueError("Invalid workload name")

def update_config(config:dict):
    check_dependency(config)

    config['data_dir'] = os.path.join(config['base_dir'], 'data')
    mkdir_p(config['data_dir'])
    config['logs_dir'] = os.path.join(config['base_dir'], 'logs')
    mkdir_p(config['logs_dir'])
    config['apps_dir'] = os.path.join(config['base_dir'], 'apps')

    config['bm_suite'] = config['program'].split('-')[0]
    config['bm_name' ] = config['program'].split('-')[1]
    config['bm_input'] = config['program'].split('-')[2]
    config['bm_fullname'] = get_fullname(config['bm_name'])
    path_suffix = os.path.join(config['bm_suite'], config['bm_name'], 'ref', f"input_{config['bm_input']}")
    config['path_suffix'] = path_suffix

    config['profiling_dir']  = os.path.join(config['data_dir'], 'profiling', config['config'], path_suffix)
    mkdir_p(config['profiling_dir'])

    config['app_dir'] = os.path.join(config['apps_dir'], config['bm_suite'], config['bm_fullname'], 'ref')
    config['app_cfg'] = os.path.join(config['app_dir'], '.'.join([config['bm_fullname'], config['bm_input'], 'cfg']))

    return config

def get_app_option(config, option:str):
    with open(config['app_cfg']) as f:
        for line in f:
            if line.startswith(option):
                return line.split(':', 1)[1].strip()
    raise ValueError(f"No {option} in the app config")

def check_app_option(config, option:str):
    with open(config['app_cfg']) as f:
        for line in f:
            if line.startswith(option):
                return True
    return False

def list_executable_elf_files(directory):
    # List all files in the directory
    files_in_directory = os.listdir(directory)
    # Filter the list to only include executable ELF files
    executable_elf_files = [file for file in files_in_directory if is_executable_elf(os.path.join(directory, file))]
    return executable_elf_files

def is_executable_elf(file_path):
    # Use the 'file' command to get the file type
    file_type = subprocess.check_output(['file', '-b', file_path]).decode()
    # Check if the file type is 'ELF' and 'executable'
    return 'ELF' in file_type and 'executable' in file_type

def get_app_bin(config):
    bin_dir = os.path.join(config['apps_dir'], config['bm_suite'], config['bm_fullname'])
    candidate_bins = list_executable_elf_files(bin_dir)
    if len(candidate_bins) != 1:
        raise ValueError(f"Multiple or no executable files in {bin_dir}")
    return os.path.join(bin_dir, candidate_bins[0])

def linkfiles(src, dest, exclude=None):
    for i in glob.iglob(os.path.join(src, "*")):
        if exclude and exclude in os.path.basename(i):
            continue
        d = os.path.join(dest, os.path.basename(i))
        try:
            os.symlink(i, d)
        except OSError as e:
            if e.errno == errno.EEXIST:
                print("[PREPROCESS] File", i, "exists; skipping.")

def ex(cmd, cwd=".", env=None):
    proc = subprocess.Popen(["bash", "-c", cmd], cwd=cwd, env=env)
    proc.communicate()

def ex_log(cmd, log_file, cwd=".", env=None):
    import time
    with open(log_file, "a") as f:
        f.write("[cwd] %s\n" % cwd)
        f.write("[command] %s\n" % cmd)
        f.write("[begin time] %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    cmd += f" 2>&1 | tee -a {log_file}"
    ex(cmd, cwd, env)
    with open(log_file, "a") as f:
        f.write("[end time] %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))

def get_fullname(raw):
    name_mapper = {
        "STREAM": "STREAM",
    }
    return name_mapper[raw]
