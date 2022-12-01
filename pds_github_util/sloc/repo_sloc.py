import git
import argparse


def main():
    parser = argparse.ArgumentParser(description='Create SLOC (Line of code) report')
    parser.add_argument('--repo-path', dest='repo_path',
                        help='local repository path')
    parser.add_argument('--tag-range', dest='tag_range',
                        help="start tag, end tag as tag1..tag2")
    args = parser.parse_args()

    repo = git.Repo(args.repo_path)

    grand_total = {}
    for c in repo.iter_commits(args.tag_range):
        for k, v in c.stats.total.items():
            grand_total[k] = grand_total.get(k, 0) + v

    print(grand_total)


if __name__ == "__main__":
    main()

