import json
import dotenv
import uvicorn
from fastapi import FastAPI
import github
import schedule
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = [
    "http://www.camarm.dev",
    "https://www.camarm.dev",
    "http://www.camarm.fr",
    "https://www.camarm.fr",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
dotenv.load_dotenv()
config = dotenv.dotenv_values()
GITHUB_TOKEN = config['GITHUB']
GITHUB = github.Github(GITHUB_TOKEN)
STATS = {}


def countWithCodeFrequency(codeFrequency: list):
    count = 0
    for code in codeFrequency:
        count += code.additions
        count -= code.deletions
    return count


def refreshStats():
    gh_user = GITHUB.get_user()
    repos = [repo for org in gh_user.get_orgs() for repo in org.get_repos()] + [repo for repo in gh_user.get_repos()]
    repos_count = len(repos)
    commits_count = sum([repo.get_commits().totalCount for repo in repos])
    lines_count = sum([countWithCodeFrequency(repo.get_stats_code_frequency()) for repo in repos])
    stats = {
        "repo_count": repos_count,
        "commit_count": commits_count,
        "line_count": f"{str(lines_count / 1000000)[0:3]}+ M"
    }
    open('stats.json', 'w').write(json.dumps({'data': stats}))


@app.get("/")
async def root():
    return {"message": "Hello World ! Check /docs for swagger !"}


@app.get("/statistics")
async def statistics():
    stats = json.loads(open('stats.json').read())['data']
    return {
        "message": f"Successfully returned statistics",
        "data": stats
    }

if __name__ == '__main__':
    refreshStats()
    schedule.every().hour.do(refreshStats)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
