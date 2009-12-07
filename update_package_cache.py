# update_package_cache.py
# osc plugin to create a link mirror of an OBS project
#
# Written by Aaron Bockover <abockover@novell.com>
#
# Copyright 2006-2009 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version
#

@cmdln.option ('-d', '--destdir', metavar='DIR',
    help='Destination directory. Default is the package cache dir as '
         'defined in osc config or overridden by OSC_PACKAGECACHEDIR. '
         'if the package cache is used, additionaly directory structure '
         'will be created so the packages can be used for building.')

@cmdln.option ('-e', '--existing', action='store_true',
    help='Only download updated versions of packages that have '
         'been previously downloaded.')

@cmdln.option ('-p', '--prune', action='store_true',
    help='Remove older versions of packages that have '
         'been previously downloaded.')

@cmdln.option ('-v', '--verbose', action='store_true',
    help='Show extra progress and processing details.')

def do_update_package_cache (self, subcmd, opts, project, repository, architecture):
    """${cmd_name}: Fetch all published binaries from a project

    ${cmd_usage}
    ${cmd_option_list}
    """
    
    import glob

    apiurl = conf.config['apiurl']

    self.prune_stats = { 'files': [], 'bytes': 0 }

    if opts.verbose:
        print 'Fetching package list for %s/%s/%s/%s' % (apiurl, project, 
            repository, architecture)
    binaries = get_binarylist (apiurl, project, 
        repository, architecture, verbose = True)
    if binaries == []:
        sys.exit ('no binaries found.')

    if not opts.destdir:
        opts.destdir = os.path.join (self.get_package_cache_dir (),
            project, repository, architecture)

    if not os.path.isdir (opts.destdir):
        if opts.verbose:
            print 'Creating cache directory: %s' % opts.destdir
        os.makedirs (opts.destdir, 0755)
    elif opts.verbose:
        print 'Using cache directory: %s' % opts.destdir

    finished_bytes = 0
    finished_binaries = 0
    total_binaries = len (binaries)
    total_bytes = 0
    for binary in binaries:
        total_bytes += binary.size

    for binary in binaries:
        finished_binaries += 1
        finished_bytes += binary.size
        if opts.verbose:
            print '==> %d / %d, %d MB / %d MB, %d%%'\
                % (finished_binaries,
                   total_binaries,
                   finished_bytes / 1024 / 1024,
                   total_bytes / 1024 / 1024,
                   (float (finished_bytes) / float (total_bytes)) * 100.0)
            print '    Checking for suitable %s' % binary.name

        # Look for existing RPMs with same name, modification time, and size.
        # We have to do this because OBS doesn't give us properly named RPM 
        # files for unpublished RPM binaries. After fetching the binary we will 
        # rename it properly so it can be picked up by osc build.
        package, ext = os.path.splitext (binary.name)
        local_binaries = glob.glob (os.path.join (opts.destdir, package) + '*')
        skip_binary = None

        for existing in local_binaries:
            st = os.stat (existing)
            if st.st_mtime == binary.mtime and st.st_size == binary.size:
                if self.get_rpm_package_name (existing) == package:
                    skip_binary = existing
                    break

        if skip_binary:
            if opts.verbose:
                print '    Skipping, found %s' % os.path.basename (skip_binary)
            if opts.prune:
                self.prune (package, local_binaries, skip_binary, opts.verbose)
            continue
        elif opts.existing and local_binaries == []:
            if opts.verbose:
                print '    Skipping, no older version found locally'
            continue

        # Download the binary
        target_filename = os.path.join (opts.destdir, binary.name)
        if opts.verbose:
            print '    ',
        else:
            print '%d/%d %dMB: ' % (finished_binaries, total_binaries,
                binary.size / 1024 / 1024),
        get_binary_file (apiurl, project, repository, architecture,
            binary.name,
            target_filename = target_filename,
            target_mtime = binary.mtime,
            progress_meter = True)

        # Update the filename based on RPM data
        new_target_filename = self.get_rpm_filename (target_filename)
        if opts.verbose:
            print '    Renaming %s to %s' % \
                (binary.name, os.path.basename (new_target_filename))
        os.rename (target_filename, new_target_filename)

        if opts.prune and not local_binaries == []:
            self.prune (package, local_binaries, new_target_filename, opts.verbose)

    if not self.prune_stats['files'] == []:
        print '%d obsolete RPMs removed (%d KB)' % (len (self.prune_stats['files']),
            self.prune_stats['bytes'])


def prune (self, package_name, local_binaries, keep_binary, verbose):
    for binary in local_binaries[:]:
        if not binary == keep_binary and self.get_rpm_package_name (binary) == package_name:
            self.prune_stats['files'].append (binary)
            self.prune_stats['bytes'] += os.stat (binary).st_size
            if verbose:
                print '    Removed obsolete %s' % os.path.basename (binary)


def get_rpm_package_name (self, filename):
    return data_from_rpm (filename, 'Name:')['Name:']


def get_rpm_filename (self, filename):
    # Adapted from osc's fetch.py
    rpm_data = data_from_rpm (filename,
        'Name:', 'Version:', 'Release:', 'Arch:',
        'SourceRPM:', 'NoSource:', 'NoPatch:')
    if not rpm_data:
        return filename

    arch = rpm_data['Arch:']
    if not rpm_data['SourceRPM:']:
        if rpm_data['NoSource:'] or rpm_data['NoPatch:']:
            arch = 'nosrc'
        else:
            arch = 'src'
    
    canonname = '%s-%s-%s.%s.rpm' % (rpm_data['Name:'], 
        rpm_data['Version:'], rpm_data['Release:'], arch)
    head, tail = os.path.split (filename)
    return os.path.join (head, canonname)


def get_package_cache_dir (self):
    val = os.getenv ('OSC_PACKAGECACHEDIR')
    if val:
        if conf.config.has_key ('packagecachedir'):
            print 'Overriding config value for packagecachedir=\'%s\' '
            'with \'%s\'' % (conf.config[var], val)
        conf.config['packagecachedir'] = val
    return conf.config['packagecachedir']

