# api.camarm.fr - Api used by website frontend
This is a private api. It's useless without a frontend.

## How it gets statistics
Using github python sdk, it calculates every addition and deletion resulting to a number of lines !

## Run

```shell
pip install -r requirements.txt
```

`.env`
```dotenv
GITHUB=ghp_your token
EMAIL=provider id /  email
PASSWORD=email_pass
DATABASE=your_mongo
```

```shell
uvicorn main:app
```