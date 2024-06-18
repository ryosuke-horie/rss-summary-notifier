import boto3
import datetime
import feedparser
import json
import os
import dateutil.parser
from botocore.exceptions import ClientError

# 環境変数からDynamoDBのテーブル名を取得
DDB_TABLE_NAME = os.environ["DDB_TABLE_NAME"]
# DynamoDBリソースを取得
dynamo = boto3.resource("dynamodb")
table = dynamo.Table(DDB_TABLE_NAME)

"""
最近の投稿か判定する
Args:
    pubdate (str): 公開日時の文字列
"""
def recently_published(pubdate):
    # 現在の日時と公開日時の差を計算
    elapsed_time = datetime.datetime.now() - str2datetime(pubdate)
    # 経過日数が3日以上ならFalseを返す
    if elapsed_time.days >= 7:
        return False

    return True

"""
ブログテキストの日付フォーマットをdatetimeに変換する
Args:
    time_str (str): 日時文字列（例: "Tue, 20 Sep 2022 16:05:47 +0000"）
"""
def str2datetime(time_str):
    return dateutil.parser.parse(time_str, ignoretz=True)

"""
DynamoDBにブログ情報を書き込む
Args:
    link (str): ブログ投稿のURL
    title (str): ブログ投稿のタイトル
    category (str): ブログ投稿のカテゴリー
    pubtime (str): ブログ投稿の公開日時
    notifier_name (str): 通知者の名前
"""
def write_to_table(link, title, category, pubtime, notifier_name):
    try:
        # 現在の日時を取得
        current_time = datetime.datetime.now()
        # 3日後のタイムスタンプを計算（TTLのため）
        ttl_time = int((current_time + datetime.timedelta(hours=72)).timestamp())

        # 書き込むアイテムを作成
        item = {
            "url": link,
            "notifier_name": notifier_name,
            "title": title,
            "category": category,
            "pubtime": pubtime,
            "expireAt": ttl_time  # TTL用のカラム
        }
        
        # 条件付き書き込み: URLが存在しない場合のみ書き込む
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(#url)",
            ExpressionAttributeNames={"#url": "url"}
        )
    except ClientError as e:
        # 重複エラーの場合の処理
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print("Duplicate item put: " + title)
        else:
            # その他のエラーの場合の処理
            print(e.response['Error']['Message'])
    except Exception as e:
        # その他のエラーの場合の処理
        print(str(e))

"""
ブログ投稿を追加する
Args:
    rss_name (str): ブログのカテゴリー（RSSユニット）
    entries (List): ブログ投稿のリスト
    notifier_name (str): 通知者の名前
"""
def add_blog(rss_name, entries, notifier_name):
    for entry in entries:
        # 最近の投稿であれば書き込み処理を行う
        if recently_published(entry["published"]):
            write_to_table(
                entry["link"],
                entry["title"],
                rss_name,
                str2datetime(entry["published"]).isoformat(),
                notifier_name,
            )
        else:
            # 古い投稿の場合はスキップ
            print("Old blog entry. skip: " + entry["title"])

"""
Lambda関数のエントリーポイント
Args:
    event (dict): イベントデータ
    context (object): ランタイム情報
"""
def handler(event, context):
    # イベントから通知者の情報を取得
    notifier_name, notifier = event.values()

    # RSS URLリストを取得
    rss_urls = notifier["rssUrl"]
    for rss_name, rss_url in rss_urls.items():
        # RSSフィードを解析
        rss_result = feedparser.parse(rss_url)

        # 最近更新されていないRSSフィードは処理しない
        if not recently_published(rss_result["feed"]["updated"]):
            print("Skip RSS " + rss_name)
            continue
        # ブログ投稿を追加
        add_blog(rss_name, rss_result["entries"], notifier_name)
