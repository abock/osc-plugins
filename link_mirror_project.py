# link_mirror_project.py
# osc plugin to create a link mirror of an OBS project
#
# Written by Aaron Bockover <abockover@novell.com>
# Copyright 2009 Novell, Inc.
# Released under the MIT/X11 license.
#

@cmdln.option ('-t', '--to-apiurl', metavar='DIR',
    help='URL of destination api server. Default is the source api server.')

@cmdln.option ('-p', '--source-proxy-name', metavar='PROXY',
    help='Name of proxy "project" prefix the target server uses to access'
         'projects in the source server. For instance, "openSUSE.org" if'
         'openSUSE:Factory is accessible on the target server through'
         'the project openSUSE.org:openSUSE:Factory.')

@cmdln.option ('-f', '--force', action='store_true',
    help='Force the link mirror strategy without asking for confirmation.')

def do_link_mirror_project (self, subcmd, opts, *args):
    """${cmd_name}: Maintains a linkpac mirror of an OBS project

    usage:
        osc link_mirror_project SOURCEPRJ DESTPRJ

    ${cmd_option_list}
    """

    args = slash_split (args)

    if not args or len (args) != 2:
        raise oscerr.WrongArgs ('Incorrect number of arguments.\n\n' \
            + self.get_cmd_help ('link_mirror_project'))

    source_project, dest_project = args
    source_apiurl = dest_apiurl = makeurl (conf.config['apiurl'], [])
    source_proxy_name = ''
    if opts.source_proxy_name:
        source_proxy_name = opts.source_proxy_name + ':'

    if opts.to_apiurl:
        dest_apiurl = makeurl (opts.to_apiurl, [])

    if source_project == dest_project and source_apiurl == dest_apiurl:
        raise oscerr.WrongArgs ('Source and destination are the same.')

    print 'Computing link mirror strategy...'

    # if the projects do not exist, this will fail via exception
    dest_packages = set (meta_get_packagelist (dest_apiurl, dest_project))
    source_packages = set (meta_get_packagelist (source_apiurl, source_project))
    
    # Compute what packages to link and remove
    to_link = source_packages.difference (dest_packages)
    to_remove = dest_packages.difference (source_packages)

    if len (to_link) == 0 and len (to_remove) == 0:
        print 'Mirror is in sync. Nothing to do.'
        sys.exit (0)

    # By default show the user what we'll do, and ask them to agree
    if not opts.force:
        self.print_and_confirm_strategy (source_apiurl, dest_apiurl,
            source_project, dest_project, opts.source_proxy_name,
            to_link, to_remove)

    print 'Executing link mirror strategy...'

    # Create links for new packages
    for package in to_link:
        print 'LINK: %s' % package
        self.link_package (source_apiurl, dest_apiurl,
            source_proxy_name, source_project, dest_project, package)

    # Remove links for removed packages
    for package in to_remove:
        print 'REMOVE: %s' % package
        delete_package (dest_apiurl, dest_project, package)

    print 'Done.'

def link_package (self, source_apiurl, dest_apiurl, source_proxy_name,
    source_project, dest_project, package):
    
    # Create or update the destination link project from the source project
    source_meta = show_package_meta (source_apiurl, source_project, package)
    dest_meta = replace_pkg_meta (source_meta, package, dest_project)
    u = makeurl (dest_apiurl, ['source', dest_project, package, '_meta'])
    http_PUT (u, data = dest_meta)

    # Create/overwrite the destination _link file
    link_data = '<link project="%s" package="%s"/>\n' % \
        (source_proxy_name + source_project, package)
    u = makeurl (dest_apiurl, ['source', dest_project, package, '_link'])
    http_PUT (u, data = link_data)


def print_and_confirm_strategy (self, source_apiurl, dest_apiurl,
    source_project, dest_project, source_proxy_name, to_link, to_remove):

    print
    print """Link mirror configuration:

    FROM: %s @ %s
    TO:   %s @ %s
    VIA:  %s
    """ % (source_project, source_apiurl, 
        dest_project, dest_apiurl, source_proxy_name or '<no-proxy>')

    to_link_count = len (to_link)
    to_remove_count = len (to_remove)

    if to_link_count > 0:
        print 'New links to be created (%d):' % to_link_count
        print
        for package in to_link:
            print '    %s' % package
        if to_remove_count > 0:
            print

    if to_remove_count > 0:
        print 'Stale links to be removed (%d):' % to_remove_count
        print
        for package in to_remove:
            print '    %s' % package

    print

    while True:
        print 'Continue? [Y/N]: ',
        input = sys.stdin.readline ().strip ().lower ()
        if input == 'y':
            break
        elif input == 'n':
            print 'Aborted.'
            sys.exit (1)
    
    print

