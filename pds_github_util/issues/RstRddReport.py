import os
import sys
from pds_github_util.utils import GithubConnection, RstClothReferenceable

from enum import Enum

import logging
from datetime import datetime

from github3.issues.issue import ShortIssue, Issue
from zenhub import Zenhub
from pds_github_util.issues.utils import has_label


class PDSIssue(ShortIssue):

    def get_rationale(self):
        splitted_body = self.body.split('Rationale:')
        if len(splitted_body) == 2:
            return splitted_body[1]\
                .replace('\n', ' ')\
                .replace('\r', ' ')\
                .replace('*', '')\
                .strip()
        else:
            return None


from pds_github_util.issues.utils import get_issue_priority, ignore_issue

class RddReport:

    ISSUE_TYPES = ['bug', 'requirement', 'theme', 'enhancement'] # non hierarchical tickets
    THEME = 'theme'
    IGNORED_LABELS = {'wontfix', 'duplicate', 'invalid', 'I&T', 'untestable'}
    NOT_TESTED = 'skip-i&t'
    IGNORED_REPOS = {'PDS-Software-Issues-Repo', 'pds-template-repo-python', 'pdsen-corral', 'pdsen-operations',
                     'roundup-action', 'github-actions-base', '.github', 'nasa-pds.github.io', 'pds-github-util',
                     'pds-template-repo-java', 'devops-BROKEN', 'kdp'}
    REPO_INFO = '*{}*\n\n' \
                '.. list-table:: \n' \
                '   :widths: 15 15 15 15 15 15\n\n' \
                '   * - `User Guide <{}>`_\n' \
                '     - `Github Repo <{}>`_\n' \
                '     - `Issue Tracking <{}/issues>`_ \n' \
                '     - `Backlog <{}/issues?q=is%3Aopen+is%3Aissue+label%3Abacklog>`_ \n' \
                '     - `Stable Release <{}/releases/latest>`_ \n' \
                '     - `Dev Release <{}/releases>`_ \n\n'
    SWG_REPO_NAME = 'pds-swg'

    def __init__(self,
                 org,
                 title=None,
                 start_time=None,
                 end_time=None,
                 build=None,
                 token=None):


        # Quiet github3 logging
        self._logger = logging.getLogger('github3')
        self._logger.setLevel(level=logging.WARNING)

        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger(__name__)

        self._org = org
        self._gh = GithubConnection.getConnection(token=token)
        self._start_time = start_time
        self._end_time = end_time
        self._build = build
        self._rst_doc = RstClothReferenceable()

        self._rst_doc.title(title)

    def available_repos(self):
        for _repo in self._gh.repositories_by(self._org):
            if _repo.name not in RstRddReport.IGNORED_REPOS:
                yield _repo

    def add_repo(self, repo):
        issues_map = self._get_issues_groupby_type(repo, state='closed')
        issue_count = sum([len(issues) for _, issues in issues_map.items()])
        if issue_count > 0:
            self._write_repo_change_section(repo, issues_map)

    def _get_issues_groupby_type(self, repo, state='closed'):
        issues = {}
        for t in RstRddReport.ISSUE_TYPES:
            issues[t] = []

            if self._start_time:
                self._logger.info("get %s issues from start time %s on ", t,  self._start_time)
                type_issues = repo.issues(state=state, labels=t, direction='asc', start=self._start_time)
            else:
                labels = [t, self._build]
                self._logger.info("get %s issues for build %s", t, self._build)
                type_issues = repo.issues(state=state, labels=','.join(labels), direction='asc')

            for issue in type_issues:
                if not ignore_issue(issue.labels(), ignore_labels=RstRddReport.IGNORED_LABELS) \
                   and (self._end_time is None or issue.created_at < datetime.fromisoformat(self._end_time)):
                    issues[t].append(issue)

        return issues


class MetricsRddReport(RddReport):

    def __init__(self,
                 org,
                 start_time=None,
                 end_time=None,
                 build=None,
                 token=None):

        title = f"Release Metrics for build {build}" if build else ''

        super().__init__(org,
                         title=title,
                         start_time=start_time,
                         end_time=end_time,
                         build=build,
                         token=token)
        self.issues_type_counts = {}
        for t in self.ISSUE_TYPES:
            self.issues_type_counts[t] = 0

        self.issues_type_five_biggest = {}
        for t in self.ISSUE_TYPES:
            self.issues_type_five_biggest[t] = []

        self.bugs_open_closed = {}
        self.bugs_severity = {}

        self.high_and_critical_open_bugs = ""

        self.epic_closed_for_the_build = {}

    def create(self, repos):
        for _repo in self.available_repos():
            if not repos or _repo.name in repos:
                self.add_repo(_repo)

        print('Issues types')
        print(self.issues_type_counts)

        print('Bug states')
        print(self.bugs_open_closed)

        print('Bug severity')
        print(self.bugs_severity)

        print('Open high and critical bugs')
        print(self.high_and_critical_open_bugs)

        print('Closed EPICS')
        print(self.epic_closed_for_the_build)

    def _non_bug_metrics(self, type, repo):
        for issue in repo.issues(
                state='closed',
                labels=f'{self._build},{type}',
                direction='asc',
                since=self._start_time
        ):
            if not ignore_issue(issue.labels(), ignore_labels=RstRddReport.IGNORED_LABELS) \
                    and (not self._end_time or issue.created_at <  datetime.fromisoformat(self._end_time)):
                self.issues_type_counts[type] += 1

    def _bug_metrics(self, repo):
        for issue in repo.issues(
                state='all',
                labels=f'{self._build},bug',
                direction='asc',
                since=self._start_time
        ):
            if not ignore_issue(issue.labels(), ignore_labels=RstRddReport.IGNORED_LABELS) \
                    and (not self._end_time or issue.created_at < datetime.fromisoformat(self._end_time)):
                # get severity
                severity = 's.unknown'
                for label in issue.labels():
                    if label.name.startswith('s.'):
                        severity = label.name
                        break
                if severity in self.bugs_severity.keys():
                    self.bugs_severity[severity] += 1
                else:
                    self.bugs_severity[severity] = 1

                # get state
                if issue.state in self.bugs_open_closed.keys():
                    self.bugs_open_closed[issue.state] += 1
                else:
                    self.bugs_open_closed[issue.state] = 1

                if issue.state == 'open' and severity in {'s.critical', 's.high'}:
                    self._logger.info("%s#%i %s %s %s", repo, issue.number, issue.title, severity, issue.state)
                    self.high_and_critical_open_bugs += "%s#%i %s %s\n" % (repo, issue.number, issue.title, severity)


                # get count
                if issue.state == 'closed':
                    self.issues_type_counts['bug'] += 1
                else:
                    self._logger.info("this issues is still open %s#%i: %s", repo, issue.number, issue.title)

    def _get_epics_count(self, repo):

        epics = repo.issues(state='closed', labels=f'{self._build},Epic')
        n = 0

        for _ in epics:
            n += 1

        return n

    def _get_issue_type_count(self, repo):

        # count epics
        n_epics = self._get_epics_count(repo)
        if n_epics>0:
            self.epic_closed_for_the_build[repo.name] = n_epics

        for t in RstRddReport.ISSUE_TYPES:
            if t == 'bug':
                self._bug_metrics(repo)
            else:
                self._non_bug_metrics(t, repo)

    def add_repo(self, repo):
        self._logger.info("add repo %s", repo)
        self._get_issue_type_count(repo)


class EpicFactory:
    def __init__(self, zenhub, logger):
        self._zenhub = zenhub
        self._logger = logger

    def create_enhancement(self, repo, gh_issue, build):
        self._logger.info('Create enhancement for repo %s for issue %i', repo.name, gh_issue.number)

        enhancement = Enhancement(gh_issue, log=self._logger)
        self._logger.info(enhancement.type.value)
        if enhancement.type.value == EnhancementTypes.THEME.value \
                or enhancement.type.value == EnhancementTypes.EPIC.value:  # not leaf in the tree
            self._logger.info("search for epic children")
            epic_child_issues = self._zenhub.get_epic_data(repo.id, gh_issue.number)
            self._logger.info(epic_child_issues)
            for issue in epic_child_issues['issues']:
                if issue['repo_id'] == repo.id:
                    self._logger.debug("github api request, get issue %i", issue['issue_number'])
                    gh_child_issue = repo.issue(issue['issue_number'])
                    if has_label(gh_child_issue, build) and gh_child_issue.state == 'closed':
                        enhancement_child = self.create_enhancement(repo, gh_child_issue, build)
                        enhancement.add_child(enhancement_child)

        return enhancement


class EnhancementTypes(Enum):
    THEME = 'theme'
    EPIC = 'epic'
    ENHANCEMENT = 'enhancement'
    REQUIREMENT = 'requirement'
    BUG = 'bug'
    TASK = 'task'


class Enhancement(Issue):
    def __init__(self, issue, log=None):
        if log:
            self._logger = log
            log.info("Create enhancement for issue %i", issue.number)

        self.issue = issue
        self.children = []
        self.type = Enhancement._get_enhancement_type(issue)

    def crawl(self):
        self._logger.info("yield issue %i", self.issue.number)
        yield self
        for child in self.children:
            self._logger.info("crawl issue %i", child.issue.number)
            yield from child.crawl()




    @staticmethod
    def _get_enhancement_type(issue):
        enhancement_type = EnhancementTypes.TASK
        for label in issue.labels():
            if label.name in {item.value for item in EnhancementTypes}:
                enhancement_type = EnhancementTypes(label.name)
                print(label.name, enhancement_type.value)
                break

        return enhancement_type

    def add_child(self, issue):
        self.children.append(issue)


class RstRddReport(RddReport):

    ZENHUB_TOKEN = 'ZENHUB_TOKEN'

    def __init__(self,
                 org,
                 title=None,
                 start_time=None,
                 end_time=None,
                 build=None,
                 token=None):

        if not title:
            build_text = f"(build {build})" if build else ''
            title = f"Release Description Document " + build_text
        super().__init__(org,
                         title=title,
                         start_time=start_time,
                         end_time=end_time,
                         build=build,
                         token=token)

        self._rst_doc = RstClothReferenceable()
        self._rst_doc.title(title)

        if RstRddReport.ZENHUB_TOKEN not in os.environ.keys():
            self._logger.error("missing %s environment variable", RstRddReport.ZENHUB_TOKEN)
            sys.exit(1)

        zenhub_token = os.environ.get('ZENHUB_TOKEN')
        self._zenhub = Zenhub(zenhub_token)

    def _get_change_requests(self):
        self._logger.info(
            "Getting change requests from %s/%s for build %s",
            self._org,
            RstRddReport.SWG_REPO_NAME,
            self._build
        )
        swg_repo = self._gh.repository(self._org, RstRddReport.SWG_REPO_NAME)

        change_requests = swg_repo.issues(state='closed', labels=','.join(['change-request', self._build]))

        columns = ["Issue", "Title", "Rationale"]
        data = []
        for cr in change_requests:
            self._rst_doc.hyperlink(f'{RstRddReport.SWG_REPO_NAME}_{cr.number}', cr.html_url)
            cr.__class__ = PDSIssue  # python cast
            data.append([f'{RstRddReport.SWG_REPO_NAME}_{cr.number}_ {cr.title}'.replace('|', ''), cr.title, cr.get_rationale()])

        self._rst_doc.table(
            columns,
            data=data)

    def _add_repo_description(self, repo):
        repo_info = RstRddReport.REPO_INFO.format(
                                     repo.description,
                                     repo.homepage or repo.html_url + '#readme',
                                     repo.html_url,
                                     repo.html_url,
                                     repo.html_url,
                                     repo.html_url,
                                     repo.html_url)
        self._rst_doc._add(repo_info)

    def _get_theme_trees(self, repo):
        labels = [self.THEME, self._build]
        theme_issues = repo.issues(state='all', labels=','.join(labels), direction='asc')
        theme_trees = []
        for theme_issue in theme_issues:
            theme = EpicFactory(self._zenhub, self._logger).create_enhancement(repo, theme_issue, self._build)
            theme_trees.append(theme)
        return theme_trees

    def _write_repo_change_section(self, repo):
        issue_map = self._get_issues_groupby_type(
            repo,
            state='closed'
        )

        issue_count = sum([len(issues) for issues in issue_map.values()])

        if issue_count:
            self._rst_doc.content("--------")
            self._rst_doc.newline()
            self._rst_doc.h2(repo.name)
            self._add_repo_description(repo)
            planned_tickets = self._add_planned_updates(repo)
            self._add_other_updates(repo, issue_map, ignore_tickets=planned_tickets)

    def _add_other_updates(self, repo, issues_map, ignore_tickets=None):

        for type, issues in issues_map.items():
            issues_map[type] = list(set(issues) - ignore_tickets)

        issue_count = sum([len(issues) for issues in issues_map.values()])

        if issue_count>0:
            self._rst_doc.h3("Other updates")
            for issue_type, issues in issues_map.items():
                if issues and issue_type != RddReport.THEME:
                    self._add_rst_repo_change_sub_section(repo, issue_type, issues, ignore_tickets=ignore_tickets)

    def _flush_theme_updates(self, theme_line, ticket_lines):
        empty_suffix = "" if ticket_lines else " (no epic in this repository)"
        theme_line = theme_line + empty_suffix
        self._rst_doc.li(theme_line)
        if ticket_lines:
            columns = ["Issue", "I&T", "Level", "Priority / Bug Severity"]
            self._rst_doc.table(
                columns,
                data=ticket_lines)

        self._rst_doc.newline()


    @staticmethod
    def _is_tested(issue):
        for label in issue.labels():
            if label.name == RstRddReport.NOT_TESTED:
                return False

        return True

    @staticmethod
    def _get_theme_head(repo, issue):
        return f'`{repo.name}#{issue.number}`_ {issue.title}'

    def _add_planned_updates(self, repo):
        themes = self._get_theme_trees(repo)
        self._rst_doc.h3("Planned Updates")
        planned_tickets = set()
        done = False
        for theme in themes:
            theme_crawler = theme.crawl()
            theme = next(theme_crawler)
            planned_tickets.add(theme.issue)
            self._rst_doc.hyperlink(f'{repo.name}#{theme.issue.number}', theme.issue.html_url)
            theme_head = RstRddReport._get_theme_head(repo,
                                                      theme.issue
                                                      )
            data = []
            for enhancement in theme_crawler:
                issue = enhancement.issue
                if not ignore_issue(issue.labels(), ignore_labels=RstRddReport.IGNORED_LABELS):
                    self._logger.info("crawl theme tree %i", issue.number)
                    self._rst_doc.hyperlink(f'{repo.name}#{issue.number}', issue.html_url)
                    i_and_t = '|iandt|' if RstRddReport._is_tested(issue) else ''
                    data.append([f'`{repo.name}#{issue.number}`_ {issue.title}'.replace('|', ''),
                                 i_and_t,
                                 enhancement.type.value,
                                 get_issue_priority(issue)])
                    planned_tickets.add(issue.number)

            self._flush_theme_updates(theme_head, data)
            done = True

        if not done:
            self._rst_doc.content("No planned update realised in the build in this repository.")
            self._rst_doc.newline()

        return planned_tickets

    def _add_rst_repo_change_sub_section(self,
                                         repo,
                                         type,
                                         issues,
                                         ignore_tickets=None
                                         ):

        data = []
        for issue in issues:
            if issue.number not in ignore_tickets:
                i_and_t = '|iandt|' if RstRddReport._is_tested(issue) else ''
                self._rst_doc.hyperlink(f'{repo.name}#{issue.number}', issue.html_url)
                data.append([f'`{repo.name}#{issue.number}`_ {issue.title}'.replace('|', ''),
                             i_and_t,
                             get_issue_priority(issue)])

        if data:
            self._rst_doc.h4(type.capitalize() + 's')
            columns = ["Issue", "I&T", "Priority / Bug Severity"]
            self._rst_doc.table(
                columns,
                data=data)

    def _add_software_changes(self, repos):
        self._logger.info("Add software changes")
        self._rst_doc.deffered_directive('image',
                                         arg=f'https://nasa-pds.github.io/_static/images/noun_certified_18093.png',
                                         fields=[('alt', 'I&T'), ('width', '20')],
                                         reference='iandt')
        self._rst_doc.h1('Software changes')
        self._rst_doc.content("The changes types are 'bug', 'enhancement' or 'requirement'. "
                              "For each software repository, the changes are listed in 2 categories: ")
        self._rst_doc.li("planned updates")
        self._rst_doc.li("other updates")
        self._rst_doc.newline()

        self._rst_doc.content(f"The 'planned updates' are organized by 'themes' which are defined at the planing phase (see `plan {self._build}`_')")
        self._rst_doc.content(f"The 'other updates' occurs during the build cycle witout being planned or attached to a theme. They are organized by types (bug, enhancements, requirements...)")
        self._rst_doc.newline()
        self._rst_doc.content(f"The deliveries are validated by the development team and most of time, when relevant, also go through an additional Integration & Test process as indicated by a specific icon in the following tables.")
        self._rst_doc.newline()

        for _repo in self.available_repos():
            if not repos or _repo.name in repos:
                self._write_repo_change_section(_repo)

    def _add_liens(self):
        self._logger.info("Add liens")
        self._rst_doc.h1('Liens')
        self._get_change_requests()

    def _add_software_catalogue(self):
        self._logger.info("Add software catalog")
        self._rst_doc.h1('Engineering Node Software Catalog')
        self._rst_doc.content(
            f'The Engineering Node Software resources are listed in the `software release summary ({self._build})`_'
        )
        self._rst_doc.newline()
        self._rst_doc.hyperlink(
            f'software release summary ({self._build})',
            f'https://nasa-pds.github.io/releases/{self._build}/index.html'
        )


    def _add_install_and_operation(self):
        self._logger.info("Add installation and operations")
        self._rst_doc.h1('Installation and operation')
        self._rst_doc.content(
            'PDS Engineering node software are meant to be deployed in 3 contexts: standalone, discipline nodes or engineering node')

        self._rst_doc.content('For the installation and operation manual see the `user''s manuals` in the software summary sections below:' )

        self._add_li('`PDS Standalone`_')
        self._add_li('`PDS Discipline Nodes`_')
        self._add_li('`PDS Engineering Node only`_')

        self._rst_doc.hyperlink(
            'PDS Standalone',
            'https://nasa-pds.github.io/releases/11.1/index.html#standalone-tools-and-libraries'
        )

        self._rst_doc.hyperlink(
            'PDS Discipline Nodes',
            'https://nasa-pds.github.io/releases/11.1/index.html#discipline-node-services'
        )

        self._rst_doc.hyperlink(
            'PDS Engineering Node only',
            'https://nasa-pds.github.io/releases/11.1/index.html#enineering-node-services'
        )

        self._rst_doc.newline()


    def _add_li(self, s):
        self._rst_doc.newline()
        self._rst_doc.li(s, wrap=False)

    def _add_reference_docs(self):
        self._logger.info("Add reference docs")
        self._rst_doc.h1('Reference documents')
        self._rst_doc.content(
            'This section details the controlling and applicable documents referenced for this release. The controlling documents are as follows:')

        self._add_li('PDS Level 1, 2 and 3 Requirements, April 20, 2017.')
        self._add_li('PDS4 Project Plan, July 17, 2013.')
        self._add_li('PDS4 System Architecture Specification, Version 1.3, September 1, 2013.')
        self._add_li('PDS4 Operations Concept, Version 1.0, September 1, 2013.')
        self._add_li(
            'PDS Harvest Tool Software Requirements and Design Document (SRD/SDD), Version 1.2, September 1, 2013.')
        self._add_li(
            'PDS Preparation Tools Software Requirements and Design Document (SRD/SDD), Version 0.3, September 1, 2013.')
        self._add_li(
            'PDS Registry Service Software Requirements and Design Document (SRD/SDD), Version 1.1, September 1, 2013.')
        self._add_li(
            'PDS Report Service Software Requirements and Design Document (SRD/SDD), Version 1.1, September 1, 2013.')
        self._add_li(
            'PDS Search Service Software Requirements and Design Document (SRD/SDD), Version 1.0, September 1, 2013.')
        self._add_li('PDS Search Scenarios, Version 1.0, September 1, 2013.')
        self._add_li('PDS Search Protocol, Version 1.2, March 21, 2014.')
        self._add_li('PDAP Search Protocol, Version 1.0, March 21, 2014.')
        self._add_li(
            'PDS Security Service Software Requirements and Design Document (SRD/SDD), Version 1.1, September 1, 2013.')
        self._add_li('`PDS Deep Archive Sotware Requirements and Design Document (SRD/SDD)`_')
        self._add_li('`PDS DOI Service Requirements and Design Document (SRD/SDD)`_')

        self._rst_doc.newline()

        self._rst_doc.hyperlink(
            'PDS Deep Archive Sotware Requirements and Design Document (SRD/SDD)',
            'https://github.com/NASA-PDS/pds-deep-archive/blob/master/docs/pds4_nssdca_delivery_design_20191219.docx'
        )
        self._rst_doc.hyperlink(
            'PDS DOI Service Requirements and Design Document (SRD/SDD)',
            'https://github.com/NASA-PDS/pds-doi-service/blob/master/docs/design/pds-doi-service-srd.md'
        )


    def _add_introduction(self):
        self._logger.info("Add introduction")
        self._rst_doc.content('This release of the PDS4 System is intended as an operational release of the system components to date.')
        self._rst_doc.content(f'The original plan for this release can be found here: `plan {self._build}`_')
        self._rst_doc.newline()
        self._rst_doc.content('The following sections can be found in this document:')
        self._rst_doc.hyperlink(f'plan {self._build}', f'https://nasa-pds.github.io/releases/{self._build[1:]}/plan.html')  # remove B prefix from the build code
        self._rst_doc.newline()
        self._rst_doc.directive('toctree', fields=[('glob', ''), ('maxdepth', 3)], content='rdd.rst')
        self._rst_doc.newline()

    def _add_standard_and_information_model_changes(self):
        self._logger.info("Add standard updates")
        IM_REPO = "pds4-information-model"

        self._rst_doc.h1('PDS4 Standards and Information Model Changes')
        self._rst_doc.content(
            'This section details the changes to the PDS4 Standards and Information Model approved by the PDS4 Change '
            'Control Board and implemented by the PDS within the latest build period.'
        )

        columns = ["Ref", "Title"]

        data = []

        repository = self._gh.repository(self._org, IM_REPO)
        labels = ['pending-scr', self._build]
        for issue in repository.issues(state='closed', labels=','.join(labels), direction='asc', since=self._start_time):
            self._rst_doc.hyperlink(f'{IM_REPO}#{issue.number}', issue.html_url)
            data.append([f'`{IM_REPO}#{issue.number}`_'.replace('|', ''), issue.title])

        if data:
            self._rst_doc.table(
                columns,
                data=data)
        else:
            self._rst_doc.content("no PDS4 standard updates")

    def create(self, repos, filename):
        self._logger.info("Create RDD rst")
        self._add_introduction()
        self._add_standard_and_information_model_changes()
        self._add_software_changes(repos)
        self._add_liens()
        self._add_software_catalogue()
        self._add_install_and_operation()
        self._add_reference_docs()
        self.write(filename)

    def add_repo(self, repo):
        issues_map = self._get_issues_groupby_type(
            repo,
            state='closed'
        )
        issue_count = sum([len(issues) for _, issues in issues_map.items()])

        if issue_count > 0:
            self._write_repo_change_section(repo, issues_map)

    def write(self, filename):
        self._logger.info('Create file %s', filename)
        self._rst_doc.write(filename)