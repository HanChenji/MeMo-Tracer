#!/usr/bin/env python
import argparse
import os, shutil
import numpy as np
import pandas as pd
from scripts import utils


def parse_args():
    if 'ZSIMDIR' not in os.environ:
        os.environ['ZSIMDIR'] = os.path.dirname(os.path.realpath(__file__))
    base_dir = os.environ['ZSIMDIR']

    parser = argparse.ArgumentParser(description="Run ZSim Arguments")
    parser.add_argument("--base-dir", type=str, default=base_dir, help="Base directory")
    parser.add_argument("--job-nums", "-n", dest="job_nums", type=int, default=1, help="number of jobs")
    parser.add_argument("--threads", "-j", dest="threads", type=int, default=1, help="Number of threads")
    parser.add_argument("--job-list", "-l", dest="job_list", type=str, nargs='+', help="file of the job list")
    parser.add_argument("--program","-p",dest="program", type=str, help="name of workload")
    parser.add_argument("--task", "-t",dest="task", type=str, help="type of analysis routine")
    parser.add_argument("--config", type=str, default="IssueModelx1", help="Path to the config file")
    # options for profiling
    parser.add_argument("--profiling-force", action="store_true", help="Force to do profiling")
    parser.add_argument("--profiling-order", type=int, default=0, help="Order of the profiling routine")
    parser.add_argument("--profiling-slice-size", type=int, default=100000000, help="Size of the slice during profiling")
    parser.add_argument("--profiling-emit-first", type=bool, default=True, help="Emit the first slice")
    parser.add_argument("--profiling-emit-last", type=bool, default=True, help="Emit the last slice")

    config = vars(parser.parse_args())

    config['zsim_bin'] = os.path.join(config['base_dir'], 'build/opt/zsim')


    return config

class ZSimRunner:
    def __init__(self, config:dict):
        self.config = config

    def do_profiling(self):
        import libconf
        import tempfile

        # check if profiling is already done
        zsim_log = os.path.join(self.config['profiling_dir'], 'zsim.log.0')
        # check if zsim_log contains 'Finished, code 0'
        if os.path.exists(zsim_log) and 'Finished, code 0' in open(zsim_log).read() and not self.config['profiling_force']:
            self.logger.info(f"Profiling already done for {self.config['program']}")
            return

        with open(os.path.join('config', f"{self.config['config']}.cfg"), 'r') as f:
            zsim_cfg = libconf.load(f)
        zsim_cfg['sim'] = {
            'slice_size'   : self.config['profiling_slice_size'],
            'emit_first'   : self.config['profiling_emit_first'],
            'emit_last'    : self.config['profiling_emit_last' ],
            'outputDir'    : self.config['profiling_dir'],
            'logToFile'    : True,
            'strictConfig' : False,
            'parallelism'  : 1,
            'schedQuantum' : 100000000,
        }
        zsim_cfg['process0'] = {
            'command' : utils.get_app_option(self.config, 'command'),
        }
        if utils.check_app_option(self.config, 'stdin'):
            zsim_cfg['process0']['input'] = utils.get_app_option(self.config, 'stdin')
        if utils.check_app_option(self.config, 'loader'):
            zsim_cfg['process0']['loader'] = utils.get_app_option(self.config, 'load')
        if utils.check_app_option(self.config, 'env'):
            zsim_cfg['process0']['env'] = utils.get_app_option(self.config, 'env')
        if utils.check_app_option(self.config, 'heap'):
            zsim_cfg['sim']['gmMBytes'] = int(utils.get_app_option(self.config, 'heap'))

        run_dir = tempfile.mkdtemp()
        with open(os.path.join(run_dir, 'zsim.cfg'), 'w') as f:
            libconf.dump(zsim_cfg, f)
        profling_cmd = f"{self.config['zsim_bin']} zsim.cfg"

        # link files and dirs from self.config['app_dir] to run_dir
        utils.linkfiles(self.config['app_dir'], run_dir)
        # link the binary to run_dir and name it as base.exe
        os.symlink(utils.get_app_bin(self.config), os.path.join(run_dir, 'base.exe'))

        # run!
        self.logger.info(f"Running {profling_cmd}")
        utils.ex_log(profling_cmd, log_file=self.config['log_file'], cwd=run_dir)

        # remove the run_dir
        shutil.rmtree(run_dir)

    
    def do_concatenating(self):
        from scripts.H5Reader import H5Reader

        def get_stat(model):
            profiling_dir = os.path.join(self.config['data_dir'], 'profiling', model, self.config['path_suffix'])
            core_stats = H5Reader(profiling_dir)
            return core_stats

        arch_range = ['x1', 'x2', 'x4', 'x8', 'x16']

        features = []

        l1d_miss_rate = []
        l2_miss_rate  = []
        llc_miss_rate = []
        mem_avg_lat   = []
        for model in [f'CacheModel{arch}' for arch in arch_range]:
            core_stats = get_stat(model)
            l1d_miss_rate.append(core_stats.l1d_miss_rate())
            l2_miss_rate.append (core_stats.l2_miss_rate())
            llc_miss_rate.append(core_stats.llc_miss_rate())
            mem_avg_lat.append(core_stats.get_cache_subsystem_avg_lat())
            features.append(f'{model}-l1d_miss_rate')
            features.append(f'{model}-l2_miss_rate')
            features.append(f'{model}-llc_miss_rate')
            features.append(f'{model}-mem_avg_lat')
        l1d_miss_rate = np.array(l1d_miss_rate).T
        l2_miss_rate  = np.array(l2_miss_rate).T
        llc_miss_rate = np.array(llc_miss_rate).T
        mem_avg_lat   = np.array(mem_avg_lat).T

        l1i_miss_rate = []
        for model in ['FetchModel-cachex1', 'FetchModel-cachex2', 'FetchModel-x4', 'FetchModel-cachex8', 'FetchModel-cachex16']:
            core_stats = get_stat(model)
            l1i_miss_rate.append(core_stats.l1i_miss_rate())
            features.append('f{model}-l1i_miss_rate')
        l1i_miss_rate = np.array(l1i_miss_rate).T

        fetch_stalls = []
        for model in ['FetchModel-widthx1', 'FetchModel-widthx2', 'FetchModel-x4', 'FetchModel-widthx8', 'FetchModel-widthx16']:
            core_stats = get_stat(model)
            fetch_stalls.append(core_stats.fetch_stalls())
            features.append('f{model}-fetch_stalls')
        fetch_stalls = np.array(fetch_stalls).T

        br_misses = []
        for model in ['FetchModel-bpx1', 'FetchModel-bpx2', 'FetchModel-x4', 'FetchModel-bpx8', 'FetchModel-bpx16']:
            core_stats = get_stat(model)
            br_misses.append(core_stats.br_misses())
            features.append('f{model}-br_mpki')
        br_misses = np.array(br_misses).T

        issue_stalls = []
        for model in [f'IssueModel{arch}' for arch in arch_range]:
            core_stats = get_stat(model)
            issue_stalls.append(core_stats.issue_stalls())
            features.append('f{model}-issuee_stalls')
        issue_stalls = np.array(issue_stalls).T

        icount = get_stat('IssueModelx1').core_instrs()
        spawned_icount = np.array([icount] * br_misses.shape[1]).T

        br_mpki      = br_misses    / spawned_icount * 1000
        fetch_stalls = fetch_stalls / spawned_icount
        issue_stalls = issue_stalls / spawned_icount

        memo = np.column_stack((
            l1d_miss_rate, l2_miss_rate, llc_miss_rate, mem_avg_lat,
            l1i_miss_rate, fetch_stalls, br_mpki,
            issue_stalls,
        ))

        dump_dir = os.path.join(config['base_dir'], 'output', self.config['path_suffix'])
        utils.mkdir_p(dump_dir)

        memo_df = pd.DataFrame(memo, columns=features)
        memo_df.to_csv(os.path.join(dump_dir, 'memo.csv'), index=False)

        return 

    def run(self, program):
        self.config['program'] = program
        self.config = utils.update_config(self.config)

        if self.config['task'] == 'profiling':
            self.logger_name = '-'.join([self.config['task'], self.config['program'], self.config['config']])
        else:
            self.logger_name = '-'.join([self.config['task'], self.config['program']])

        self.config['log_file'] = os.path.join(self.config['logs_dir'], self.logger_name)
        self.logger = utils.set_logger(self.config['log_file'])

        if self.config['task'] == 'profiling':
            self.do_profiling()
        elif self.config['task'] == 'concatenating':
            self.do_concatenating()
        else:
            raise ValueError("Invalid analysis routine")

def single_run(program, config):
    zsim_runner = ZSimRunner(config)
    zsim_runner.run(program)

if __name__ == "__main__":
    config = parse_args()

    programs = []
    if config['job_list']:
        for job_file in config['job_list']:
            with open(job_file, 'r') as f:
                for line in f:
                    if not line.startswith('#') and line.strip() != '':
                        programs.append(line.strip())
    else:
        programs.append(config['program'])

    # parallelize programs
    import multiprocessing
    pool = multiprocessing.Pool(config['job_nums'])
    pool.starmap(single_run, [(program, config) for program in programs])
    pool.close()
    pool.join()
