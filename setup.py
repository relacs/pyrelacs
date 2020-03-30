from setuptools import setup

setup(
    name = "pyrelacs",
    version = "0.0.1",
    author = "Fabian Sinz, Juan Sehuanes, Jan Benda",
    author_email = "fabian.sinz@uni-tuebingen.de",
    description = ("Python tools for RELACS neurophysiological recording software"),
    #license = "MIT",
    keywords = "data tool",
    #url = "http://packages.python.org/pycircstat",
    packages=['pyrelacs', 'pyrelacs.DataClasses'],
    #long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        #"License :: OSI Approved :: MIT License",
    ],
    # setup_requires=['nose>=1.0', 'mock', 'sphinx_rtd_theme'],
)
