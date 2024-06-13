# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import datetime
import feedparser
import json
import os
import dateutil.parser

# CRAWL_BLOG_URL = json.loads(os.environ["RSS_URL"])
# NOTIFIERS = json.loads(os.environ["NOTIFIERS"])

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
    if elapsed_time.days > 7:
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
def write_to_table(item):
    try:
        link = item['url']
        
        # Check if item with the given link already exists
        response = table.get_item(
            Key={
                'url': link
            }
        )
        if 'Item' in response:
            # Item exists, update it
            table.update_item(
                Key={
                    'url': link
                },
                UpdateExpression="SET title=:t, category=:c, pubtime=:p, notifier_name=:n, summary=:s, detail=:d",
                ExpressionAttributeValues={
                    ':t': item['title'],
                    ':c': item['category'],
                    ':p': item['pubtime'],
                    ':n': item['notifier_name'],
                    ':s': item.get('summary', ''),  # Using .get() to handle cases where summary/detail might not be provided
                    ':d': item.get('detail', '')
                },
                ReturnValues="UPDATED_NEW"
            )
            print(f"Item updated: {link}")
        else:
            # Item does not exist, put new item
            table.put_item(Item=item)
            print(f"New item put: {link}")

    except Exception as e:
        print(f"Error: {e}")

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
