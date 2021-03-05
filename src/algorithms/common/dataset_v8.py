# -*- coding: utf-8 -*-
"""
@author: "Dickson Owuor"
@credits: "Anne Laurent"
@license: "MIT"
@version: "8.0"
@email: "owuordickson@gmail.com"
@created: "12 July 2019"
@modified: "08 Mar 2021"

Changes
-------
1. Chunks CSV file read

"""
import gc
import os
from pathlib import Path
from dateutil.parser import parse
import h5py
import time
import numpy as np
import pandas as pd


class Dataset:

    def __init__(self, file_path):  # , c_size, min_sup, eq=False):
        self.h5_file = 'app_data/' + str(Path(file_path).stem) + str('.h5')
        if os.path.exists(self.h5_file):
            print("Fetching data from h5 file")
            h5f = h5py.File(self.h5_file, 'r')
            self.titles = h5f['dataset/titles'][:]
            self.time_cols = h5f['dataset/time_cols'][:]
            self.attr_cols = h5f['dataset/attr_cols'][:]
            size = h5f['dataset/size_arr'][:]
            self.col_count = size[0]
            # self.row_count = size[1]
            # valid_count = size[2]
            # self.used_chunks = size[3]
            # self.skipped_chunks = size[4]
            h5f.close()
            # self.thd_supp = min_sup
            # if valid_count < 3:
            #    self.no_bins = True
            # else:
            #    self.no_bins = False
        else:
            self.csv_file = file_path
            # self.thd_supp = min_sup
            # self.equal = eq
            # self.chunk_size = c_size
            self.titles, self.col_count, self.time_cols = Dataset.read_csv_header(file_path)
            self.attr_cols = self.get_attr_cols()
        self.row_count = 0  # TO BE UPDATED
        self.used_chunks = 0
        self.skipped_chunks = 0
        self.save_to_hdf5()
        # self.no_bins = False
        # self.init_gp_attributes()

    def get_attr_cols(self):
        all_cols = np.arange(self.col_count)
        attr_cols = np.setdiff1d(all_cols, self.time_cols)
        return attr_cols

    def save_to_hdf5(self):
        # 1. Initiate HDF5 file
        h5f = h5py.File(self.h5_file, 'w')
        h5f.create_dataset('dataset/titles', data=self.titles)
        h5f.create_dataset('dataset/time_cols', data=self.time_cols.astype('u1'))
        h5f.create_dataset('dataset/attr_cols', data=self.attr_cols.astype('u1'))
        h5f.create_dataset('dataset/size_arr', data=np.array([self.col_count]))
        h5f.close()

    def read_csv_data(self, col, c_size):
        if self.titles.dtype is np.int32:
            chunk = pd.read_csv(self.csv_file, sep="[;,' '\t]", usecols=[col], chunksize=c_size, header=None,
                                engine='python')
        else:
            chunk = pd.read_csv(self.csv_file, sep="[;,' '\t]", usecols=[col], chunksize=c_size, engine='python')
        return chunk

    def print_header(self):
        str_header = "Header Columns/Attributes\n-------------------------\n"
        for txt in self.titles:
            try:
                str_header += (str(txt.key) + '. ' + str(txt.value.decode()) + '\n')
            except AttributeError:
                try:
                    str_header += (str(txt[0]) + '. ' + str(txt[1].decode()) + '\n')
                except IndexError:
                    str_header += (str(txt) + '\n')
        return str_header

    @staticmethod
    def read_csv_header(file):
        try:
            df = pd.read_csv(file, sep="[;,' '\t]", engine='python', nrows=1)
            header_row = df.columns.tolist()

            if len(header_row) <= 0:
                print("CSV file is empty!")
                raise Exception("CSV file read error. File has little or no data")
            else:
                print("Header titles fetched from CSV file")
                # 2. Get table headers
                if header_row[0].replace('.', '', 1).isdigit() or header_row[0].isdigit():
                    titles = np.arange(len(header_row))
                else:
                    if header_row[1].replace('.', '', 1).isdigit() or header_row[1].isdigit():
                        titles = np.arange(len(header_row))
                    else:
                        # titles = self.convert_data_to_array(data, has_title=True)
                        keys = np.arange(len(header_row))
                        values = np.array(header_row, dtype='S')
                        titles = np.rec.fromarrays((keys, values), names=('key', 'value'))
                del header_row
                gc.collect()
                return titles, titles.size, Dataset.get_time_cols(df.values)
        except Exception as error:
            print("Unable to read 1st line of CSV file")
            raise Exception("CSV file read error. " + str(error))

    @staticmethod
    def get_time_cols(data):
        # Retrieve first column only
        time_cols = list()
        # n = len(data)
        for i in range(data.shape[1]):  # check every column/attribute for time format
            row_data = str(data[0][i])
            try:
                time_ok, t_stamp = Dataset.test_time(row_data)
                if time_ok:
                    time_cols.append(i)
            except ValueError:
                continue
        return np.array(time_cols)

    @staticmethod
    def test_time(date_str):
        # add all the possible formats
        try:
            if type(int(date_str)):
                return False, False
        except ValueError:
            try:
                if type(float(date_str)):
                    return False, False
            except ValueError:
                try:
                    date_time = parse(date_str)
                    t_stamp = time.mktime(date_time.timetuple())
                    return True, t_stamp
                except ValueError:
                    raise ValueError('no valid date-time format found')
