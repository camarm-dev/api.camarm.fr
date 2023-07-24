import json
import smtplib
from email.message import EmailMessage
from pydantic import BaseModel
import dotenv
import uvicorn
from fastapi import FastAPI, HTTPException, Request
import github
import schedule
from fastapi.middleware.cors import CORSMiddleware
from starlette import status

app = FastAPI(title="API for camarm.dev", description="Api to get stats and send emails. Developped for https://www.camarm.dev", version="1.1")
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
MAIL_PASSWORD = config['PASSWORD']
MAIL_ADDRESS = config['EMAIL']
REDIRECT = 'https://www.camarm.dev/contact?success'
GITHUB = github.Github(GITHUB_TOKEN)
STATS = {}
IPS = {}


class Person(BaseModel):
    name: str
    email: str


class Message(BaseModel):
    sender: Person
    subject: str
    content: str


def countWithCodeFrequency(codeFrequency: list):
    count = 0
    for code in codeFrequency:
        count += code.additions
        count -= code.deletions
    return count


def sendMail(message: Message, to):
    try:
        subject = message.subject
        content = message.content
        from_email, from_name = message.sender.email, message.sender.name
        server = smtplib.SMTP('ns0.ovh.net', 5025)
        server.set_debuglevel(1)
        server.login(MAIL_ADDRESS, MAIL_PASSWORD)
        msg = EmailMessage()
        msg.set_content(f"{content}\n\nEnvoyé depuis https://www.camarm.fr par {from_name} ({from_email})")
        msg['Subject'] = f'[www.camarm.dev] {subject}'
        msg['From'] = f"{from_name} <{from_email}>"
        server.sendmail(MAIL_ADDRESS, to, msg.as_string())
        server.quit()
    except Exception as error:
        print(f"Error when send email: {error.__class__.__name__}")
        return False
    else:
        print('Email sent correctly')
    return True


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
        "line_count": f"{str(lines_count / 1000000)[0:3]}+ M"
    }
    open('stats.json', 'w').write(json.dumps({'data': stats}))
    print(f"Stats refreshed: {commits_count} commits, {repos_count} repos {lines_count} lines of code.")


@app.get("/")
async def root():
    return {"message": "Hello World ! Check /docs for swagger !"}


@app.get("/statistics")
async def statistics():
    stats = json.loads(open('stats.json').read())['data']
    return {
        "message": f"Successfully returned statistics.",
        "data": stats
    }


@app.post("/contact")
async def contact(message: Message, request: Request):
    user_ip = request.client.host
    if IPS.get(user_ip):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You have already sent an email !"
        )
    if sendMail(message, "armand@camponovo.xyz"):
        IPS[user_ip] = True
        return {
            "message": f"Message successfully sent.",
            "code": 200,
            "data": {}
        }
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error occurred when sending message.",
    )

if __name__ == '__main__':
    refreshStats()
    schedule.every().hour.do(refreshStats)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
