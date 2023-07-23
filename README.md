# api.camarm.fr - Api used by website frontend
This is a private api. It's useless without a frontend.
## Run

```shell
pip install -r requirements.txt
```

`.env`
```dotenv
GITHUB=ghp_your token
EMAIL=provider id /  email
PASSWORD=email_pass
```

```shell
uvicorn main:app
```