import boto3
import datetime
import feedparser
import json
import os
import dateutil.parser

DDB_TABLE_NAME = os.environ["DDB_TABLE_NAME"]
dynamo = boto3.resource("dynamodb")
table = dynamo.Table(DDB_TABLE_NAME)

"""
最近の投稿か判定する
Args:
    pubdate (str): The publication date and time
"""
def recently_published(pubdate):
    elapsed_time = datetime.datetime.now() - str2datetime(pubdate)
    print(elapsed_time)
    if elapsed_time.days >= 3:
        return False

    return True


"""
Convert the date format from the blog text to datetime
Args:
    time_str (str): The date and time string, e.g., "Tue, 20 Sep 2022 16:05:47 +0000"
"""
def str2datetime(time_str):
    return dateutil.parser.parse(time_str, ignoretz=True)

"""
DynamoDBにブログ情報を書き込む
Args:
    link (str): The URL of the blog post
    title (str): The title of the blog post
    category (str): The category of the blog post
    pubtime (str): The publication date of the blog post
"""
def write_to_table(link, title, category, pubtime, notifier_name):
    try:
        current_time = datetime.datetime.now()
        ttl_time = int((current_time + datetime.timedelta(hours=72)).timestamp())  # 3日後のタイムスタンプ

        item = {
            "url": link,
            "notifier_name": notifier_name,
            "title": title,
            "category": category,
            "pubtime": pubtime,
            "expireAt": ttl_time  # TTL用のカラム
        }
        print(item)
        
        # 条件付き書き込み: url が存在しない場合のみ書き込む
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(url)"
        )
    except Exception as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print("Duplicate item put: " + title)
        else:
            print(e.message)


def add_blog(rss_name, entries, notifier_name):
    """Add blog posts

    Args:
        rss_name (str): The category of the blog (RSS unit)
        entries (List): The list of blog posts
    """

    for entry in entries:
        if recently_published(entry["published"]):
            write_to_table(
                entry["link"],
                entry["title"],
                rss_name,
                str2datetime(entry["published"]).isoformat(),
                notifier_name,
            )
        else:
            print("Old blog entry. skip: " + entry["title"])


def handler(event, context):

    notifier_name, notifier = event.values()

    rss_urls = notifier["rssUrl"]
    for rss_name, rss_url in rss_urls.items():
        rss_result = feedparser.parse(rss_url)
        print(json.dumps(rss_result))
        print("RSS updated " + rss_result["feed"]["updated"])
        if not recently_published(rss_result["feed"]["updated"]):
            # Do not process RSS feeds that have not been updated for a certain period of time.
            # If you want to retrieve from the past, change this number of days and re-import.
            print("Skip RSS " + rss_name)
            continue
        add_blog(rss_name, rss_result["entries"], notifier_name)
