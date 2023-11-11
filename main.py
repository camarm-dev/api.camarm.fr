import json
import secrets
import smtplib
from email.message import EmailMessage
import pymongo
import requests
from bson import ObjectId
from pydantic import BaseModel
import dotenv
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile, Path, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from jinja2 import Template
from typing import Annotated

app = FastAPI(title="API for camarm.dev", description="Api to get stats and send emails. Developped for https://www.camarm.dev", version="1.1")
origins = [
    "*"
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
MAIL_PASSWORD = config['PASSWORD']
MAIL_ADDRESS = config['EMAIL']
MASTER_PASSWORD = config['MASTER_PASSWORD']
REDIRECT = 'https://www.camarm.dev/contact?success'
STATS = {}
IPS = {}
mongo = pymongo.MongoClient(config['DATABASE'])
customerPage = Template(open('front/index.html').read())
loginPage = open('front/login.html').read()
adminLoginPage = open('front/admin_login.html').read()
adminPage = Template(open('front/admin.html').read())
customers = mongo.Customers.customers
resources = mongo.Customers.resources
messages = mongo.Customers.messages


class Person(BaseModel):
    name: str
    email: str


class Message(BaseModel):
    sender: Person
    subject: str
    content: str


class CustomerMessage(Message):
    api_key: str


class LoginPayload(BaseModel):
    key: str


def sendMail(message: Message, to):
    data = {
        "fromAddress": MAIL_ADDRESS,
        "toAddress": to,
        "subject": message.subject,
        "content": message.content
    }
    try:
        response = requests.post('https://mail.zoho.eu/api/accounts/20093658488/messages', data=data)
        return response.ok
    except Exception as error:
        print(f"Error when send email: {error.__class__.__name__}")
        return False
    else:
        print('Email sent correctly')
    return True


def validApiKey(key: str):
    customer = customers.find_one({'key': key})
    if customer:
        return customer['valid'], customer
    return False, {}


def getResources(customer: str):
    customerResources = resources.find({'customer': customer})
    if customerResources:
        return customerResources
    return []


def getMessages(customer: str):
    customerMessages = messages.find({'customer': customer})
    if customerMessages:
        return customerMessages
    return []


def isAdmin(key: str):
    return key == MASTER_PASSWORD


def fillCustomerObject(customer: dict):
    customer['resources'] = getResources(str(customer['_id']))
    customer['messages'] = getMessages(str(customer['_id']))
    return customer
    

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


@app.get("/customer")
async def getCustomer(api_key: str):
    valid, customerObject = validApiKey(api_key)
    if valid:
        customerResources = getResources(customerObject['_id'])
        return {
            **customerObject,
            "ressources": customerResources
        }
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="API key not valid !"
    )


@app.post("/customer/send-mail")
async def sendCustomerMail(message: CustomerMessage):
    isValidKey, customerObject = validApiKey(message.api_key)
    if isValidKey:
        if sendMail(message, customerObject['email']):
            return {
                "message": f"Message successfully sent.",
                "code": 200,
                "data": {}
            }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred when sending message.",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="API key not valid !"
    )


@app.post('/ui', response_class=HTMLResponse)
async def customerInterface(key: Annotated[str, Form()]):
    isValidKey, customerObject = validApiKey(key)
    if isValidKey:
        customerObject['resources'] = getResources(str(customerObject['_id']))
        customerObject['messages'] = getMessages(str(customerObject['_id']))
        return customerPage.render(customer=customerObject)
    return loginPage


@app.get('/login', response_class=HTMLResponse)
async def loginInterface():
    return loginPage


@app.get('/admin', response_class=HTMLResponse)
async def adminLoginInterface():
    return adminLoginPage


@app.post('/admin/new-customer')
async def addCustomer(org: Annotated[str, Form()], person: Annotated[str, Form()], email: Annotated[str, Form()]):
    token = f"c_{secrets.token_urlsafe(32)}"
    customers.insert_one({
        'org': org,
        'contact': person,
        'email': email,
        'key': token,
        'valid': True
    })
    return


@app.post('/admin/add-message')
async def addMessageToCustomer(customer: Annotated[str, Form()], name: Annotated[str, Form()], content: Annotated[str, Form()]):
    customerObject = customers.find_one({'_id': ObjectId(customer)})
    if customerObject:
        messages.insert_one({
            'customer': customer,
            'name': name,
            'content': content
        })
    return


@app.post('/admin/add-resource')
async def addResourceToCustomer(customer: Annotated[str, Form()], name: Annotated[str, Form()], resource: UploadFile):
    customerObject = customers.find_one({'_id': ObjectId(customer)})
    if customerObject:
        fileExtension = resource.filename.split('.')[-1]
        resourceId = resources.insert_one({
            'customer': customer,
            'name': name,
            'filename': resource.filename,
            'extension': fileExtension
        }).inserted_id
        open(f"files/{resourceId}.{fileExtension}", 'wb+').write(await resource.read())
    return


@app.post('/admin', response_class=HTMLResponse)
async def adminInterface(key: Annotated[str, Form()]):
    if isAdmin(key):
        customersObjects = [fillCustomerObject(customer) for customer in customers.find()]
        return adminPage.render(customers=customersObjects)
    return adminLoginPage


@app.get('/favicon.ico')
async def favicon():
    return FileResponse('front/favicon.png')


@app.get('/download/{rid}')
async def downloadResource(key: Annotated[str, Query()], rid: Annotated[str, Path(title="The resource ID to download")]):
    isValid, customerObject = validApiKey(key)
    if isValid:
        resource = resources.find_one({'_id': ObjectId(rid)})
        return FileResponse(f"files/{rid}.{resource['extension']}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="API key not valid !"
    )

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
