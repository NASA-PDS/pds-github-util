# PDS Utility Function for GitHub

Enforces the PDS engineering node software lifecycle:
- publish snapshot releases for python (`python-release --snapshot`) or maven  (`maven-release --snapshot`) projects
- create requirements reports (`requirement-report`)
- ping a repository, ie creates an empty commit & push e.g. to trigger github action (`git-ping`)
- create build summaries from .gitmodule file (`summaries`)
  
These routines are called from [GitHub Actions](https://github.com/features/actions).

They are orchestrated around the [pdsen-corral](https://github.com/nasa-pds/pdsen-corral/) repository.
  

# Prerequisites

libxml2 is used to do publish a snapshot release of a maven project (`maven-release --snapshot`). It needs to be deployed as described in the following subsections.


## macOS

    brew install libxml2
    cd ./venv/lib/python3.7/site-packages/  # chose the site package of the used python
    ln -s /usr/local/Cellar/libxml2/2.9.10/lib/python3.7/site-packages/* .

## Ubuntu, Debian, Mint, or Similar Linux

    sudo apt-get update && sudo apt-get install libxml2-dev libxslt-dev python-dev
    pip install lxml


# Deployment and Execution

Deploy:

    pip install pds-gihub-util

Some environment variables need to be set (they are defined by default in GitHub Actions but need to be set manually otherwise):

    export GITHUB_WORKSPACE=<where the repository which we want to publish a snapshot is cloned>
    export GITHUB_REPOSITORY=<full name of the repository which we want to publish for example NASA-PDS-Incubator/pds-app-registry>
    

# Usage

Get command arguments for each of the available utilities using `--help` flag. e.g.

    maven-release --help
    python-release --help
    requirement-report --help
    git-ping --help
    summaries --help
    milestones --help


## Milestones

Tool for managing Github milestones.

Example of creating milestones:
- for a single repo
- specified in a config file
- prepended by a number
- first due date is 2021-02-25

For example:

    milestones --create --sprint-name-file conf/milestones_2021.yaml \
               --prepend-number 3 --due-date 2021-02-25 \
               --github-org NASA-PDS --github-repos pds-registry-common

## PDS Issues

Tool for generating simple Markdown issue reports.

⚠️ **Warning:** not well tested beyond this example use case.

Example of generating a report for open [NASA-PDS/validate repo](https://github.com/NASA-PDS/validate) issues:

    pds-issues --github_repos validate --issue_state open

Currently outputs to file: `pdsen_issues.md`.

For the RDD generation:

    pds-issues --github-repos validate --issue_state closed --format rst --start-time 2020-10-26T00:00:00Z

Generates `pdsen_issues.rst`.

or (better)

    pds-issues  --github-repos validate --issue_state closed --format rst --build B11.1
Generates `pdsen_issues.rst`

For RD metrics:

    pds-issues --issue_state closed --format metrics --start-time 2020-04-19T00:00:00+00:00 --end-time 2021-10-31T00:00:00+00:00

Move issues from one obsolete repository to a new one:

     move-issues --source-repo NASA-PDS/api-search-query-lexer --target-repo NASA-PDS/registry-api --label lexer
    

# Milestones

Example of creating milestones:
- for a single repo
- specified in a config file
- prepended by a number
- first due date is 2021-02-25

For example:

        milestones --create --sprint_name_file conf/milestones_2021.yaml \
               --prepend_number 3 --due_date 2021-02-25 \
               --github_org NASA-PDS --github_repos pds-registry-common
                   

To close a milestone and move the open ticket to the next milestone use, for example:

    milestones --github-org NASA-PDS --close --sprint-names 06.Mary.Decker.Slaney

Note that the next milestone is automatically retrieved from the number (here 06) in the prefix. That might not work if the next sprint is not found this way.



# Development
 
    git clone ...
    cd pds-github-util
    python -m venv venv
    source venv/bin/activate
    pip install --editable '.'
    
Update the code.

Test the code:

    export GITHUB_TOKEN=<personal access token for github>
    python setup.py test

Create package and publish it. Set the version in setup.py. Tag the code:

    git tag <version>
    git push origin --tags

The package will be published to pypi automatically though GitHub Action.


## Documentation Generation

To manually create the project documentation:

    pip install sphinx-rtd-theme sphinx-argparse


## Manual Publications

Create the package:

    python setup.py sdist

Publish it as a GitHub release.

Publish on pypi (you need a pypi account):

    pip install twine
    twine upload dist/*
