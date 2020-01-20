#!/usr/bin/python3

from multiprocessing import Process, Queue
import json
import time
import copy
import jsondiff
import time
import argparse
import zlib
import base64

program_start_time = time.time()

def log_write(log_file, log_buffer, secs=1.0):
    previous_data = {} 
    while True:
        if not log_buffer.empty():
            data = log_buffer.get()
            diff_result = jsondiff.diff(previous_data, data)
            if diff_result != {}:
                if [str(key) for key in diff_result.keys()][0] == '$replace':
                    diff_result = copy.deepcopy(list(diff_result.values())[0])
                diff_result['time'] = time.time() - program_start_time
                # compress sequence
                diff_result = json.dumps(diff_result)
                diff_result = diff_result.encode('utf-8')
                diff_result = zlib.compress(diff_result, level=9)
                diff_result = base64.b85encode(diff_result)
                diff_result = diff_result.decode('ascii')
                # write sequence
                log_file.write("{}\n".format(diff_result).encode())
            previous_data = copy.deepcopy(data)
        else:
            time.sleep(secs)


def log_read_process(file_path, secs = 1.0):
    original_file = open(file_path, "r")
    while True:
        try:
            data = json.loads(original_file.readline())
            log_buffer.put(data)
            original_file.seek(0)
            time.sleep(secs)
        except Exception as e:
            print("Exception({}): {}".format(__func__, e))
            break
    original_file.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Custom kernel log parser')
    parser.add_argument('-p', '--path', type=str, default="/sys/block/mydevice/pblk/lines",
            metavar='json_log_file_path',
            help='set log file path')
    parser.add_argument('-r', '--read', type=float, default=1.0,
            metavar='read_timer',
            help='set read timer time (default: 1.0)')
    parser.add_argument('-w', '--write', type=float, default=1.0,
            metavar='write_timer',
            help='set write timer time (default: 1.0)')

    args = parser.parse_args()
    log_file = open("result.log", 'wb', 0)
    log_buffer = Queue()
    log_write_process = Process(target=log_write, args=(log_file, log_buffer, args.write))
    log_write_process.start()
    log_read_process(args.path, args.read)
    log_write_process.terminate()
    log_file.close()
