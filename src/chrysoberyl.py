#!/usr/bin/env python
# encoding: UTF-8

import os
import sys

import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def load_chrysoberyl_dir(dirname):
    data = {}

    for root, dirnames, filenames in os.walk(dirname):
        for filename in filenames:
            if filename.endswith('.yaml'):
                file = open(os.path.join(root, filename))
                data.update(yaml.load(file, Loader=Loader))
                file.close()
        del dirnames[:]  # don't automatically descend

    return data

def check_scalar_ref(data, key, node, property, type_=None):
    assert property in node, \
        "'%s' does not specify a %s" % (key, property)
    value = node[property]
    assert value in data, \
        "'%s' has undefined %s '%s'" % (key, property, value)
    if type_ is None:
        return
    assert data[value]['type'] == type_, \
        "'%s' has %s '%s' which is a %s, not a %s" % (
            key, property, value, data[value]['type'], type_)

def check_optional_scalar_ref(data, key, node, property, type_=None):
    if property in node:
        check_scalar_ref(data, key, node, property, type_=type_)

def check_list_ref(data, key, node, property):
    if property in node:
        for value in node[property]:
            assert value in data, \
                "'%s' has undefined %s '%s'" % \
                (key, property, value)

def check_chrysoberyl_data(data):
    for key in data:
      node = data[key]
      assert 'type' in node, \
          "'%s' does not specify a type" % key
      type_ = node['type']
      assert type_ in data, \
          "'%s' specifies undefined type '%s'" % (key, type_)
      assert 'type' in data[type_] and data[type_]['type'] == 'type', \
          "'%s' has bad type '%s'" % (key, type_)

      if type_ == 'Distribution':
          #assert 'distribution-of' in node, \
          #   "Distribution '%s' does not say what it is of" % key
          # this only makes sense for Distributions:
          # (and it has multiple possible types)
          check_optional_scalar_ref(data, key, node, 'distribution-of')

      # these only make sense for Language Implementations:
      if type_ == 'Language Implementation':
          check_scalar_ref(data, key, node, 'license', type_='License')
          check_optional_scalar_ref(data, key, node, 'in-distribution',
                                    type_='Distribution')
          check_scalar_ref(data, key, node, 'host-language',
                           type_='Programming Language')
          check_scalar_ref(data, key, node, 'implementation-type',
                           type_='Implementation Type')
          # ... these only make sense for compilers ...
          if node['implementation-type'] == 'compiler':
              check_scalar_ref(data, key, node, 'source-language',
                               type_='Programming Language')
              check_scalar_ref(data, key, node, 'target-language',
                               type_='Programming Language')

      # these only make sense for Games and Programming Languages:
      if type_ in ['Game', 'Programming Language']:
          check_scalar_ref(data, key, node, 'genre', type_='Genre')
          check_optional_scalar_ref(data, key, node, 'reference-distribution',
                                    type_='Distribution')
          check_list_ref(data, key, node, 'implementations')

      if type_ == 'Programming Language':
          check_scalar_ref(data, key, node, 'computational-class',
                           type_='Computational Class')

if __name__ == '__main__':
    data = load_chrysoberyl_dir(sys.argv[1])
    check_chrysoberyl_data(data)
