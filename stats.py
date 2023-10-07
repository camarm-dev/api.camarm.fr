import dotenv
import github
import schedule
import json

dotenv.load_dotenv()
config = dotenv.dotenv_values()

GITHUB_TOKEN = config['GITHUB']
GITHUB = github.Github(GITHUB_TOKEN)


def countWithCodeFrequency(codeFrequency: list):
    count = 0
    for code in codeFrequency:
        count += code.additions
        count -= code.deletions
    return count


def refreshStats():
    print("Getting new stats")
    gh_user = GITHUB.get_user()
    repos = [repo for org in gh_user.get_orgs() for repo in org.get_repos()] + [repo for repo in gh_user.get_repos()]
    repos_count = len(repos)
    commits_count = sum([repo.get_commits().totalCount for repo in repos])
    lines_count = sum([countWithCodeFrequency(repo.get_stats_code_frequency()) for repo in repos])
    stats = {
        "repo_count": repos_count,
        "commit_count": commits_count,
        "line_count": f"{str(lines_count / 1000)[0:4]}+ K"
    }
    open('stats.json', 'w').write(json.dumps({'data': stats}))
    print(f"Stats refreshed: {commits_count} commits, {repos_count} repos {lines_count} lines of code.")


if __name__ == '__main__':
    refreshStats()
    schedule.every(1).hour.do(refreshStats)
