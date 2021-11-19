"""Release Planning."""

import argparse
import logging
import os
import sys
import traceback

from pds_github_util.issues.utils import get_labels, is_theme
from pds_github_util.zenhub.zenhub import Zenhub
from pds_github_util.utils import GithubConnection, addStandardArguments

from pkg_resources import resource_string
from jinja2 import Template
from yaml import FullLoader, load

# PDS Github Org
GITHUB_ORG = 'NASA-PDS'

REPO_INFO = ('\n--------\n\n'
             '{}\n'
             '{}\n\n'
             '*{}*\n\n'
             '.. list-table:: \n'
             '   :widths: 15 15 15 15 15 15\n\n'
             '   * - `User Guide <{}>`_\n'
             '     - `Github Repo <{}>`_\n'
             '     - `Issue Tracking <{}/issues>`_ \n'
             '     - `Backlog <{}/issues?q=is%3Aopen+is%3Aissue+label%3Aicebox>`_ \n'
             '     - `Stable Release <{}/releases/latest>`_ \n'
             '     - `Dev Release <{}/releases>`_ \n\n')

# Enable logging
_logger = logging.getLogger(__name__)


def append_to_project(proj, output):
    if 'output' in proj.keys():
        proj['output'] += output
    else:
        proj['output'] = output


def get_project(projects, gh_issue, labels):
    intersection = list(set(projects.keys()) & set(labels))
    if intersection:
        return projects[intersection[0]]
    else:
        raise Exception(f"Unknown project for theme '{gh_issue.title}': {labels}")


def main():

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)
    addStandardArguments(parser)
    parser.add_argument('--github_token',
                        help='github API token')
    parser.add_argument('--zenhub_token',
                        help='zenhub API token')
    parser.add_argument('--build_number',
                        help='build number',
                        required=True)
    parser.add_argument('--projects_config',
                        help='Path to config file with project information',
                        required=True)

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel, format="%(levelname)s %(message)s")

    # set output filename
    output_fname = 'plan.rst'

    # get github token or throw error
    github_token = args.github_token or os.environ.get('GITHUB_TOKEN')
    if not github_token:
        _logger.error('github API token must be provided or set as environment'
                     ' variable (GITHUB_TOKEN).')
        sys.exit(1)

    # get zenhub token or throw error
    zenhub_token = args.github_token or os.environ.get('ZENHUB_TOKEN')
    if not zenhub_token:
        _logger.error('zenhub API token must be provided or set as environment'
                     ' variable (ZENHUB_TOKEN).')
        sys.exit(1)

    try:
        gh = GithubConnection.getConnection(token=github_token)
        org = gh.organization(GITHUB_ORG)
        repos = org.repositories()

        issues = []
        repo_dict = {}
        zen = Zenhub(zenhub_token)
        for repo in repos:
            if not issues:
                issues = zen.get_issues_by_release(repo.id, f'B{args.build_number}')

            repo_dict[repo.id] = {'repo': repo,
                                  'issues': []}

        # Build up dictionary of repos + issues in release
        issue_dict = {}
        for issue in issues:
            repo_dict[issue['repo_id']]['issues'].append(issue['issue_number'])

        # Create project-based dictionary
        with open(args.projects_config) as _file:
            _conf = load(_file, Loader=FullLoader)

        # get project info
        projects = _conf['projects']

        # get key dates info
        key_dates = _conf['key_dates']

        # Loop through repos
        plan_output = ''
        maintenance_output = ''
        ddwg_plans = ''
        for repo_id in repo_dict:
            r = repo_dict[repo_id]['repo']
            issues = repo_dict[repo_id]['issues']
            repo_output = ''
            if issues:
                for issue_num in issues:
                    gh_issue = gh.issue(org.login, repo_dict[repo_id]['repo'].name, issue_num)
                    zen_issue = zen.issue(repo_id, issue_num)

                    # we only want release themes in the plan (is_epic + label:theme)
                    labels = get_labels(gh_issue)

                    # Custom handling for pds4-information-model SCRs
                    if 'CCB-' in gh_issue.title:
                        ddwg_plans += f'* `{r.name}#{issue_num} <{gh_issue.html_url}>`_ **{gh_issue.title}**\n'

                    elif is_theme(labels, zen_issue):
                        repo_output += f'* `{r.name}#{issue_num} <{gh_issue.html_url}>`_ **{gh_issue.title}**\n'

                        # proj_id = get_project(projects, gh_issue, labels)
                        # append_to_project(projects[proj_id], f'* `{r.name}#{issue_num} <{gh_issue.html_url}>`_ **{gh_issue.title}**\n')

                        for child in zen.get_epic_children(gh, org, repo_id, issue_num):
                            child_repo = child['repo']
                            child_issue = child['issue']
                            repo_output += f'   * `{child_repo.name}#{child_issue.number} <{child_issue.html_url}>`_ {child_issue.title}\n'

                            # append_to_project(projects[proj_id], f'   * `{child_repo.name}#{child_issue.number} <{child_issue.html_url}>`_ {child_issue.title}\n')
                    # print(repo_output)

            repo_info = REPO_INFO.format(r.name,
                                         '#' * len(r.name),
                                         r.description,
                                         r.homepage or r.html_url + '#readme',
                                         r.html_url,
                                         r.html_url,
                                         r.html_url,
                                         r.html_url,
                                         r.html_url)
            # only output the header
            if repo_output:
                plan_output += repo_info
                plan_output += repo_output

        with open(output_fname, 'w') as f_out:

            template_kargs = {
                'output': output_fname,
                'build_number': args.build_number,
                'scr_date': key_dates['scr_date'],
                'doc_update_date': key_dates['doc_update_date'],
                'delivery_date': key_dates['delivery_date'],
                'trr_date': key_dates['trr_date'],
                'beta_test_date': key_dates['beta_test_date'],
                'dldd_int_date': key_dates['dldd_int_date'],
                'doc_review_date': key_dates['doc_review_date'],
                'ddr_date': key_dates['ddr_date'],
                'release_date': key_dates['release_date'],
                'pds4_changes': ddwg_plans,
                'planned_changes': plan_output
            }
            template = Template(resource_string(__name__,  'plan.template.rst').decode("utf-8"))
            rst_str = template.render(template_kargs)
            f_out.write(rst_str)

            # else:
            #     maintenance_output += repo_info

            #                     print(f'## {r.name}')
            #     print(f'Description: {r.description}')
            #     print(f'User Guide: {r.homepage}')
            #     print(f'Github Repo: {r.html_url}')
            #     print(f'Issue Tracker: {r.html_url}/issues')

                    # print(repo_dict[repo_id]['repo'].name)
                    # print(repo_dict[repo_id]['issues'])

        # print(repo_dict)

        # for repo in repos:


    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

    _logger.info('SUCCESS: Release Plan generated successfully.')

if __name__ == '__main__':
    main()
