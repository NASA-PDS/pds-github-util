import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("pds_github_util/VERSION.txt") as fh:
    version = fh.read().strip()

setuptools.setup(
    name="pds_github_util",
    version=version,
    license="apache-2.0",
    author="thomas loubrieu",
    author_email="loubrieu@jpl.nasa.gov",
    description="util functions for software life cycle enforcement on github",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NASA-PDS/pds-github-util",
    download_url=f"https://github.com/NASA-PDS/pds-github-util/releases/download/{version}/pds_github_util-{version}.tar.gz",
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={
        '': ['*.template', 'gh_pages/resources/*', 'gh_pages/resources/images/*']},
    keywords=['github', 'action', 'github action', 'snapshot', 'release', 'maven'],
    test_suite="tests",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "github3.py==1.3.0",      # Do not change this version without also changing it in github-actions-base
        "lxml==4.6.3",            # Do not change this version without also changing it in github-actions-base
        "mdutils~=1.2.2",
        "packaging==21.0",        # Do not change this version without also changing it in roundup-action
        "markdown2~=2.4.3",
        "jinja2<3.1",             # Do not change: Jinja2 ≥ 3.1 incompatible with Sphinx ≅ 3.2.1
        "emoji~=2.0.0",
        "gitpython~=3.1.27",
        "requests==2.32.0",       # Do not change this version without also changing it in github-actions-base
        "beautifulsoup4~=4.9.0",
        "rstcloth~=0.4.0",
        "pyyaml==6.0",
        "pyzenhub~=0.3.1"
    ],
    entry_points={
        # snapshot-release for backward compatibility
        'console_scripts': ['snapshot-release=pds_github_util.release.maven_release:main',
                            'maven-release=pds_github_util.release.maven_release:main',
                            'python-release=pds_github_util.release.python_release:main',
                            'requirement-report=pds_github_util.requirements.generate_requirements:main',
                            'git-ping=pds_github_util.branches.git_ping:main',
                            'summaries=pds_github_util.gh_pages.build_summaries:main',
                            'pds-plan=pds_github_util.plan.plan:main',
                            'milestones=pds_github_util.milestones.milestones:main',
                            'pds-issues=pds_github_util.issues.issues:main',
                            'move-issues=pds_github_util.issues.move_issues:main',
                            'pds-labels=pds_github_util.issues.labels:main'
                            ],
    },


)
