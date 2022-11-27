from setuptools import setup, find_packages

setup(
        name="regina",
        version="1.0",
        description="Get analytics from nginx logs and visualize them",

        author="Matthias Quintern",
        author_email="matthias@quintern.xyz",

        url="https://git.quintern.xyz/MatthiasQuintern/regina.git",

        license="GPLv3",

        packages=find_packages(),
        install_requires=[],
        python_requires='>=3.10',

        classifiers=[
            "Operating System :: POSIX :: Linux",
            "Environment :: Console",
            "Programming Language :: Python :: 3",
            "Topic :: Server",
            "Topic :: Utilities",
            ],

        # scripts=["bin/nicole"],
        entry_points={
            "console_scripts": [ "regina=regina.main:main" ],
            },
)
