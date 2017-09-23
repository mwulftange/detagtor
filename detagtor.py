#!/usr/bin/env python

# Copyright (c) Markus Wulftange (@mwulftange)

from __future__ import print_function
import os,sys
import argparse
from braceexpand import braceexpand
from fnmatch import fnmatch
from collections import OrderedDict
import subprocess
import hashlib
import re
import json
import urllib3
import urlparse


ARGS = None
FNULL = open(os.devnull, 'w')


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BraceExpandAction(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        attr_value = getattr(namespace, self.dest)
        if attr_value is None:
            attr_value = []
        attr_value.extend(list(braceexpand(value)))
        setattr(namespace, self.dest, attr_value)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Detect tagged versions of a web application.',
        epilog='Use the \'index\' command to build a knowledge base of a source code repository. Then use the \'detect\' command to run the tag detection against a web application based on the knowledge base.'
    )

    # sub-parser for the commands 'index' and 'detect'
    subparsers = parser.add_subparsers(dest='command', help='command to run; use \'detagtor.py <command> -h\' for help on command')

    # argparser for 'index' command arguments
    index_parser = subparsers.add_parser(
        'index',
        help='index a source code repository',
        epilog='PATTERN allows glob and brace expansion expressions. For example, \'--include "*.{css,js}"\' will match any file ending with \'.css\' or \'.js\'.'
    )
    index_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='print verbose status information'
    )
    index_parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        type=argparse.FileType('w'),
        default=sys.stdout,
        help='file to write index to; defaults to STDOUT'
    )

    pattern_group = index_parser.add_argument_group(
        'Inclusion and Exclusion',
        'Include or exclude files and directories based on PATTERN matching.'
    )
    pattern_group.add_argument(
        '--include',
        metavar='PATTERN',
        action=BraceExpandAction,
        help='include only files whose base name matches PATTERN'
    )
    pattern_group.add_argument(
        '--include-dir',
        metavar='PATTERN',
        action=BraceExpandAction,
        help='include only directories whose base name matches PATTERN'
    )
    pattern_group.add_argument(
        '--include-prefix',
        metavar='PATTERN',
        action=BraceExpandAction,
        help='include only directories whose path matches the PATTERN as prefix'
    )
    pattern_group.add_argument(
        '--exclude',
        metavar='PATTERN',
        action=BraceExpandAction,
        help='exclude all files whose base name matches PATTERN'
    )
    pattern_group.add_argument(
        '--exclude-dir',
        metavar='PATTERN',
        action=BraceExpandAction,
        help='exclude all directories whose base name matches PATTERN'
    )
    pattern_group.add_argument(
        '--exclude-prefix',
        metavar='PATTERN',
        action=BraceExpandAction,
        help='exclude all directories whose path matches the PATTERN as prefix'
    )

    # argparser for 'detect' command arguments
    detect_parser = subparsers.add_parser('detect', help='detect the tagged versions of a web application')

    detect_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='print verbose status information'
    )
    detect_parser.add_argument(
        'url',
        help='base URL'
    )
    detect_parser.add_argument(
        '-H', '--header',
        action='append',
        help='extra header to include in the request'
    )
    detect_parser.add_argument(
        '-i', '--input',
        metavar='FILE',
        type=argparse.FileType('r'),
        default=sys.stdin,
        help='index file to read from; defaults to STDIN'
    )
    detect_parser.add_argument(
        '-c', '--config',
        type=argparse.FileType('r'),
        help='config file to read'
    )
    detect_parser.add_argument(
        '--exhaustive',
        action='store_true',
        help='disable optimization'
    )

    args = parser.parse_args()

    return args


def print_status(msg, end='\n'):
    print(msg, end=end, file=sys.stderr)


def is_git():
    proc = subprocess.Popen(['git', 'status'], stdout=FNULL, stderr=FNULL)
    proc.wait()
    return proc.returncode == 0


def get_tags():
    proc = subprocess.Popen(['git', 'tag'], stdout=subprocess.PIPE, stderr=FNULL)
    return [line.rstrip('\r\n') for line in proc.stdout]


def is_dir_included(path):
    is_included = True
    basename = os.path.basename(path)
    path = path + '/'
    if is_included and ARGS.include_prefix is not None and len(ARGS.include_prefix) > 0:
        is_included = is_included and any([path.startswith(p+'/') for p in ARGS.include_prefix])
    elif ARGS.include_dir is not None and len(ARGS.include_dir) > 0:
        is_included = is_included and any([fnmatch(basename, p) for p in ARGS.include_dir])
    if is_included and ARGS.exclude_prefix is not None and len(ARGS.exclude_prefix) > 0:
        is_included = is_included and not any([path.startswith(p+'/') for p in ARGS.exclude_prefix])
    if is_included and ARGS.exclude_dir is not None and len(ARGS.exclude_dir) > 0:
        is_included = is_included and not any([fnmatch(basename, p) for p in ARGS.exclude_dir])
    return is_included


def is_file_included(path):
    is_included = True
    basename = os.path.basename(path)
    if is_included and ARGS.include is not None and len(ARGS.include) > 0:
        is_included = is_included and any([fnmatch(basename, p) for p in ARGS.include])
    if is_included and ARGS.exclude is not None and len(ARGS.exclude) > 0:
        is_included = is_included and not any([fnmatch(basename, p) for p in ARGS.exclude])
    return is_included


def get_files(tag):
    proc = subprocess.Popen(['git', 'checkout', tag], stdout=FNULL, stderr=FNULL)
    proc.wait()

    queue = []
    if ARGS.include_prefix is not None and len(ARGS.include_prefix) > 0:
        queue.extend(ARGS.include_prefix)
    files = []

    i = 0
    while i < len(queue):
        file = queue[i]
        i = i + 1
        if os.path.isdir(file):
            if not is_dir_included(file):
                continue
            dirlist = os.listdir(file)
            if dirlist is not None:
                queue.extend([file + '/' + f for f in dirlist])
        elif os.path.isfile(file):
            if not is_file_included(file):
                continue
            files.append(file[2:])

    return files


def hash_file(f):
    h = hashlib.sha1()
    for b in iter(lambda : f.read(0x100), b''):
        h.update(b)
    return h.hexdigest()


def sort_index(t):
    file_versions = t[1]
    file_tags = [item for sublist in file_versions.values() for item in sublist]
    file_tags_uniq = list(set(file_tags))

    return -len(file_versions) * (len(file_tags_uniq) / len(file_tags))


def run_index():
    if not is_git():
        raise Exception('must be execution within a git repository') 

    if ARGS.include_prefix is None:
        ARGS.include_prefix = ['.']
    if ARGS.exclude_dir is None:
        ARGS.exclude_dir = []
        ARGS.exclude_dir.append('.git')

    if ARGS.include_prefix is not None:
        ARGS.include_prefix = [p if p == '.' or p.startswith('./') else './'+p for p in ARGS.include_prefix]
    if ARGS.exclude_prefix is not None:
        ARGS.exclude_prefix = [p if p == '.' or p.startswith('./') else './'+p for p in ARGS.exclude_prefix]

    index = {}

    tags = get_tags()
    if len(tags) == 0:
        raise Exception('no tags found')

    for tag in tags:
        if ARGS.verbose:
            print_status('Processing tag \'%s\' ... ' % (tag), end='')

        n = 0
        files = get_files(tag)
        for file in files:
            with open(file, 'rb', buffering=0) as f:
                hash = hash_file(f)

            if file not in index:
                index[file] = {}
            if hash not in index[file]:
                index[file][hash] = []
            index[file][hash].append(tag)
            n = n + 1

        if ARGS.verbose:
            print_status('%d file(s) indexed' % (n))

    sorted_index = OrderedDict(sorted(index.items(), key=sort_index))

    ARGS.output.write(json.dumps(sorted_index.items()))


def run_detect():
    index = json.load(ARGS.input)
    config = {}
    http = urllib3.PoolManager()

    if ARGS.config is not None:
        config = json.load(ARGS.config)

    tags = set()
    tag_counts = {}
    for file, file_versions in index:
        if not ARGS.exhaustive and len(tags) > 0 and not any([t in tags for t in file_versions.values()[0]]):
            continue

        if 'patterns' in config:
            for pattern,repl in config['patterns'].iteritems():
                file = re.sub(pattern, repl, file)

        resp = http.request(
            'GET',
            urlparse.urljoin(ARGS.url, file),
            preload_content=False
        )
        if resp is None or resp.status != 200:
            continue

        hash = hash_file(resp)
        if hash not in file_versions:
            continue

        if ARGS.verbose:
            print_status('File \'%s\' found with hash \'%s\'' % (file, hash))

        for tag in file_versions[hash]:
            if tag not in tag_counts:
                tag_counts[tag] = 1
            else:
                tag_counts[tag] = tag_counts[tag] + 1

        if len(tags) == 0:
            tags = set(file_versions[hash])
        else:
            tags = tags.intersection(set(file_versions[hash]))

        if not ARGS.exhaustive and len(tags) == 1:
            print_status('Best matched tag: %s' % (tags.pop()))
            break

    tag_counts = OrderedDict(sorted(tag_counts.items(), key=lambda t: -t[1]))

    print_status('Matched tags in descending order: ', end='')
    print(json.dumps(tag_counts.items()))


if __name__ == '__main__':
    ARGS = parse_args()
    if ARGS.command == 'index':
        run_index()
    if ARGS.command == 'detect':
        run_detect()

