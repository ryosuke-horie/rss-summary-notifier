import boto3
import json
import os
import time
import traceback
import urllib.request
from typing import Optional
from botocore.config import Config
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from datetime import datetime, timezone
import re

MODEL_ID = os.environ["MODEL_ID"]
MODEL_REGION = os.environ["MODEL_REGION"]
NOTIFIERS = json.loads(os.environ["NOTIFIERS"])
SUMMARIZERS = json.loads(os.environ["SUMMARIZERS"])

DDB_TABLE_NAME = os.environ["DDB_TABLE_NAME"]
dynamo = boto3.resource("dynamodb")
table = dynamo.Table(DDB_TABLE_NAME)

ssm = boto3.client("ssm")

def get_blog_content(url):
    try:
        if url.lower().startswith(("http://", "https://")):
            with urllib.request.urlopen(url) as response:
                html = response.read()
                if response.getcode() == 200:
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Try to find main content in <main> tag
                    main = soup.find("main")
                    if main:
                        return main.get_text()
                    
                    # If <main> tag not found, try to find <article> tag
                    article = soup.find("article")
                    if article:
                        return article.get_text()
                    
                    # If <article> tag not found, try to find other possible tags
                    # You can add more tags or specific classes/IDs as needed
                    div = soup.find("div", {"class": "content"})
                    if div:
                        return div.get_text()

                    # As a fallback, return the text of the entire body
                    return soup.body.get_text()
        else:
            print(f"Error accessing {url}, status code {response.getcode()}")
            return None
    except urllib.error.URLError as e:
        print(f"Error accessing {url}: {e.reason}")
        return None

# OGP画像の収集を行う
def get_ogp_image(url):
    try:
        if url.lower().startswith(("http://", "https://")):
            with urllib.request.urlopen(url) as response:
                html = response.read()
                if response.getcode() == 200:
                    soup = BeautifulSoup(html, "html.parser")
                    ogp_image = soup.find("meta", property="og:image")
                    if ogp_image:
                        return ogp_image["content"]
                    else:
                        return None
        else:
            print(f"Error accessing {url}, status code {response.getcode()}")
            return None
    except urllib.error.URLError as e:
        print(f"Error accessing {url}: {e.reason}")
        return None

def get_bedrock_client(assumed_role: Optional[str] = None, region: Optional[str] = None, runtime: Optional[bool] = True):
    if region is None:
        target_region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION"))
    else:
        target_region = region

    session_kwargs = {"region_name": target_region}
    client_kwargs = {**session_kwargs}

    profile_name = os.environ.get("AWS_PROFILE")
    if profile_name:
        session_kwargs["profile_name"] = profile_name

    retry_config = Config(region_name=target_region, retries={"max_attempts": 10, "mode": "standard"})
    session = boto3.Session(**session_kwargs)

    if assumed_role:
        sts = session.client("sts")
        response = sts.assume_role(RoleArn=str(assumed_role), RoleSessionName="langchain-llm-1")
        client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
        client_kwargs["aws_secret_access_key"] = response["Credentials"]["SecretAccessKey"]
        client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]

    service_name = "bedrock-runtime" if runtime else "bedrock"
    bedrock_client = session.client(service_name=service_name, config=retry_config, **client_kwargs)

    return bedrock_client

def extract_tech_tags(blog_body):
    boto3_bedrock = get_bedrock_client(assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None), region=MODEL_REGION)
    prompt_data = f"""
<input>{blog_body}</input>
<instruction>Extract all relevant technology-related tags from the given input text. The tags should be keywords that describe technologies, programming languages, frameworks, tools, and other technical terms present in the text. List each tag as a separate item in a JSON array.</instruction>
"""

    max_tokens = 4096

    user_message = {
        "role": "user",
        "content": [{"type": "text", "text": prompt_data}],
    }

    assistant_message = {
        "role": "assistant",
        "content": [{"type": "text", "text": "[]"}],
    }

    messages = [user_message, assistant_message]

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": 0.5,
        "top_p": 1,
        "top_k": 250,
    })

    accept = "application/json"
    contentType = "application/json"
    tags = []

    try:
        response = boto3_bedrock.invoke_model(
            body=body, modelId=MODEL_ID, accept=accept, contentType=contentType
        )
        response_body = json.loads(response.get("body").read().decode())
        tags = json.loads(response_body.get("content")[0]["text"])
        print(tags)
    except ClientError as error:
        if error.response["Error"]["Code"] == "AccessDeniedException":
            print(
                f"\x1b[41m{error.response['Error']['Message']}\
            \nTo troubeshoot this issue please refer to the following resources.\ \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
            \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n"
            )
        else:
            raise error

    return tags

def summarize_blog(blog_body, language, persona):
    boto3_bedrock = get_bedrock_client(assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None), region=MODEL_REGION)
    beginning_word = "<output>"
    prompt_data = f"""
<input>{blog_body}</input>
<persona>You are a professional {persona}. </persona>
<instruction>Describe a new update in <input></input> tags in bullet points to describe "What is the new feature", "Who is this update good for". description shall be output in <thinking></thinking> tags and each thinking sentence must start with the bullet point "- " and end with "\n". Make final summary as per <summaryRule></summaryRule> tags. Try to shorten output for easy reading. You are not allowed to utilize any information except in the input. output format shall be in accordance with <outputFormat></outputFormat> tags.</instruction>
<outputLanguage>In {language}.</outputLanguage>
<summaryRule>The final summary must consists of 1 or 2 sentences. Output format is defined in <outputFormat></outputFormat> tags.</summaryRule>
<outputFormat><thinking>(bullet points of the input)</thinking><summary>(final summary)</summary></outputFormat>
Follow the instruction.
"""

    max_tokens = 4096

    user_message = {
        "role": "user",
        "content": [{"type": "text", "text": prompt_data}],
    }

    assistant_message = {
        "role": "assistant",
        "content": [{"type": "text", "text": f"{beginning_word}"}],
    }

    messages = [user_message, assistant_message]

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": 0.5,
        "top_p": 1,
        "top_k": 250,
    })

    accept = "application/json"
    contentType = "application/json"
    outputText = "\n"

    try:
        response = boto3_bedrock.invoke_model(
            body=body, modelId=MODEL_ID, accept=accept, contentType=contentType
        )
        response_body = json.loads(response.get("body").read().decode())
        outputText = beginning_word + response_body.get("content")[0]["text"]
        print(outputText)
        summary = re.findall(r"<summary>([\s\S]*?)</summary>", outputText)[0]
        detail = re.findall(r"<thinking>([\s\S]*?)</thinking>", outputText)[0]
    except ClientError as error:
        if error.response["Error"]["Code"] == "AccessDeniedException":
            print(
                f"\x1b[41m{error.response['Error']['Message']}\
            \nTo troubeshoot this issue please refer to the following resources.\ \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
            \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n"
            )
        else:
            raise error

    tags = extract_tech_tags(blog_body)

    return summary, detail, tags

def push_notification(item_list):
    for item in item_list:
        notifier = NOTIFIERS[item["rss_notifier_name"]]
        webhook_url_parameter_name = notifier["webhookUrlParameterName"]
        destination = notifier["destination"]
        ssm_response = ssm.get_parameter(Name=webhook_url_parameter_name, WithDecryption=True)
        app_webhook_url = ssm_response["Parameter"]["Value"]

        item_url = item["rss_link"]
        content = get_blog_content(item_url)
        summarizer = SUMMARIZERS[notifier["summarizerName"]]
        summary, detail, tags = summarize_blog(content, language=summarizer["outputLanguage"], persona=summarizer["persona"])

        item["summary"] = summary
        item["detail"] = detail
        item["tags"] = tags

        # OGP画像を取得して保存
        ogp_image_url = get_ogp_image(item_url)
        item["ogp_image"] = ogp_image_url if ogp_image_url else ""

        # 通知用のメッセージを作成し、Slackに送信
        msg = {
            "text": f"<{item['rss_link']}|{item['rss_title']}> {item['summary']} \nTags: {', '.join(tags)}"
        }
        encoded_msg = json.dumps(msg).encode("utf-8")
        print("push_msg:{}".format(item))
        headers = {
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(app_webhook_url, encoded_msg, headers)
        with urllib.request.urlopen(req) as res:
            print(res.read())
        time.sleep(0.5)

        # DynamoDBに要約と詳細を保存
        update_item_in_dynamodb(item)

def update_item_in_dynamodb(item):
    try:
        table.update_item(
            Key={
                'url': item['rss_link'],
                'notifier_name': item['rss_notifier_name']
            },
            UpdateExpression="SET title=:t, category=:c, pubtime=:p, summary=:s, detail=:d, tags=:tg, ogp_image=:oi",
            ExpressionAttributeValues={
                ':t': item['rss_title'],
                ':c': item['rss_category'],
                ':p': item['rss_time'],
                ':s': item['summary'],
                ':d': item['detail'],
                ':tg': item['tags'],
                ':oi': item.get('ogp_image', '')
            },
            ReturnValues="UPDATED_NEW"
        )
        print(f"Item updated: {item['rss_link']}")
    except Exception as e:
        print(f"Error: {e}")

def get_new_entries(blog_entries):
    res_list = []
    for entry in blog_entries:
        if entry["eventName"] == "INSERT":
            new_data = {
                "rss_category": entry["dynamodb"]["NewImage"]["category"]["S"],
                "rss_time": entry["dynamodb"]["NewImage"]["pubtime"]["S"],
                "rss_title": entry["dynamodb"]["NewImage"]["title"]["S"],
                "rss_link": entry["dynamodb"]["NewImage"]["url"]["S"],
                "rss_notifier_name": entry["dynamodb"]["NewImage"]["notifier_name"]["S"],
            }
            res_list.append(new_data)
        else:
            print("skip REMOVE or UPDATE event")
    return res_list

def handler(event, context):
    try:
        new_data = get_new_entries(event["Records"])
        if len(new_data) > 0:
            push_notification(new_data)
    except Exception as e:
        print(traceback.print_exc())
