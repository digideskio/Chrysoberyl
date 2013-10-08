# encoding: UTF-8

"""Parse command line and execute the command(s) given on it.

"""

import codecs
import json
from optparse import OptionParser
import os
import re
import sys

from chrysoberyl.checker import check_chrysoberyl_data
from chrysoberyl.feed import make_news_feed
from chrysoberyl.loader import load_chrysoberyl_dirs
from chrysoberyl.localrepos import (
    bitbucket_repos,
    troll_docs, survey_repos, get_latest_release_tag, lint_dists
)
from chrysoberyl.renderer import Renderer
from chrysoberyl.transformer import (
    convert_chrysoberyl_data, transform_dates
)
from chrysoberyl.util import do_it


def survey(data, options):
    """Survey local clones of distributions.

    """
    survey_repos(data, options.clone_dir, hg_outgoing=options.hg_outgoing)
    return 0


def lint(data, options):
    """Lint local clones of distributions.

    """
    lint_dists(data, options.clone_dir, host_language=options.host_language)
    return 0


def troll(data, options):
    """Troll local hg clones of distributions listed in Chrysoberyl,
    looking through each distribution for anything that looks like
    documentation, and update documentation.yaml with those
    filenames.

    """
    troll_docs(data, options.clone_dir, options.output_filename)
    return 0


def render(data, options):
    """Render all nodes to a set of HTML5 files.

    """
    json_data = {}
    for key in data:
        if not data[key].get('hidden', False):
            json_data[key] = data[key]
    filename = os.path.join(options.node_dir, 'chrysoberyl.json')
    with codecs.open(filename, 'w', 'utf-8') as file:
        json.dump(transform_dates(json_data), file, encoding='utf-8',
                  default=unicode)
    convert_chrysoberyl_data(data)
    r = Renderer(data,
        options.template_dirs, options.node_dir, options.clone_dir,
        options.render_docs, options.sleek_node_links
    )
    r.render_chrysoberyl_data()


def announce(data, options):
    """Create news feeds from news item nodes in Chrysoberyl.

    """
    convert_chrysoberyl_data(data)
    make_news_feed(data, options.feed_dir, 'atom_15_news.xml', limit=15)
    make_news_feed(data, options.feed_dir, 'atom_30_news.xml', limit=30)
    make_news_feed(data, options.feed_dir, 'atom_all_news.xml')


def release(data, options):
    """Create a distfile from the latest tag in a local distribution repo.

    """
    distro = options.distro_name
    tag = get_latest_release_tag(data, distro, options.clone_dir)
    if not tag:
        print "ERROR: repository not tagged"
        return 1
    match = re.match(r'^rel_(\d+)_(\d+)_(\d+)_(\d+)$', tag)
    if match:
        v_maj = match.group(1)
        v_min = match.group(2)
        r_maj = match.group(3)
        r_min = match.group(4)
        filename = '%s-%s.%s-%s.%s.zip' % (distro, v_maj, v_min, r_maj, r_min)
    else:
        match = re.match(r'^rel_(\d+)_(\d+)$', tag)
        if match:
            v_maj = match.group(1)
            v_min = match.group(2)
            r_maj = "0"
            r_min = "0"
            filename = '%s-%s.%s.zip' % (distro, v_maj, v_min)
        else:
            print "ERROR: not a release tag: %s" % tag
            return 1
    print """\
  - version: "%s.%s"
    revision: "%s.%s"
    url: http://catseye.tc/distfiles/%s
""" % (v_maj, v_min, r_maj, r_min, filename)
    full_filename = os.path.join(options.distfiles_dir, filename)
    if os.path.exists(full_filename):
        print "ERROR: distfile already exists: %s" % full_filename
        do_it("unzip -v %s" % full_filename)
        return 1
    excludes = ' '.join(['-X %s' % x
                         for x in ('.hgignore', '.gitignore',
                                   '.hgtags', '.hg_archival.txt')])
    cwd = os.getcwd()
    os.chdir(os.path.join(options.clone_dir, distro))
    do_it("hg archive -t zip -r %s %s %s" % (tag, excludes, full_filename))
    os.chdir(cwd)


def catalog(data, options):
    """Create a toolshelf catalog from distribution nodes.

    """
    for (key, user, repo) in bitbucket_repos(data):
        print 'bb:%s/%s' % (user, repo)


### driver ###

COMMANDS = {
    'render': render,
    'announce': announce,
    'troll': troll,
    'survey': survey,
    'lint': lint,
    'release': release,
    'catalog': catalog,
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
    optparser.add_option("-d", "--data-dirs",
                         dest="data_dirs", metavar='DIRS', default='data',
                         help="colon-separated list of directories "
                              "containing Chrysoberyl Yaml data files "
                              "(default: %default)")
    optparser.add_option("--distfiles-dir",
                         dest="distfiles_dir", metavar='DIR',
                         default='../catseye.tc/distfiles',
                         help="write distfiles into this directory "
                              "(default: %default)")
    optparser.add_option("--distro-name",
                         dest="distro_name",
                         default=None,
                         help="(for release) basename for distfile to create")
    optparser.add_option("--feed-dir",
                         dest="feed_dir", metavar='DIR',
                         default='../catseye.tc/feeds',
                         help="write feeds into this directory "
                              "(default: %default)")
    optparser.add_option("--hg-outgoing",
                         dest='hg_outgoing', default=False,
                         action='store_true',
                         help="(for lint) call `hg outgoing` on each repo")
    optparser.add_option("--host-language",
                         dest="host_language", metavar='LANG',
                         default=None,
                         help="(for lint) lint only those distributions "
                              "containing implementations in this language")
    optparser.add_option("--node-dir",
                         dest="node_dir", metavar='DIR',
                         default='../catseye.tc/node',
                         help="write rendered nodes into this directory "
                              "(default: %default)")
    optparser.add_option("--output-doc-yaml-to",
                         dest="output_filename", metavar='FILENAME',
                         default=None,
                         help="(for troll) write updated documentation yaml here")
    optparser.add_option("--render-docs",
                         dest="render_docs", default=False,
                         action='store_true',
                         help="render documentation nodes as well")
    optparser.add_option("--sleek-node-links",
                         dest="sleek_node_links", default=False,
                         action='store_true',
                         help="render links to nodes using Mediawiki-ish "
                              "URLs (requires web server that understands "
                              "what nodes these refer to")
    optparser.add_option("-t", "--template-dirs",
                         dest="template_dirs", metavar='DIRS',
                         default='templates',
                         help="colon-separated list of directories "
                              "containing Chrysoberyl templates "
                              "(default: %default)")

    options, args = optparser.parse_args(args)

    print "Loading Chrysoberyl data..."
    data = load_chrysoberyl_dirs(options.data_dirs.split(':'))
    check_chrysoberyl_data(data)

    for command in args:
        func = COMMANDS.get(command, None)
        if func is None:
            sys.stderr.write("Usage: " + usage())
            sys.exit(1)
        print "Executing '%s'..." % command
        result = func(data, options)
        if result != 0:
            sys.exit(result)
