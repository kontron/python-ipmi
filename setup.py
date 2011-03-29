#!/usr/bin/env python

from setuptools import setup
import sys
sys.path.insert(0, 'src')

def main():
    setup(name         = 'pyipmi',
          version      = '0',
          description  = 'Pure python IPMI library',
          author_email = 'michael.walle@kontron.com',
          package_dir  = { '' : 'src' },
          packages     = [ 'pyipmi',
                           'pyipmi.interfaces',
                           'pyipmi.msgs',
                         ]
          )

if __name__ == '__main__':
    main()
