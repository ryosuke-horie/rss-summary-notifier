import { Stack, type StackProps, aws_iam } from "aws-cdk-lib";
import type { Construct } from "constructs";

const GITHUB_OWNER = "ryosuke-horie";
const GITHUB_REPO = "rss-summary-notifier";
const CDK_QUALIFIER = "hnb659fds"; // 既定値

/**
 * @description GitHub Actions によるデプロイを許可する OIDC プロバイダーを作成する。
 * @see https://dev.classmethod.jp/articles/use-aws-cdk-to-create-permission-resources-when-pr-merge-is-an-action-trigger-using-the-oidc-connection-between-aws-and-github-actions/
 */
export class OidcStack extends Stack {
	constructor(scope: Construct, id: string, props?: StackProps) {
		super(scope, id, props);

		const accountId = Stack.of(this).account;
		const region = Stack.of(this).region;

		// GitHub とのフェデレーション認証を行う OIDC プロバイダーを作成
		const gitHubOidcProvider = new aws_iam.OpenIdConnectProvider(
			this,
			"GitHubOidcProvider",
			{
				url: "https://token.actions.githubusercontent.com",
				clientIds: ["sts.amazonaws.com"],
			},
		);

		// AssumeRole の引受先を制限する信頼ポリシーを定めたロールを作成
		const gitHubOidcRole = new aws_iam.Role(this, "GitHubOidcRole", {
			roleName: "GitHubOidcRole",
			assumedBy: new aws_iam.FederatedPrincipal(
				gitHubOidcProvider.openIdConnectProviderArn,
				{
					StringEquals: {
						// 引受先の Audience（Client ID）を 'sts.amazonaws.com' に制限。
						"token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
						"token.actions.githubusercontent.com:sub":
							// トリガーを Pull Request に制限。
							`repo:${GITHUB_OWNER}/${GITHUB_REPO}:ref:refs/heads/main`,
					},
				},
				"sts:AssumeRoleWithWebIdentity", // 未指定だと既定で 'sts:AssumeRole' が指定されるため、指定必須。
			),
		});

		// CDK Deploy に必要な権限を定めたポリシーを作成
		const cdkDeployPolicy = new aws_iam.Policy(this, "CdkDeployPolicy", {
			policyName: "CdkDeployPolicy",
			statements: [
				// S3 に関する権限
				new aws_iam.PolicyStatement({
					effect: aws_iam.Effect.ALLOW,
					actions: ["s3:getBucketLocation", "s3:List*"],
					resources: ["arn:aws:s3:::*"],
				}),
				// CloudFormation に関する権限
				new aws_iam.PolicyStatement({
					effect: aws_iam.Effect.ALLOW,
					actions: [
						"cloudformation:CreateStack",
						"cloudformation:CreateChangeSet",
						"cloudformation:DeleteChangeSet",
						"cloudformation:DescribeChangeSet",
						"cloudformation:DescribeStacks",
						"cloudformation:DescribeStackEvents",
						"cloudformation:ExecuteChangeSet",
						"cloudformation:GetTemplate",
					],
					resources: [
						`arn:aws:cloudformation:${region}:${accountId}:stack/*/*`,
					],
				}),
				// S3 に関する権限
				new aws_iam.PolicyStatement({
					effect: aws_iam.Effect.ALLOW,
					actions: ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
					resources: [
						"arn:aws:s3:::frontends3cloudfrontstack-websitebucket75c24d94-eklnbci0fwth/*",
					],
				}),
				// SSM に関する権限
				new aws_iam.PolicyStatement({
					effect: aws_iam.Effect.ALLOW,
					actions: ["ssm:GetParameter"],
					resources: [
						`arn:aws:ssm:${region}:${accountId}:parameter/cdk-bootstrap/${CDK_QUALIFIER}/version`,
					],
				}),
				// IAM に関する権限
				new aws_iam.PolicyStatement({
					effect: aws_iam.Effect.ALLOW,
					actions: ["iam:PassRole"],
					resources: [
						`arn:aws:iam::${accountId}:role/cdk-${CDK_QUALIFIER}-cfn-exec-role-${accountId}-${region}`,
					],
				}),
				// CloudFront に関する権限
				new aws_iam.PolicyStatement({
					effect: aws_iam.Effect.ALLOW,
					actions: [
						"cloudfront:GetDistribution",
						"cloudfront:GetDistributionConfig",
						"cloudfront:ListDistributions",
						"cloudfront:ListStreamingDistributions",
						"cloudfront:CreateInvalidation",
						"cloudfront:ListInvalidations",
						"cloudfront:GetInvalidation",
					],
					resources: [
						"arn:aws:cloudfront::730335419965:distribution/E1SO6JWEVR7627",
					],
				}),
			],
		});

		// OIDC用ロールにポリシーをアタッチ
		gitHubOidcRole.attachInlinePolicy(cdkDeployPolicy);
	}
}
