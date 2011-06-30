#!/usr/bin/env python

from setuptools import setup

def main():
    setup(name = 'pyipmi',
            version = '1.00',
            description = 'Pure python IPMI library',
            author_email = 'michael.walle@kontron.com',
            package_dir = { '' : 'src' },
            packages = [ 'pyipmi',
                'pyipmi.interfaces',
                'pyipmi.msgs',
                'pyipmi.ext',
                'pyipmi.ext.totalphase',
            ],
            package_data = {
                'pyipmi.ext.totalphase':
                    ['aardvark.so', 'LICENSE.txt']
            },
            scripts = ['bin/ipmitool.py']
    )

if __name__ == '__main__':
    main()
