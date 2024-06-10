#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { RssSummaryNotifierStack } from "../lib/rss-summary-notifier-stack";

const app = new cdk.App();
new RssSummaryNotifierStack(app, "RssSummaryNotifierStack", {
	env: {
		account: process.env.CDK_DEFAULT_ACCOUNT,
		region: process.env.CDK_DEFAULT_REGION,
	},
});
