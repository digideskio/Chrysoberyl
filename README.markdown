Chrysoberyl
===========

*Chrysoberyl* is an attempt to catalogue, and curate, the things produced
by, and related to, Cat's Eye Technologies.

It is something between a wiki and a database and a semantic web and
_The Devil's Dictionary_.

It is supposed to be primarily informative, and only secondarily machine-
processable, and only thirdly structured.  So, the schemas in use are
fuzzy, flexible, incomplete, and subject to change and the drop of a hat.

It does not contain only those things produced by Cat's Eye Technologies;
in theory, anything can be in it.  In these cases, the entry may consist
simply of commentary on the item, or a short explanation of how it relates
to Cat's Eye Technologies.

General Format
--------------

The Chrysoberyl data files are in YAML format, in the `data` directory.

The division into files is artificial; files make no semantic difference;
if they were all concatenated into a single file, the data would be the
same.

Each top-level key in the data is the name of a *node*.  The name should
be both human and machine readable, like the name of a page in a wiki.

To disambiguate nodes which would otherwise have the same name, a
disambiguating phrase may be placed after the name in parentheses.

Each node must have a `type` field, whose value names a node whose `type`
field is `type`.  (This necessitates the presence of a node named `type`
whose `type` is `type`.)

Each node may have any of the following fields:

*   `summary` -- a one-line summary of the node
*   `description` -- a relatively objective description of the node
*   `commentary` -- a subjective opinion, by Chris Pressey, of the node
*   `subtitle` -- expanding on the name of the node
*   `acronym-for` -- expanding the name of the node
*   `hidden` -- if true, does not show up in `related()` lists
*   ...

Each node can have a `domain`, which influences how breadcrumbs are
arranged.  For example, domain of lingography is Chris Pressey.  Domain
of everything which does not specify a domain is Cat's Eye Technologies.
(This scheme is, of course, subject to modifications)

In addition, nodes of particular types may have fields that have meaning
for that type.

Specific Schema
---------------

In the following, an "implementable" (for lack of a better term) is pretty
much anything that can be implemented.  Specifically, it refers to any of
the following:

*   a programming language (which includes machine languages)
*   a game
*   a platform (which includes operating systems, architectures, and
    frameworks)
*   a tool
*   a library
*   a musical composition

An implementable may have zero or more implementations.

Ideally (it is not really this way in Chrysoberyl yet), an implementation
could be either an "actual" implementation, or a specification document
which attempts to unambiguously describe how to implement the implementable
(for example, a language specification would be an "implementation" of a
programming language, and a musical score would be an "implementation" of a
musical composition.)

Each implementation may or may not be a reference implementation.  Ideally,
Chrysoberyl should understand that an implementable can have more than one
reference implementation.  (For example, having a prescriptive specification
*and* a reference implementation can be useful.)

A standards body could also be a reference implementation, in a sense, as
it can act as a disambiguator for when reference implementations prove to
be insufficiently clear.  (Maybe this is stretching it?)

Each implementation may be included in zero or more distributions.

The _reference distribution_ of an implementable is defined as the first
distribution that the first reference implementation is included in.  (This
derived notion of reference distribution should replace the explicit notion
of a reference distribution currently present in Chrysoberyl.)

Only one distribution can be the reference distribution for an implementable.
There can be only one reference distribution for an implementable.  Typically
It will contain the spec and/or reference implementation of the implementable.

If there is no reference distribution, a link to its specification (even if
it's just a page on a wiki) or standards body (even if it's just "the official
website") is required.

(This part needs updating)  Therefore, every implementable needs at least one
of the following:

*   `defining-distribution` (a key)
*   `specification-link` (a URL, or `esowiki`)
*   `standards-body` (a URL)
*   `no-specification: true`

`defining-distribution` is really just a stopgap measure that basically means
"defined by the specification that you will find somewhere in this
distribution" -- really the spec itself should be referenced in the node.

If none of the last three of that list are present, we expect an
implementable to have a `reference-distribution`.  If that key is not present,
we look for a distribution called `FOO distribution` where `FOO` is the name
of the implementable.

An implementable may also have multiple implementations.  Each implementation
may be in zero or more distributions, and a distribution may contain multiple
implementations.  Only one implementation can be the reference implementation
for an implementable.

An implementation may be an implementation of multiple implementables.
(For example, `gcc` is an implementation of ANSI C and C99.)

If an implementation does not give authors, they are assumed to be the
authors of the implementable it implements.  Ditto auspices.

A distribution has releases and, often, can be checked out of some version
control system, and, often, has a place to report bugs.  An implementation,
by itself, has none of those things (at least not in a structured way -- it
might simply be a page on a wiki somewhere.)  The releases of a distribution
should be sorted from earliest to latest.

On the other hand, neither distributions nor implementables have licenses,
but implementations do.  The license of a distribution can be inferred from
the licenses of the implementations contained with it.

Each implementation has an implementation-type.  For a programming language,
this may be interpreter, compiler, etc.  For a platform, this currently must
be "emulator" (even if the platform is a framework...)

An implementation may claim that it is prebuilt in its distribution.  This
assumes it's only in one distribution.  Really, being prebuilt somewhere is
a property of the *distribution*, but this fudging makes some things easier
for now.

Each platform must specify what its native language is.  Implementations
may specify, along with a host language, a host platform.

Every implementable must have a development stage.  The development
stage of an implementation, if not given, is assumed to be on par with the
development stage of the thing it implements.  Distributions never have
development stages, as they are, in a sense, always works in progress.

### side note ###

Any tool which understands a language may be considered an implementation
of that language: an interpreter, a compiler, a parser, a static analyzer, a
pretty-printer, etc., are all implementations.

This is actually kind of weird (e.g. yucca is an implementation of BASIC?
maybe say "partial implementation" in the template if the implementation
type is not interpreter or compiler) but we'll go with it for now.

License
-------

See the file LICENSE.

Script
------

`chrysoberyl` is a Python script included in this distribution which
can process the Chrysberyl database.  It is located in the `bin` directory,
and its source modules are in the `src/chrysoberyl` directory.  Things it
can do include:

*   check the data for consistency (all subcommands do this)
*   render Jinja2 templates with the data (one file per node) and
    dump all nodes to a single JSON file (`chrysoberyl render`)
*   render all nodes to a JSON blob (`chrysoberyl jsonify`)
*   write out an Atom news feed (`chrysoberyl announce`)

Less common activities include:

*   create a `toolshelf` catalogue of Bitbucket repos (`chrysoberyl catalogue`)
*   write out a mapping between nodes and distributions (`chrysoberyl mkdistmap`)

The tool has the following requirements, which can be installed with
`toolshelf` or `easy_install` or `pip` or whatever:

    atomize
    jinja2
    markdown
    PyYaml
