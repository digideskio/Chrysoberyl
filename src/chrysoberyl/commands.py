# encoding: UTF-8

"""Parse command line and execute the command(s) given on it.

"""

import codecs
import json
from optparse import OptionParser
import os
import sys

from chrysoberyl.checker import check_chrysoberyl_data
from chrysoberyl.feed import make_news_feed
from chrysoberyl.loader import load_chrysoberyl_dirs
from chrysoberyl.localrepos import (
    bitbucket_repos, troll_docs, survey_repos
)
from chrysoberyl.renderer import Renderer
from chrysoberyl.transformer import (
    convert_chrysoberyl_data, transform_dates
)


# experimental loose toolshelf integration
if 'TOOLSHELF' in os.environ and os.environ['TOOLSHELF']:
    sys.path.insert(0, os.path.join(os.environ['TOOLSHELF'], '.toolshelf', 'src'))
    import toolshelf
else:
    toolshelf = None


def survey(data, options):
    """Survey local clones of distributions.

    """
    survey_repos(data, options.clone_dir, hg_outgoing=options.hg_outgoing)


def troll(data, options):
    """Troll local hg clones of distributions listed in Chrysoberyl,
    looking through each distribution for anything that looks like
    documentation, and update documentation.yaml with those
    filenames.

    """
    troll_docs(data, options.clone_dir, options.output_filename)


def render(data, options):
    """Render all nodes to a set of HTML5 files.

    """
    convert_chrysoberyl_data(data)
    r = Renderer(data,
        options.template_dirs, options.node_dir, options.clone_dir,
        options.render_docs, options.sleek_node_links
    )
    r.render_chrysoberyl_data()


def jsonify(data, options):
    """Render all nodes to a JSON blob.

    """
    json_data = {}
    for key in data:
        if not data[key].get('hidden', False):
            json_data[key] = data[key]
    filename = os.path.join(options.node_dir, 'chrysoberyl.json')
    with codecs.open(filename, 'w', 'utf-8') as file:
        json.dump(transform_dates(json_data), file, encoding='utf-8',
                  default=unicode)


def announce(data, options):
    """Create news feeds from news item nodes in Chrysoberyl.

    """
    convert_chrysoberyl_data(data)
    make_news_feed(data, options.feed_dir, 'atom_15_news.xml', limit=15)
    make_news_feed(data, options.feed_dir, 'atom_30_news.xml', limit=30)
    make_news_feed(data, options.feed_dir, 'atom_all_news.xml')


def catalog(data, options):
    """Create a toolshelf catalog from distribution nodes.

    """
    for (key, user, repo) in bitbucket_repos(data):
        print 'bb:%s/%s' % (user, repo)


### driver ###

COMMANDS = {
    'render': render,
    'jsonify': jsonify,
    'announce': announce,
    'troll': troll,
    'survey': survey,
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
        # expected that func will just raise an exc if it fails
        func(data, options)
