# update_moblin_mirrors.py
# osc plugin to update Moblin OBS/IBS link mirrors
#
# Written by Aaron Bockover <abockover@novell.com>
# Copyright 2009 Novell, Inc.
# Released under the MIT/X11 license.
#

@cmdln.option ('-f', '--force', action='store_true',
    help='Force the link mirror strategy without asking for confirmation.')

def do_update_moblin_mirrors (self, subcmd, opts, *args):
    """${cmd_name}: Updates Moblin OBS/IBS link mirrors

    ${cmd_usage}
    ${cmd_option_list}
    """

    ibs_api = 'https://api.suse.de'
    obs_api = 'https://api.opensuse.org'

    for project in ['Moblin:Factory', 'Moblin:UI']:
        print 'Updating OBS %s -> IBS Devel:%s' % (project, project)
        self.link_mirror_project (obs_api, ibs_api, project,
            'Devel:' + project, 'openSUSE.org', opts.force)


def link_mirror_project (self, source_apiurl, dest_apiurl, 
    source_project, dest_project, source_proxy_name, force):

    if source_proxy_name:
        source_proxy_name = '-p ' + source_proxy_name
    else:
        source_proxy_name = ''

    if force:
        force = '-f'
    else:
        force = ''

    self.run_link ('osc -A %s link_mirror_project -t %s %s %s %s %s' % \
        (source_apiurl, dest_apiurl, force, source_proxy_name,
        source_project, dest_project))

    print


def run_link (self, command):
    print 'Running: %s' % command
    if not os.system (command) == 0:
        sys.exit (1)

