import unittest
from pds_github_util.issues.move_issues import move_issues, get_gh_connection


class MyTestCase(unittest.TestCase):

    def test_move_issue(self):
        gh_connection = get_gh_connection()
<<<<<<< HEAD
<<<<<<< HEAD
        move_issues('NASA-PDS/registry-api', 'NASA-PDS/registry', gh_connection, label='model', dry_run=True)
=======
        move_issues('NASA-PDS/pds-api-javalib', 'NASA-PDS/registry-api', gh_connection, label='model', dry_run=False)
>>>>>>> add script to move issue from one repository to another
=======
        move_issues('NASA-PDS/registry-api', 'NASA-PDS/registry', gh_connection, label='model', dry_run=True)
>>>>>>> updates after peer review




if __name__ == '__main__':
    unittest.main()
