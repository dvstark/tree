# !usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under a 3-clause BSD license.
#
# @Author: Brian Cherinka
# @Date:   2018-07-14 14:31:36
# @Last modified by:   Brian Cherinka
# @Last Modified time: 2018-07-14 19:03:32

from __future__ import print_function, division, absolute_import
import sys
import os
import argparse
import glob
import shutil
import time


def _remove_link(link):
    ''' Remove a symlink if it exists

    Parameters:
        link (str):
            The symlink filepath
    '''
    if os.path.islink(link):
        os.remove(link)


def make_symlink(src, link):
    '''create a symlink

    Parameters:
        src (str):
            The fullpath source of the symlink
        link (str):
            The symlink file path
    '''
    _remove_link(link)
    os.symlink(src, link)


def create_index_table(environ, envdir):
    ''' create an html table
    
    Parameters:
        environ (dict):
            A tree environment dictionary
        envdir (str):
            The filepath for the env directory
    Returns:
        An html table definition string
    '''

    table_header = """<table id="list" cellpadding="0.1em" cellspacing="0">
<colgroup><col width="55%"/><col width="20%"/><col width="25%"/></colgroup>
<thead>
    <tr><th><a href="?C=N&O=A">File Name</a>&nbsp;<a href="?C=N&O=D">&nbsp;&darr;&nbsp;</a></th><th><a href="?C=S&O=A">File Size</a>&nbsp;<a href="?C=S&O=D">&nbsp;&darr;&nbsp;</a></th><th><a href="?C=M&O=A">Date</a>&nbsp;<a href="?C=M&O=D">&nbsp;&darr;&nbsp;</a></th></tr>
</thead><tbody>
    <tr><td><a href="../">Parent directory/</a></td><td>-</td><td>-</td></tr>"""
    table_footer = """</tbody></table>"""

    # create table
    table = table_header

    # loop over the environment
    for section, values in environ.items():
        if section == 'default':
            continue

        for tree_name, tree_path in values.items():
            skipmsg = 'Skipping {0} for {1}'.format(tree_name, section)
            if '_root' in tree_name:
                continue

            # create the src and target links
            src = tree_path
            link = os.path.join(envdir, tree_name.upper())

            # get the local time of the symlink
            try:
                stattime = time.strftime('%d-%b-%Y %H:%M', time.localtime(os.stat(src).st_mtime))
            except OSError:
                print("{0} does not appear to exist, skipping...".format(src))
                _remove_link(link)
                continue

            # skip the sas_base_dir
            if section == 'general' and 'sas_base_dir' in tree_name:
                print(skipmsg)
                continue

            # only create symlinks
            if section == 'general' and tree_name in ['cas_load', 'staging_data']:
                # only create links here if the target exist
                if os.path.exists(src):
                    make_symlink(src, link)
                else:
                    print(skipmsg)
            else:
                print('Processing {0} for {1}'.format(tree_name, section))
                make_symlink(src, link)
            
            # create the table entry
            if os.path.exists(link):
                table += '    <tr><td><a href="{0}/">{0}/</a></td><td>-</td><td>{1}</td></tr>\n'.format(tree_name.upper(), stattime)

    table += table_footer
    return table


def create_index_page(environ, defaults, envdir):
    ''' create the env index html page
    
    Builds the index.html page containing a table of symlinks
    to datamodel directories

    Parameters:
        environ (dict):
            A tree environment dictionary
        defaults (dict):
            The defaults dictionary from environ['default']
        envdir (str):
            The filepath for the env directory
    Returns:
        A string defintion of an html page
    '''

    # header of index file
    header = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><meta name="viewport" content="width=device-width"/><meta http-equiv="content-type" content="text/html; charset=utf-8"/><style type="text/css">body,html {{background:#fff;font-family:"Bitstream Vera Sans","Lucida Grande","Lucida Sans Unicode",Lucidux,Verdana,Lucida,sans-serif;}}tr:nth-child(even) {{background:#f4f4f4;}}th,td {{padding:0.1em 0.5em;}}th {{text-align:left;font-weight:bold;background:#eee;border-bottom:1px solid #aaa;}}#list {{border:1px solid #aaa;width:100%%;}}a {{color:#a33;}}a:hover {{color:#e33;}}</style>
<link rel="stylesheet" href="{url}/css/sas.css" type="text/css"/>
<title>Index of /sas/{name}/env/</title>
</head><body><h1>Index of /sas/{name}/env/</h1>
"""

    # footer of index file
    footer = """<h3><a href='{url}/sas/'>{location}</a></h3>
<p>This directory contains links to the contents of
environment variables defined by the tree product, version {name}.
To examine the <em>types</em> of files contained in each environment variable
directory, visit <a href="/datamodel/files/">the datamodel.</a></p>
</body></html>
"""
    # create index html file
    index = header.format(**defaults)
    index += create_index_table(environ, envdir)
    index += footer.format(**defaults)

    return index


def create_env(environ, mirror=None, verbose=None):
    ''' create the env symlink directory structure
    
    Creates the env folder filled with symlinks to datamodel directories
    for a given tree config file.  

    Parameters:
        environ (dict):
            A tree environment dictionary
        mirror (bool):
            If True, use the SAM url location
        verbose (bool):
            If True, print more information
    '''

    defaults = environ['default'].copy()
    defaults['url'] = "https://data.mirror.sdss.org" if mirror else "https://data.sdss.org"
    defaults['location'] = "SDSS-IV Science Archive Mirror (SAM)" if mirror else "SDSS-IV Science Archive Server (SAS)"

    if not os.path.exists(environ['general']['sas_root']):
        if verbose:
            print("{0} doesn't exist, skipping env link creation.".format(environ['general']['sas_root']))
        return

    if verbose:
        print("Found {0}.".format(environ['general']['sas_root']))

    # sets and creates envdir
    envdir = os.path.join(environ['general']['sas_root'], 'env')
    if not os.path.exists(envdir):
        os.makedirs(envdir)
    if not os.access(envdir, os.W_OK):
        return

    # create index html
    index = create_index_page(environ, defaults, envdir)

    # write the index file
    indexfile = os.path.join(envdir, 'index.html')
    with open(indexfile, 'w') as f:
        f.write(index)


def check_sas_base_dir(root=None):
    ''' Check for the SAS_BASE_DIR environment variable

    Will set the SAS_BASE_DIR in your local environment
    or prompt you to define one if is undefined

    Parameters:
        root (str):
            Optional override of the SAS_BASE_DIR envvar

    '''
    sasbasedir = root or os.getenv("SAS_BASE_DIR")
    if not sasbasedir:
        sasbasedir = input('Enter a path for SAS_BASE_DIR: ')
    os.environ['SAS_BASE_DIR'] = sasbasedir


def write_header(term='bash', tree_dir=None, name=None):
    ''' Write proper file header in a given shell format

    Parameters:
        term (str):
            The type of shell header to write, can be "bash", "tsch", or "modules"
        tree_dir (str):
            The path to this repository
        name (str):
            The name of the configuration

    Returns:
        A string header to insert
    '''

    assert term in ['bash', 'tsch', 'modules'], 'term must be either bash, tsch, or module'

    product_dir = tree_dir.rstrip('/')
    base = 'export' if term == 'bash' else 'setenv'

    if term != 'modules':
        hdr = """# Set up tree/{0} for {1}
{2} TREE_DIR {3}
{2} TREE_VER {1}
{2} PATH $TREE_DIR/bin:$PATH
{2} PYTHONPATH $TREE_DIR/python:$PYTHONPATH
                """.format(name, term, base, product_dir)
    else:
        hdr = """#%Module1.0
proc ModulesHelp {{ }} {{
    global product version
    puts stderr "This module adds $product/$version to various paths"
}}
set name tree
set product tree
set version {1}
conflict $product
module-whatis "Sets up $product/$version in your environment"

set PRODUCT_DIR {0}
setenv [string toupper $product]_DIR $PRODUCT_DIR
setenv [string toupper $product]_VER $version
prepend-path PATH $PRODUCT_DIR/bin
prepend-path PYTHONPATH $PRODUCT_DIR/python

                """.format(product_dir, name)

    return hdr.strip()


def write_version(name):
    ''' Make the default modules version string '''
    modules_version = "#%Module1.0\nset ModulesVersion {0}".format(name)
    return modules_version


def write_file(environ, term='bash', out_dir=None, tree_dir=None):
    ''' Write a tree environment file

    Loops over the tree environ and writes them out to a bash, tsch, or
    modules file

    Parameters:
        environ (dict):
            The tree dictionary environment
        term (str):
            The type of shell header to write, can be "bash", "tsch", or "modules"
        tree_dir (str):
            The path to this repository
        out_dir (str):
            The output path to write the files (default is etc/)

    '''

    # get the proper name, header and file extension
    name = environ['default']['name']
    header = write_header(term=term, name=name, tree_dir=tree_dir)
    exts = {'bash': '.sh', 'tsch': '.csh', 'modules': '.module'}
    ext = exts[term]

    # shell command
    if term == 'bash':
        cmd = 'export {0}={1}\n'
    else:
        cmd = 'setenv {0} {1}\n'

    # write the environment config files
    filename = os.path.join(out_dir, name + ext)
    with open(filename, 'w') as f:
        f.write(header + '\n')
        for key, values in environ.items():
            if key != 'default':
                # write separator
                f.write('#\n# {0}\n#\n'.format(key))
                # write tree names and paths
                for tree_name, tree_path in values.items():
                    f.write(cmd.format(tree_name.upper(), tree_path))

    # write default .version file for modules
    modules_version = write_version(name)
    if term == 'modules' and environ['default']['current']:
        version_name = os.path.join(out_dir, '.version')
        with open(version_name, 'w') as f:
            f.write(modules_version)


def get_tree(config=None):
    ''' Get the tree for a given config

    Parameters:
        config (str):
            The name of the tree config to load

    Returns:
        a Python Tree instance
    '''
    path = os.path.dirname(os.path.abspath(__file__))
    pypath = os.path.realpath(os.path.join(path, '..', 'python'))
    if pypath not in sys.path:
        sys.path.append(pypath)
    os.chdir(pypath)
    from tree.tree import Tree
    tree = Tree(config=config)
    return tree


def copy_modules(filespath=None, modules_path=None, verbose=None):
    ''' Copy over the tree module files into your path '''

    # find or define a modules path
    if not modules_path:
        modulepath = os.getenv("MODULEPATH")
        if not modulepath:
            modules_path = input('Enter the root path for your module files:')
        else:
            split_mods = modulepath.split(':')
            if len(split_mods) > 1:
                if verbose:
                    print('Multiple module paths found.  Using top one: {0}'.format(split_mods[0]))
            modules_path = split_mods[0]

    # check for the tree module directory
    tree_mod = os.path.join(modules_path, 'tree')
    if not os.path.isdir(tree_mod):
        os.makedirs(tree_mod)

    # copy the modules into the tree
    if verbose:
        print('Copying modules from etc/ into {0}'.format(tree_mod))
    module_files = glob.glob(os.path.join(filespath, '*.module'))
    for mfile in module_files:
        base = os.path.splitext(os.path.basename(mfile))[0]
        tree_out = os.path.join(tree_mod, base)
        shutil.copy2(mfile, tree_out)

    # copy the default version into the tree
    version = os.path.join(filespath, '.version')
    if os.path.isfile(version):
        shutil.copy2(version, tree_mod)


def parse_args():
    ''' Parse the arguments '''

    parser = argparse.ArgumentParser(prog='setup_tree_modules', usage='%(prog)s [opts]')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='Print extra information.', default=False)
    parser.add_argument('-r', '--root', action='store', dest='root', default=os.getenv('SAS_BASE_DIR'),
                        help='Override the value of $SAS_BASE_DIR.', metavar='SAS_BASE_DIR')
    parser.add_argument('-t', '--treedir', action='store', dest='treedir', default=os.getenv('TREE_DIR'),
                        help='Override the value of $TREE_DIR.', metavar='TREE_DIR')
    parser.add_argument('-m', '--modulesdir', action='store', dest='modulesdir', default=os.getenv('MODULES_DIR'),
                        help='Your modules directory', metavar='MODULES_DIR')
    parser.add_argument('-e', '--env', action='store_true', dest='env',
                        help='Create tree environment symlinks.', default=False)
    parser.add_argument('-i', '--mirror', action='store_true', dest='mirror',
                        help='Use the mirror site (SAM) instead.')
    parser.add_argument('-o', '--only', action='store', dest='only', metavar='[xxx].cfg',
                        default=None, help='create links for only the specified tree config.')

    opts = parser.parse_args()

    return opts


def main(args):

    # parse arguments
    opts = parse_args()

    # get directories
    datadir = os.path.join(opts.treedir, 'data')
    etcdir = os.path.join(opts.treedir, 'etc')

    # config files
    configs = glob.glob(os.path.join(datadir, '*.cfg'))

    # check for the SAS_BASE_DIR
    check_sas_base_dir(root=opts.root)

    # Read and write the configuration files
    for cfgfile in configs:
        tree = get_tree(config=cfgfile)
        # create env symlinks or write out tree module/bash files
        if opts.env:
            # skip creating the environ if a specific config if specified
            if opts.only and opts.only not in cfgfile:
                continue
            create_env(tree.environ, mirror=opts.mirror)
        else:
            write_file(tree.environ, term='modules', out_dir=etcdir, tree_dir=opts.treedir)
            write_file(tree.environ, term='bash', out_dir=etcdir, tree_dir=opts.treedir)
            write_file(tree.environ, term='tsch', out_dir=etcdir, tree_dir=opts.treedir)

            # Setup the modules
            copy_modules(filespath=etcdir, modules_path=opts.modulesdir, verbose=opts.verbose)


if __name__ == '__main__':
    main(sys.argv[1:])
