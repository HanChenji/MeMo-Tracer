import h5py as h5
import os
import numpy as np


class H5Reader:
    def __init__(self, profiling_dir):
        self.core       = 'MeMo'
        self.stats_file = os.path.join(profiling_dir, 'zsim.h5')
        if not os.path.exists(self.stats_file):
            raise ValueError(f"No file of {self.stats_file}")
        self.core_stats = self.get_core_stats()

    def get_core_stats(self):
        f = h5.File(self.stats_file, 'r')
        core_stats = f['stats']['root'][self.core]
        f.close()

        return core_stats

    def get_stats(self, name):
        raw_data    = self.core_stats[:][name].reshape(-1)
        sliced_data = raw_data[0::1]
        incre_data  = self.get_incre(sliced_data)

        return incre_data
    
    def get_incre(self, data):
        incre_data  = np.diff(data)
        incre_data  = np.insert(incre_data, 0, data[0])

        return incre_data
    
    def get_cache_miss_rate(self, name):
        f = h5.File(self.stats_file, 'r')
        cache_stats = f['stats']['root'][name]
        f.close()

        if 'l1' in name:
            hits = np.sum(
                cache_stats['fhGETS'] + cache_stats['fhGETX'] + cache_stats['hGETS'] + cache_stats['hGETX'],
            axis=-1)
        else:
            hits = np.sum(
                cache_stats['hGETS'] + cache_stats['hGETX'], 
            axis=-1)
        miss = np.sum(cache_stats['mGETS'] + cache_stats['mGETXIM'] + cache_stats['mGETXSM'], axis=-1)

        incre_hits = self.get_incre(hits)
        incre_miss = self.get_incre(miss)

        if np.any(incre_hits == 0):
            incre_hits[incre_hits == 0] = 1

        incre_all = incre_hits + incre_miss
        miss_rate = incre_miss / incre_all

        return miss_rate

    def get_cache_subsystem_avg_lat(self):
        f = h5.File(self.stats_file, 'r')
        cache_stats = f['stats']['root']['l1d']
        f.close()

        hits = np.sum(
            cache_stats['fhGETS'] + cache_stats['fhGETX'] + cache_stats['hGETS'] + cache_stats['hGETX'],
        axis=-1)
        miss = np.sum(
            cache_stats['mGETS'] + cache_stats['mGETXIM'] + cache_stats['mGETXSM'],
        axis=-1)
        accesses = hits + miss

        latency = np.sum(
            cache_stats['fhGETS_cycles'] + cache_stats['fhGETX_cycles'], 
        axis=-1)

        incre_lat = self.get_incre(latency)
        incre_accesses = self.get_incre(accesses)

        avg_lat = incre_lat / incre_accesses

        return avg_lat
    
    def br_misses(self):
        return self.get_stats('mispredBranches')

    def br_stalls(self):
        return self.get_stats('BrStalls')
    
    def br_mpki(self):
        return self.br_misses() / self.core_instrs() * 1000
    
    def l1i_miss_rate(self):
        return self.get_cache_miss_rate('l1i')
    
    def l1d_miss_rate(self):
        return self.get_cache_miss_rate('l1d')
    
    def l2_miss_rate(self):
        return self.get_cache_miss_rate('l2')
    
    def llc_miss_rate(self):
        return self.get_cache_miss_rate('l3')
    
    def fetch_stalls(self):
        return self.get_stats('fetchStalls')
    
    def decode_stalls(self):
        return self.get_stats('decodeStalls')
    
    def issue_stalls(self):
        return self.get_stats('issueStalls')

    def mpkis(self):
        return self.br_mpki()
    
    def core_instrs(self):
        return self.get_stats('icount')
    
    def cpis(self):
        self.core_cycles = self.get_stats('cycles')
        self.core_cpis   = self.core_cycles / self.core_instrs()

        return self.core_cpis
    
    def cpi_at(self, index):
        return self.core_cpis[index]

    def cycles(self):
        return self.core_cycles

    def instrs(self):
        return self.core_instrs()

    def cycle_at(self, index):
        return self.core_cycles[index]
    
    def instr_at(self, index):
        return self.core_instrs()[index]
