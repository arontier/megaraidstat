import pathlib
import re
from setuptools import setup


here = pathlib.Path(__file__).parent.resolve()


def version(path):
    contents = (here/path).read_text(encoding='utf-8')
    pattern = r"^__version__ = ['\"]([^'\"]*)['\"]"
    return re.search(pattern, contents, re.M).group(1)


setup(
    name='megaraidstat',
    version=version('megaraidstat/__init__.py'),
    author='daverona',
    author_email='egkimatwork@gmail.com',
    license='MIT',
    description='Inspect disks on MegaRAID controllers',
    long_description=(here/'README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    url='https://gitlab.com/daverona/python/megaraidstat',
    keywords='megaraid, storcli, python',
    classifiers=[],
    packages=['megaraidstat'],
    zip_safe=False,

    python_requires='>=3.6, <4',
    entry_points={
        'console_scripts': [
            'megaraidstat=megaraidstat.index:main',
        ],
    },
    setup_requires=[],
    install_requires=[],
    extras_require={},
    package_data={},
    data_files=[],
)
