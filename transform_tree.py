#!/usr/bin/env python
"""Transform a directory tree by file"""

import argparse
import sys
import os
import subprocess
import shutil
import logging

def real_dir(path):
    if os.path.isdir(path):
        return path
    else:
        msg = "%s is not a directory" % path
        raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('source', metavar='SOURCE', type=real_dir)
parser.add_argument('dest', metavar='DEST', nargs='?', default='.')
parser.add_argument('-f', '--force', action='store_true')
parser.add_argument('-i', '--interactive', action='store_true')
parser.add_argument('-q', '--quiet', action='store_true')
parser.add_argument('-v', '--verbose', action='count')
parser.add_argument('-n', '--dry-run', action='store_true')
parser.add_argument('-c', '--convert', metavar='CONVERTER')
parser.add_argument('-r', '--rename', metavar='RENAMER')
rename_group = parser.add_mutually_exclusive_group()
rename_group.add_argument('--rename-file', action='store_true')
rename_group.add_argument('--rename-path', action='store_true')
op_group = parser.add_mutually_exclusive_group()
op_group.add_argument('-p', '--in-place', action='store_true')
op_group.add_argument('-l', '--link', action='store_true')
op_group.add_argument('-s', '--symbolic-link', action='store_true')

def main():
    return walk_tree(args.source, args.dest)

def make_renamer():
    rename_map = {}
    def pipe_rename(path):
        if path not in rename_map.keys():
            renamer = subprocess.Popen(args.rename, shell=True,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            (newpath, err) = renamer.communicate(path)
            rename_map[path] = newpath
            logging.debug('%s renamed to %s', path, newpath)
        return rename_map[path]

    def rename_file(path):
        (head, tail) = os.path.split(path)
        renamed_tail = pipe_rename(tail)
        return os.path.join(head, renamed_tail)

    def rename_path(path):
        return pipe_rename(path)

    def rename_elements(path):
        elements = path.split(os.path.sep)
        renamed_elements = map(pipe_rename, elements)
        return os.path.join(*renamed_elements)

    if not args.rename:
        return lambda x: x
    elif args.rename_file:
        return rename_file
    elif args.rename_path:
        return rename_path
    else:
        return rename_elements

def walk_tree(source, dest):
    new_dir = os.path.basename(source) # depends on trailing forward-slash
    for root, dirs, files in os.walk(source):
        logging.debug("in %s", root)
        rel_path = os.path.relpath(root, source)
        rel_dest_dir = os.path.join(new_dir, rel_path)

        if not files:
            make_dirs(RENAMED(rel_dest_dir))

        for file in files:
            logging.debug("handling file %s", file)
            transform_file(file, root, rel_dest_dir, dest)
    return 0

def transform_file(file, source_dir, rel_dest_dir, dest_root):
    source_path = os.path.join(source_dir, file)
    rel_dest_path = RENAMED(os.path.join(rel_dest_dir, file))
    dest_path = os.path.normpath(os.path.join(dest_root, rel_dest_path))
    dest_dir = os.path.dirname(dest_path)

    if not is_subdir(rel_dest_dir, dest_root):
        logging.error('file %s outside destination', rel_dest_path)
        return

    make_dirs(dest_dir)

    if args.link:
        transform_function = os.link
    elif args.symbolic_link:
        transform_function = os.symlink
    else:
        transform_function = shutil.copy

    do_transform(transform_function, source_path, dest_path)

def do_transform(function, source_path, dest_path):
    if args.interactive:
        pass #TODO
    if not args.dry_run:
        function(source_path, dest_path)

def make_dirs(path):
    if os.path.isdir(path):
        logging.debug("%s dir exists, skipping", path)
    elif os.path.lexists(path):
        logging.error('%s exists and is not a directory', path)
    else:
        logging.debug("%s dir doesn't exist, creating", path)
        if not args.dry_run:
            os.makedirs(path)

def is_subdir(dir, root):
    root = os.path.join(os.path.realpath(root),'')
    dir = os.path.join(os.path.realpath(dir),'')
    logging.debug('check %s inside %s', dir, root)
    return root == os.path.commonprefix([dir, root])

def log_level():
    if args.quiet:
        return logging.ERROR
    elif args.verbose == 1:
        return logging.INFO
    elif args.verbose >= 2:
        return logging.DEBUG
    else:
        return logging.WARNING

if __name__ == '__main__':
    args = parser.parse_args()
    logging.basicConfig(level=log_level())
    RENAMED = make_renamer()
    sys.exit(main())
