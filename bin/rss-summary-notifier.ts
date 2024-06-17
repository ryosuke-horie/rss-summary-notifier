#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { RssSummaryNotifierStack } from "../lib/rss-summary-notifier-stack";
import { FrontendS3CloudFrontStack } from "../lib/frontend-s3-cloudfront-stack";
import { OidcStack } from "../lib/oidc-stack";
import { BillingAlarmStack } from "../lib/billing_alarm_stack";

const app = new cdk.App();

const env = {
	account: process.env.CDK_DEFAULT_ACCOUNT,
	region: process.env.CDK_DEFAULT_REGION,
};

// RSSサマライザーバッチ処理用のStackを作成する
new RssSummaryNotifierStack(app, "RssSummaryNotifierStack", { env });

// CloudFront + S3でホスティング用のStackを作成する
new FrontendS3CloudFrontStack(app, "FrontendS3CloudFrontStack", { env });

// GitHub Actions によるデプロイを許可する OIDC プロバイダーを作成する
new OidcStack(app, "OidcStack", { env });

// コストアラート 3$をリミット、閾値を1に設定
new BillingAlarmStack(app, "billing-alarm", {
	env,
	slackWorkspaceId: process.env.SLACK_WORKSPACE_ID as string,
	slackChannelConfigurationName: process.env
		.SLACK_CHANNEL_CONFIGURATION_NAME as string,
	slackChannelId: process.env.SLACK_CHANNEL_ID as string,
	budgetLimitAmountUsd: 3,
	costAnomaryThresholdUsd: 1,
});
