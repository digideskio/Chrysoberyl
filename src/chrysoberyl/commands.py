# encoding: UTF-8

"""Parse command line and execute the command(s) given on it.

"""

import codecs
import json
from optparse import OptionParser
import os
import re
import subprocess
import sys

from chrysoberyl.checker import check_chrysoberyl_data
from chrysoberyl.feed import make_news_feed
from chrysoberyl.loader import (
    load_chrysoberyl_dirs, load_config, overlay_yaml
)
from chrysoberyl.objects import Universe
from chrysoberyl.renderer import Renderer
from chrysoberyl.transformer import transform_dates


# experimental loose toolshelf integration
if 'TOOLSHELF' in os.environ and os.environ['TOOLSHELF']:
    sys.path.insert(0, os.path.join(os.environ['TOOLSHELF'], '.toolshelf', 'src'))
    import toolshelf
else:
    toolshelf = None


### helper functions ###


def bitbucket_repos(space):
    """Generator which yields information about every Mercurial repository
    on Bitbucket referenced by some distribution in Chrysoberyl.

    Information is a triple of the distribution key, the Bitbucket username,
    and the repository name.

    """
    for key, node in space.iteritems():
        if node['type'] != 'Distribution':
            continue
        if 'bitbucket' not in node:
            continue
        (user, repo) = node['bitbucket'].split('/')
        yield (key, user, repo)


def get_distname(node):
    if 'distname' in node:
        return node['distname']
    if 'bitbucket' in node:
        match = re.match(r'^catseye/(.*?)$', node['bitbucket'])
        return match.group(1)
    urls = [release['url'] for release in node['releases']]
    distnames = set()
    for url in urls:
        match = re.match(r'^http:\/\/.*\/(.*?)\-', url)
        if not match:
            raise ValueError(url)
        distnames.add(match.group(1))
    if len(distnames) == 1:
        return distnames.pop()
    raise ValueError(distnames)


# FIXME this is generally a terrible duplication of stuff from toolshelf.
# these changes should be incorporated into toolshelf, and this should
# use toolshelf.

def get_it(command):
    output = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE
    ).communicate()[0]
    return output


def each_tag(user, repo):
    os.chdir(os.path.join(os.getenv('TOOLSHELF'), 'bitbucket.org', user, repo))
    output = get_it('hg tags')
    for line in output.split('\n'):
        match = re.match(r'^\s*(\S+)\s+(\d+):(.*?)\s*$', line)
        if match:
            yield match.group(1), int(match.group(2))


def get_latest_tag(user, repo):
    last_tag = 'tip'
    last_rev = -1
    for tag, hg_rev in each_tag(user, repo):
        if tag == 'tip':
            continue
        if hg_rev > last_rev:
            last_tag = tag
            last_rev = hg_rev
    return last_tag


### command functions ###

def mkdistmap(universe, options, config):
    """Create a mapping between nodes and distributions."""
    space = universe['node']  # FIXME hardcoded
    dist = {}
    for (key, user, repo) in bitbucket_repos(space):
        dist[key] = (user, repo)

    repo_to_node = {}
    for key, node in space.iteritems():
        distribution = None

        if 'defining-distribution' in node:
            distribution = node['defining-distribution']
        else:
            ref_impl = space.reference_implementation_of(key)
            if ref_impl is not None:
                if 'in-distributions' in space[ref_impl]:
                    return space[ref_impl]['in-distributions'][0]

        if distribution:
            if distribution in dist:
                # special case-ish hack-ish special case
                if dist[distribution][1] != 'html5-gewgaws':
                    repo_to_node[dist[distribution][1]] = key

    with open(config[space.name]['dist_map'], 'w') as f:
        f.write(json.dumps(repo_to_node))


def render(universe, options, config):
    """Render all nodes to a set of HTML5 files.

    """
    for space in universe.spaces:
        space.convert_chrysoberyl_data()
        r = Renderer(universe, space,
            config[space.name]['template_dirs'],
            config[space.name]['output_dir'],
            options.clone_dir,
            options.sleek_node_links,
            options.render_nodes,
        )
        r.render_chrysoberyl_data()


def jsonify(universe, options, config):
    """Render all nodes to a JSON blob.

    """
    json_data = {}
    space = universe['node']  # FIXME hardcoded
    for (key, node) in space.iteritems():
        if not node.get('hidden', False):
            json_data[key] = node
    filename = os.path.join(config['node']['output_dir'], 'chrysoberyl.json')
    with codecs.open(filename, 'w', 'utf-8') as file:
        json.dump(transform_dates(json_data), file, encoding='utf-8',
                  default=unicode)


def announce(universe, options, config):
    """Create news feeds from news item nodes in Chrysoberyl.

    """
    space = universe['node']  # FIXME hardcoded
    space.convert_chrysoberyl_data()
    feed_dir = config['node']['feed_dir']
    make_news_feed(universe, space, feed_dir, 'atom_15_news.xml', limit=15)
    make_news_feed(universe, space, feed_dir, 'atom_30_news.xml', limit=30)
    make_news_feed(universe, space, feed_dir, 'atom_all_news.xml')


def catalogue(universe, options, config):
    """Create a toolshelf catalogue from distribution nodes.

    """
    space = universe['node']  # FIXME hardcoded
    lines = []
    for (key, user, repo) in bitbucket_repos(space):
        tag = get_latest_tag(user, repo)
        lines.append('bb:%s/%s@%s' % (user, repo, tag))
    for line in sorted(lines):
        print line


def check_releases(universe, options, config):
    """Check for missing Chrysoberyl releases based on hg tags.

    """

    def match_tag(tag):
        match = re.match(r'^rel_(\d+)_(\d+)_(\d\d\d\d)_?(\d\d\d\d)$', tag)
        if match:
            v_maj = match.group(1)
            v_min = match.group(2)
            r_maj = match.group(3)
            r_min = match.group(4)
            v_name = '%s.%s-%s.%s' % (
                v_maj, v_min, r_maj, r_min
            )
            return (v_maj, v_min, r_maj, r_min, v_name)
    
        match = re.match(r'^rel_(\d+)_(\d+)$', tag)
        if not match:
            match = re.match(r'^v?(\d+)\.(\d+)$', tag)
        if match:
            v_maj = match.group(1)
            v_min = match.group(2)
            v_name = '%s.%s' % (v_maj, v_min)
            return (v_maj, v_min, "0", "0", v_name)
    
        match = re.match(r'^v?(\d+)\.(\d+)\-(\d+)\.(\d+)$', tag)
        if match:
            v_maj = match.group(1)
            v_min = match.group(2)
            r_maj = match.group(3)
            r_min = match.group(4)
            v_name = '%s.%s-%s.%s' % (
                v_maj, v_min, r_maj, r_min
            )
            return (v_maj, v_min, r_maj, r_min, v_name)

        return None

    def print_release(version):
        print """\
  - version: "%s"
    revision: "%s"
    url: %s""" % (version['version'], version['revision'], version['url'])

    passes = 0
    space = universe['node']  # FIXME hardcoded
    for (key, user, repo) in sorted(bitbucket_repos(space)):
        if key in ('The Dipple', 'Illgol: Grand Mal',):
            continue

        releases = space[key]['releases']

        # record releases which are associated with a tag that does exist,
        # so we can filter them out at the discovery phase
        release_tags = set()
        for r in releases:
            tag = r.get('tag', None)
            if tag:
                release_tags.add(tag)

        versions = []
        for tag, hg_rev in each_tag(user, repo):
            if tag in ('tip',) or tag in release_tags:
                continue
            result = match_tag(tag)
            if not result:
                print "Weird tag in %s: '%s'.  Skipping." % (key, tag)
                continue
            (v_maj, v_min, r_maj, r_min, v_name) = result
            distname = get_distname(space[key])
            versions.append((hg_rev, {
                'url': 'http://catseye.tc/distfiles/%s-%s.zip' % (distname, v_name),
                'version': "%s.%s" % (v_maj, v_min),
                'revision': "%s.%s" % (r_maj, r_min),
            }))
        versions = [version[1] for version in sorted(versions)]

        def strip_release(r):
            return {
               'version': str(r['version']), 'revision': str(r['revision'])
            }

        stripped_versions = [strip_release(v) for v in versions]
        stripped_releases = [strip_release(v) for v in releases]

        missing_releases = []
        for version in versions:
            if strip_release(version) not in stripped_releases:
                missing_releases.append(version)

        if not missing_releases:
            passes += 1
        else:
            print '-' * 40
            print key
            print '-' * 40
            print
            for release in releases:
                print_release(release)
            print
            print output
            print
            print "** MISSING: **"
            print
            for release in missing_releases:
                print_release(release)
            print

    print
    print "%s passed" % passes


def check_distfiles(universe, options, config):
    """Check for missing distfiles based on Chrysoberyl releases

    """
    # FIXME hardcoded
    depo = '/media/cpressey/Transcend/mine/catseye.tc/distfiles/'
    space = universe['node']  # FIXME hardcoded


    def v_name_to_rel_name(v_name):
        match = re.match(r'^(\d+)\.(\d+)\-(\d\d\d\d)\.(\d\d\d\d)$', v_name)
        if match:
            return 'rel_%s_%s_%s_%s' % match.groups()
        match = re.match(r'^(\d+)\.(\d+)$', v_name)
        if match:
            return 'rel_%s_%s' % match.groups()
        return v_name

    commands = []
    for (key, user, repo) in bitbucket_repos(space):
        for release in space[key]['releases']:
            url = release['url']
            match = re.match(r'^http\:\/\/catseye\.tc\/distfiles\/(.*?)$', url)
            if not match:
                raise ValueError(url)
            filename = os.path.join(depo, match.group(1))
            if not os.path.exists(filename):
                print filename
                distname = get_distname(space[key])
                match = re.match(r'^http\:\/\/catseye\.tc\/distfiles\/' + re.escape(distname) + r'\-(.*?)\.zip$', url)
                if not match:
                    raise ValueError(url)
                v_name = match.group(1)
                if not os.getenv('DECIMAL_VERSIONS'):
                    v_name = v_name_to_rel_name(v_name)
                command = "cd `toolshelf.py pwd %s` && toolshelf.py --output-dir=%s release .@%s" % (distname, depo, v_name)
                commands.append(command)

    print
    for command in commands:
        print command

### driver ###

COMMANDS = {
    'render': render,
    'jsonify': jsonify,
    'announce': announce,
    'mkdistmap': mkdistmap,
    'catalogue': catalogue,
    'check_releases': check_releases,
    'check_distfiles': check_distfiles,
}


def usage():
    message = "chrysoberyl {option} {<command>}\n\n"
    message += "where each <command> is one of the following.  All commands\n"
    message += "will be executed in the sequence in which they were given,\n"
    message += "after the Chrysoberyl data has been loaded and statically checked.\n"
    for command in sorted(COMMANDS.keys()):
        message += "\n  %s - " % command
        message += COMMANDS[command].__doc__.rstrip()
    return message


def perform(args):
    optparser = OptionParser(usage().rstrip())
    optparser.add_option("-c", "--clone-dir",
                         dest="clone_dir", metavar='DIR', default='..',
                         help="specify location of the hg clones "
                              "of reference distributions "
                              "(default: %default)")
    optparser.add_option("--config",
                         dest="config", metavar='FILE', default='config.yaml',
                         help="specify the config file to use "
                              "(default: %default)")
    optparser.add_option("--render-nodes",
                         dest="render_nodes", metavar='NODES', default=None,
                         help="comma-separated list of nodes to render "
                              "(default: render all nodes)")
    optparser.add_option("--sleek-node-links",
                         dest="sleek_node_links", default=False,
                         action='store_true',
                         help="render links to nodes using Mediawiki-ish "
                              "URLs (requires web server that understands "
                              "what nodes these refer to)")

    options, args = optparser.parse_args(args)

    config = load_config(options.config)

    universe = Universe()

    for key in config.keys():
        try:
            os.makedirs(config[key]['output_dir'])
        except OSError:
            pass
        print "Loading Chrysoberyl '%s' data..." % key
        space = universe.create_namespace(key)
        load_chrysoberyl_dirs(space, config[key]['data_dirs'])
        for filename in config[key].get('overlay_files', []):
            overlay_yaml(filename, space)

    for key in config.keys():
        check_chrysoberyl_data(universe, universe[key])

    for command in args:
        func = COMMANDS.get(command, None)
        if func is None:
            sys.stderr.write("Usage: " + usage() + '\n')
            sys.exit(1)
        print "Executing '%s'..." % command
        # it's expected that func will just raise an exc if it fails
        func(universe, options, config)
