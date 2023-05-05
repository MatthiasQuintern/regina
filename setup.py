from matplotlib.pyplot import matplotlib
from setuptools import setup, find_packages

setup(
        name="regina",
        version="1.0",
        description="Get analytics from nginx logs and visualize them",

        author="Matthias Quintern",
        author_email="matthias@quintern.xyz",

        url="https://git.quintern.xyz/MatthiasQuintern/regina.git",

        license="GPLv3",

        packages=["regina"],
        install_requires=["matplotlib"],
        python_requires='>=3.10',

        classifiers=[
            "Operating System :: POSIX :: Linux",
            "Environment :: Console",
            "Programming Language :: Python :: 3",
            "Topic :: Server",
            "Topic :: Utilities",
            ],

        # data_files=[("ip2nation", ["ip2nation.sql", "ip2nation.db"])],

        # scripts=["bin/nicole"],
        entry_points={
            "console_scripts": [ "regina=regina.main:main" ],
            },
)
