import type { Construct } from "constructs";
import { Stack, type StackProps, Duration } from "aws-cdk-lib";
import {
	Table,
	AttributeType,
	BillingMode,
	StreamViewType,
} from "aws-cdk-lib/aws-dynamodb";
import {
	Rule,
	Schedule,
	RuleTargetInput,
	type CronOptions,
} from "aws-cdk-lib/aws-events";
import { LambdaFunction } from "aws-cdk-lib/aws-events-targets";
import {
	Role,
	Policy,
	ServicePrincipal,
	PolicyStatement,
	Effect,
} from "aws-cdk-lib/aws-iam";
import { Runtime, StartingPosition } from "aws-cdk-lib/aws-lambda";
import { DynamoEventSource } from "aws-cdk-lib/aws-lambda-event-sources";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import { RetentionDays } from "aws-cdk-lib/aws-logs";
import { StringParameter } from "aws-cdk-lib/aws-ssm";
import * as path from "node:path";

export class RssSummaryNotifierStack extends Stack {
	constructor(scope: Construct, id: string, props?: StackProps) {
		super(scope, id, props);

		const region = Stack.of(this).region;
		const accountId = Stack.of(this).account;

		// Bedrockのモデルとリージョンを設定
		const modelRegion = this.node.tryGetContext("modelRegion");
		const modelId = this.node.tryGetContext("modelId");

		const notifiers: [] = this.node.tryGetContext("notifiers");
		const summarizers: [] = this.node.tryGetContext("summarizers");

		// Lambda関数がDynamoDBに書き込まれた新しいエントリをSlackに投稿するためのロール
		const notifyNewEntryRole = new Role(this, "NotifyNewEntryRole", {
			assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
		});
		// インラインポリシーにより、Lambda関数がログを書き込むことを許可
		// また、Bedrockのモデルを呼び出すための権限も追加
		notifyNewEntryRole.attachInlinePolicy(
			new Policy(this, "AllowNotifyNewEntryLogging", {
				statements: [
					new PolicyStatement({
						actions: [
							"logs:CreateLogGroup",
							"logs:CreateLogStream",
							"logs:PutLogEvents",
						],
						effect: Effect.ALLOW,
						resources: [`arn:aws:logs:${region}:${accountId}:log-group:*`],
					}),
					new PolicyStatement({
						actions: ["bedrock:InvokeModel"],
						effect: Effect.ALLOW,
						resources: ["*"],
					}),
				],
			}),
		);

		// RSSを取得し、DynamoDBに書き込むLambda関数用のロール
		const newsCrawlerRole = new Role(this, "NewsCrawlerRole", {
			assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
		});
		// インラインポリシーにより、Lambda関数がログを書き込むことを許可
		// また、DynamoDBに書き込む権限を追加
		newsCrawlerRole.attachInlinePolicy(
			new Policy(this, "AllowNewsCrawlerLogging", {
				statements: [
					new PolicyStatement({
						actions: [
							"logs:CreateLogGroup",
							"logs:CreateLogStream",
							"logs:PutLogEvents",
						],
						effect: Effect.ALLOW,
						resources: [`arn:aws:logs:${region}:${accountId}:log-group:*`],
					}),
				],
			}),
		);

		// RSSデータを格納するDynamoDB
		const rssHistoryTable = new Table(this, "RSSHistory", {
			partitionKey: { name: "url", type: AttributeType.STRING },
			sortKey: { name: "notifier_name", type: AttributeType.STRING },
			billingMode: BillingMode.PAY_PER_REQUEST,
			stream: StreamViewType.NEW_IMAGE,
		});

		// DynamoDBをアップデートするため権限を付与
		rssHistoryTable.grantReadWriteData(notifyNewEntryRole);
		// rssHistoryTable.grantWriteData(notifyNewEntryRole);

		// RSSデータを格納するDynamoDBに書き込まれた新しいエントリをSlackに投稿するLambda関数
		const notifyNewEntry = new PythonFunction(this, "NotifyNewEntry", {
			runtime: Runtime.PYTHON_3_11,
			entry: path.join(__dirname, "../lambda/notify-to-app"),
			handler: "handler",
			index: "index.py",
			timeout: Duration.seconds(180),
			logRetention: RetentionDays.TWO_WEEKS,
			role: notifyNewEntryRole,
			environment: {
				MODEL_ID: modelId,
				MODEL_REGION: modelRegion,
				NOTIFIERS: JSON.stringify(notifiers),
				SUMMARIZERS: JSON.stringify(summarizers),
				DDB_TABLE_NAME: rssHistoryTable.tableName,
			},
		});

		// RSSデータを格納するDynamoDBに書き込まれた新しいエントリをSlackに投稿するLambda関数をDynamoDBのストリームに接続
		notifyNewEntry.addEventSource(
			new DynamoEventSource(rssHistoryTable, {
				startingPosition: StartingPosition.LATEST,
				batchSize: 1,
			}),
		);

		// RSSデータを格納するDynamoDBに書き込まれた新しいエントリをSlackに投稿するLambda関数にDynamoDBへの書き込み権限を付与
		rssHistoryTable.grantWriteData(newsCrawlerRole);

		// RSSを取得し、DynamoDBに書き込むLambda関数
		const newsCrawler = new PythonFunction(this, "newsCrawler", {
			runtime: Runtime.PYTHON_3_11,
			entry: path.join(__dirname, "../lambda/rss-crawler"),
			handler: "handler",
			index: "index.py",
			timeout: Duration.seconds(60),
			logRetention: RetentionDays.TWO_WEEKS,
			role: newsCrawlerRole,
			environment: {
				DDB_TABLE_NAME: rssHistoryTable.tableName,
				NOTIFIERS: JSON.stringify(notifiers),
			},
		});

		for (const notifierName in notifiers) {
			const notifier = notifiers[notifierName];
			// 通知のスケジュールを取得
			// 実行するのは → 毎日の0時
			const schedule: CronOptions = notifier["schedule"] || {
				minute: "08",
				hour: "*",
				day: "*",
				month: "*",
				year: "*",
			};
			// 通知先のURLを取得
			const webhookUrlParameterName = notifier["webhookUrlParameterName"];
			const webhookUrlParameterStore =
				StringParameter.fromSecureStringParameterAttributes(
					this,
					`webhookUrlParameterStore-${notifierName}`,
					{
						parameterName: webhookUrlParameterName,
					},
				);

			// RSSデータを格納するDynamoDBに書き込まれた新しいエントリをSlackに投稿するLambda関数にパラメータストアから読み取る権限を付与
			webhookUrlParameterStore.grantRead(notifyNewEntryRole);

			// 通知のスケジュールを設定
			// see https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#CronExpressions
			const rule = new Rule(this, `CheckUpdate-${notifierName}`, {
				schedule: Schedule.cron(schedule),
				enabled: true,
			});

			rule.addTarget(
				new LambdaFunction(newsCrawler, {
					event: RuleTargetInput.fromObject({ notifierName, notifier }),
					retryAttempts: 2,
				}),
			);
		}
	}
}
