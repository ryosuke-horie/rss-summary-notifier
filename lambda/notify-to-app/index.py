import boto3
import json
import os
import traceback
import urllib.request
from typing import Optional
from botocore.config import Config
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from datetime import datetime
import re

# モデルIDやリージョンなどの環境変数を取得
MODEL_ID = os.environ["MODEL_ID"]
MODEL_REGION = os.environ["MODEL_REGION"]
NOTIFIERS = json.loads(os.environ["NOTIFIERS"])
SUMMARIZERS = json.loads(os.environ["SUMMARIZERS"])

DDB_TABLE_NAME = os.environ["DDB_TABLE_NAME"]
dynamo = boto3.resource("dynamodb")
table = dynamo.Table(DDB_TABLE_NAME)

# 技術カテゴリの定義
TECH_CATEGORIES = {
    'AWS': ['AWS', 'Amazon Web Services', 'EC2', 'S3', 'Lambda', 'DynamoDB'],
    'Next.js': ['Next.js', 'Nextjs'],
    'JavaScript': ['JavaScript', 'JS', 'ES6', 'ECMAScript'],
    'PHP': ['PHP', 'Laravel', 'Symfony'],
    'TypeScript': ['TypeScript', 'TS'],
    'Python': ['Python', 'Django', 'Flask', 'PyTorch', 'TensorFlow'],
    'DevOps': ['DevOps', 'CI/CD', 'Jenkins', 'Docker', 'Kubernetes', 'Terraform', 'Ansible'],
    'Cloud': ['Cloud', 'Azure', 'Google Cloud Platform', 'GCP'],
    'Machine Learning': ['Machine Learning', 'ML', 'Artificial Intelligence', 'AI', 'Deep Learning', 'Neural Networks'],
    'Data Science': ['Data Science', 'Data Analysis', 'Pandas', 'NumPy', 'SciPy', 'R'],
    'Frontend': ['Frontend', 'React', 'Vue.js', 'Angular', 'HTML', 'CSS', 'SASS', 'SCSS'],
    'Backend': ['Backend', 'Node.js', 'Express', 'Ruby on Rails', 'Spring Boot', 'ASP.NET'],
    'Database': ['Database', 'SQL', 'NoSQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQLite'],
    'Security': ['Security', 'Cybersecurity', 'Encryption', 'SSL', 'TLS', 'OAuth', 'SAML'],
    'Networking': ['Networking', 'TCP/IP', 'HTTP', 'DNS', 'BGP', 'Firewall', 'VPN'],
    'Mobile': ['Mobile', 'Android', 'iOS', 'React Native', 'Flutter', 'Swift', 'Kotlin'],
    'Blockchain': ['Blockchain', 'Cryptocurrency', 'Bitcoin', 'Ethereum', 'Smart Contract'],
    'Testing': ['Testing', 'Unit Testing', 'Integration Testing', 'Selenium', 'JUnit', 'pytest']
}

# 記事の内容を基にカテゴリを判定する関数
def categorize_article(content):
    categories = []
    for category, synonyms in TECH_CATEGORIES.items():
        for synonym in synonyms:
            # 正規表現を使ってカテゴリを判定
            if re.search(r'\b' + re.escape(synonym) + r'\b', content, re.IGNORECASE):
                categories.append(category)
                break
    # カテゴリが判定されなかった場合、「未分類」として扱う
    if not categories:
        categories.append('未分類')
    return categories

# ブログコンテンツを取得する関数
def get_blog_content(url):
    try:
        if url.lower().startswith(("http://", "https://")):
            with urllib.request.urlopen(url) as response:
                html = response.read()
                if response.getcode() == 200:
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # メインコンテンツを取得
                    main = soup.find("main")
                    if main:
                        return main.get_text()
                    
                    # メインタグがない場合、アーティクルタグを探す
                    article = soup.find("article")
                    if article:
                        return article.get_text()
                    
                    # それでも見つからない場合、他のタグを探す
                    div = soup.find("div", {"class": "content"})
                    if div:
                        return div.get_text()

                    # 最後の手段として、ボディ全体のテキストを返す
                    return soup.body.get_text()
        else:
            print(f"Error accessing {url}, status code {response.getcode()}")
            return None
    except urllib.error.URLError as e:
        print(f"Error accessing {url}: {e.reason}")
        return None

# URLをデコードする関数
def decode_url(url):
    try:
        decoded_url = urllib.parse.unquote(url)
        return decoded_url
    except Exception as e:
        print(f"Error decoding URL {url}: {e}")
        return url

# OGP画像を取得する関数
def get_ogp_image(url):
    try:
        if url.lower().startswith(("http://", "https://")):
            with urllib.request.urlopen(url) as response:
                html = response.read()
                if response.getcode() == 200:
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # OGP画像を取得するためのメタタグをチェック
                    meta_tags = [
                        ("meta", {"property": "og:image"}),         # Open Graph画像
                        ("meta", {"property": "twitter:image"}),     # Twitter画像
                        ("meta", {"name": "og:image"}),              # 別のOpen Graph画像
                        ("meta", {"name": "twitter:image"}),         # 別のTwitter画像
                        ("meta", {"itemprop": "image"})              # Schema.orgの画像
                    ]
                    
                    # 各メタタグを順にチェックし、画像URLが見つかればそれを返す
                    for tag, attrs in meta_tags:
                        ogp_image = soup.find(tag, attrs=attrs)
                        if ogp_image and ogp_image.get("content"):
                            ogp_image_url = decode_url(ogp_image["content"])
                            return ogp_image_url
                    
                    print(f"No OGP image found for {url}")
                    return None
        else:
            print(f"Invalid URL {url}")
            return None
    except urllib.error.URLError as e:
        print(f"Error accessing {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"Unexpected error while accessing {url}: {e}")
        return None

# Bedrockクライアントを取得する関数
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

# ブログを要約する関数
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
        print(f"Model Output: {outputText}")
        summary = re.findall(r"<summary>([\s\S]*?)</summary>", outputText)[0]
    except ClientError as error:
        if error.response["Error"]["Code"] == "AccessDeniedException":
            print(
                f"\x1b[41m{error.response['Error']['Message']}\
            \nTo troubeshoot this issue please refer to the following resources.\ \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
            \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n"
            )
        else:
            raise error
    except IndexError as e:
        print(f"Error extracting summary or thinking: {e}")
        summary = "Summary extraction failed."
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        summary = "An unexpected error occurred."

    return summary

# RSSアイテムを処理する関数
def process_items(item_list):
    for item in item_list:
        notifier = NOTIFIERS[item["rss_notifier_name"]]

        # アイテムのURLを取得して、ブログの内容を取得
        item_url = item["rss_link"]
        content = get_blog_content(item_url)
        summarizer = SUMMARIZERS[notifier["summarizerName"]]
        summary = summarize_blog(content, language=summarizer["outputLanguage"], persona=summarizer["persona"])

        item["summary"] = summary

        # 技術カテゴリを判定
        categories = categorize_article(content)
        item["rss_category"] = categories

        # OGP画像を取得して保存
        ogp_image_url = get_ogp_image(item_url)
        item["ogp_image"] = ogp_image_url if ogp_image_url else ""

        # DynamoDBに要約と詳細を保存
        update_item_in_dynamodb(item)

# DynamoDB更新処理
def update_item_in_dynamodb(item):
    try:
        table.update_item(
            Key={
                'url': item['rss_link'],                        # URLをキーとして使用
                'notifier_name': item['rss_notifier_name']      # Notifier名もキーとして使用
            },
            UpdateExpression="SET title=:t, category=:c, pubtime=:p, summary=:s, ogp_image=:oi",
            ExpressionAttributeValues={
                ':t': item['rss_title'],                        # タイトルを更新
                ':c': item['rss_category'],                     # カテゴリーを更新
                ':p': item['rss_time'],                         # 公開時間を更新
                ':s': item['summary'],                          # 要約を更新
                ':oi': item['ogp_image']                        # OGP画像URLを更新
            },
            ReturnValues="UPDATED_NEW"
        )
        print(f"Item updated: {item['rss_link']}")
    except Exception as e:
        # DynamoDB更新エラーのログ
        print(f"Error updating DynamoDB item: {e}")

# DynamoDBの新規エントリを取得する関数
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

# Lambdaハンドラー
def handler(event, context):
    try:
        new_data = get_new_entries(event["Records"])
        if len(new_data) > 0:
            process_items(new_data)
    except Exception as e:
        print(traceback.print_exc())
