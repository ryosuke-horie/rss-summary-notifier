import { Stack, type StackProps } from "aws-cdk-lib";
import * as budgets from "aws-cdk-lib/aws-budgets";
import * as ce from "aws-cdk-lib/aws-ce";
import * as chatbot from "aws-cdk-lib/aws-chatbot";
import * as sns from "aws-cdk-lib/aws-sns";
import type { Construct } from "constructs";

// @note: https://dev.classmethod.jp/articles/aws-cdk-budgets-billing-anomaly-detection-alarm/
// AWSコストアラートを作成するスタック

export interface BillingAlarmStackProps extends StackProps {
	slackChannelConfigurationName: string;
	slackWorkspaceId: string;
	slackChannelId: string;
	budgetLimitAmountUsd: number;
	costAnomaryThresholdUsd: number;
}

export class BillingAlarmStack extends Stack {
	constructor(scope: Construct, id: string, props: BillingAlarmStackProps) {
		super(scope, id, props);
		/**
		 * SNS
		 */
		const topic = new sns.Topic(this, "BillingAlarmTopic");

		/**
		 * Chatbot
		 */
		const slackChannel = new chatbot.SlackChannelConfiguration(
			this,
			"SlackChannel",
			{
				slackWorkspaceId: props.slackWorkspaceId,
				slackChannelConfigurationName: props.slackChannelConfigurationName,
				slackChannelId: props.slackChannelId,
				loggingLevel: chatbot.LoggingLevel.ERROR,
			},
		);

		slackChannel.addNotificationTopic(topic);

		/**
		 * Budgets
		 */
		new budgets.CfnBudget(this, "CfnBudgetCost", {
			budget: {
				budgetType: "COST",
				timeUnit: "MONTHLY",
				budgetLimit: {
					amount: props.budgetLimitAmountUsd,
					unit: "USD",
				},
			},
			notificationsWithSubscribers: [
				{
					notification: {
						comparisonOperator: "GREATER_THAN",
						notificationType: "ACTUAL",
						threshold: 80,
						thresholdType: "PERCENTAGE",
					},
					subscribers: [
						{
							subscriptionType: "SNS",
							address: topic.topicArn,
						},
					],
				},
				{
					notification: {
						comparisonOperator: "GREATER_THAN",
						notificationType: "FORECASTED",
						threshold: 80,
						thresholdType: "PERCENTAGE",
					},
					subscribers: [
						{
							subscriptionType: "SNS",
							address: topic.topicArn,
						},
					],
				},
			],
		});

		/**
		 * Cost Anomaly Detection
		 */
		const cfnAnomalyMonitor = new ce.CfnAnomalyMonitor(
			this,
			"CfnAnomalyMonitor",
			{
				monitorName: "AWS_Services-Recommended",
				monitorType: "DIMENSIONAL",
				monitorDimension: "SERVICE",
			},
		);
		new ce.CfnAnomalySubscription(this, "CfnAnomalySubscription", {
			frequency: "IMMEDIATE",
			monitorArnList: [cfnAnomalyMonitor.attrMonitorArn],
			subscribers: [
				{
					address: topic.topicArn,
					type: "SNS",
				},
			],
			subscriptionName: "AWS_Services-Recommended-AlertSubscription",
			threshold: props.costAnomaryThresholdUsd,
		});
	}
}
