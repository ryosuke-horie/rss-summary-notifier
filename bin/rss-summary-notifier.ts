#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { RssSummaryNotifierStack } from "../lib/rss-summary-notifier-stack";
import { FrontendS3CloudFrontStack } from "../lib/frontend-s3-cloudfront-stack";

const app = new cdk.App();

// RSSサマライザーバッチ処理用のStackを作成する
new RssSummaryNotifierStack(app, "RssSummaryNotifierStack", {
	env: {
		account: process.env.CDK_DEFAULT_ACCOUNT,
		region: process.env.CDK_DEFAULT_REGION,
	},
});

// CloudFront + S3でホスティング用のStackを作成する
new FrontendS3CloudFrontStack(app, "FrontendS3CloudFrontStack", {
    env: {
        account: process.env.CDK_DEFAULT_ACCOUNT,
        region: process.env.CDK_DEFAULT_REGION,
    },
});
