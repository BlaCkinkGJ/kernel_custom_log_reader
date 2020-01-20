#!/usr/bin/python3

import time
import json
import pprint
import copy
import curses
import argparse
import base64
import zlib

def readline(log_file, sep='\n'):
    line_buffer = ""
    data = log_file.read(1).decode()
    while data != '\n':
        line_buffer += data
        data = log_file.read(1).decode()
    line_buffer = line_buffer.encode('ascii')
    line_buffer = base64.b85decode(line_buffer)
    line_buffer = zlib.decompress(line_buffer)
    line_buffer = line_buffer.decode('utf-8')
    return line_buffer

# @reference: https://stackoverflow.com/questions/20656135/python-deep-merge-dictionary-dataor 
def merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination

def check_change(original_stack, change_dict):
    stack = copy.deepcopy(original_stack)
    value = change_dict
    while stack != [] and value != None:
        key = stack.pop(0)
        value = value.get(key)
    return value

row = 0
axis = 0
def draw_screen(log_dict, stdscr, change_dict, offset = 0, stack = []):
    global row, axis
    max_row, max_col = stdscr.getmaxyx()

    for key, value in log_dict.items():
        row += 1
        stack.append(key)
        if row > max_row - 5:
            axis += 30
            row = 1

        if isinstance(value, dict):
            draw_str = "{}{}:".format("".join(['.' for _ in range(offset)]),key)
            stdscr.addstr(row, axis, draw_str, curses.color_pair(0))
            next_stack = copy.deepcopy(stack)
            draw_screen(value, stdscr, change_dict, offset + 2, next_stack)
        else:
            draw_str = "{}{}: {}".format("".join(['.' for _ in range(offset)]),key, value)
            if check_change(stack, change_dict) != None:
                stdscr.addstr(row, axis, draw_str, curses.color_pair(1))
            else:
                stdscr.addstr(row, axis, draw_str, curses.color_pair(0))
        stack.pop()

def replay_log_file(log_file):
    log_buffer = None
    start_time = time.time()
    stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(0, curses.COLOR_WHITE, -1)
    curses.init_pair(1, curses.COLOR_RED, -1)
    while log_file.read(1):
        log_file.seek(log_file.tell() - 1)
        stdscr.clear()
        current_time = time.time()
        data = json.loads(readline(log_file))
        if log_buffer == None:
            log_buffer = copy.deepcopy(data)
        else:
            merge(data, log_buffer)
        checkpoint = log_buffer['time']
        del log_buffer['time']
        gap = checkpoint - (current_time - start_time)
        if gap > 0:
            time.sleep(gap)
        stdscr.addstr(0,0,"=========== {} ===========".format(checkpoint))
        global row, axis
        row = 0
        axis = 0
        draw_screen(log_buffer, stdscr, data)
        stdscr.refresh()
    curses.endwin()

def serialize_log_buffer(json_file, result = {}, current = ""):
    for key, value in json_file.items():
        if isinstance(value, dict):
            next_current = "{}{}-".format(current, key)
            serialize_log_buffer(value, result, next_current)
        else:
            result["{}{}".format(current, key)] = value

def save_log_file_to_csv(log_file, result_file):
    log_buffer = None
    serial_log_buffer = {}
    need_header = True
    while log_file.read(1):
        log_file.seek(log_file.tell() - 1)
        data = json.loads(readline(log_file))
        if log_buffer == None:
            log_buffer = copy.deepcopy(data)
        else:
            merge(data, log_buffer)
        serialize_log_buffer(log_buffer, serial_log_buffer)
        if need_header == True:
            for key in serial_log_buffer.keys():
                result_file.write("{},".format(key))
            result_file.seek(result_file.tell() - 1)
            result_file.write("\n")
            need_header = False

        for value in serial_log_buffer.values():
            result_file.write("{},".format(value))
        result_file.seek(result_file.tell() - 1)
        result_file.write("\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Custom kernel log parser')
    parser.add_argument('-p', '--path', type=str, default="result.log",
            metavar='log_file_path',
            help='set log file path')
    parser.add_argument('-r', '--replay', default=False,
            help='replay the log file',
            action='store_true')
    parser.add_argument('-s', '--save', default=False,
            help='original log file to full log csv files',
            action='store_true')

    args = parser.parse_args()
    log_file = open(args.path, "rb")
    if args.replay:
        print("start the replay")
        replay_log_file(log_file)
    if args.save:
        print("start the save")
        result_file = open("result.csv", "w")
        save_log_file_to_csv(log_file, result_file)
        result_file.close()
        print("save complete")
    log_file.close()
