import { createDynamoDbClient } from "../lib/dynamodb";
import { ScanCommand, type ScanCommandInput } from "@aws-sdk/lib-dynamodb";
import Card from "@/components/Card";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

interface HomeProps {
	items: {
		title: string;
		summary: string;
		url: string;
		ogp_image: string;
		category: string[];
	}[];
}

interface GroupedItems {
	[category: string]: {
		title: string;
		summary: string;
		url: string;
		ogp_image: string;
		category: string[];
	}[];
}

const getData = async (): Promise<GroupedItems> => {
	const client = createDynamoDbClient();
	const params: ScanCommandInput = {
		TableName: process.env.TABLE_NAME,
	};
	try {
		const { Items: allItems } = await client.send(new ScanCommand(params));

		// allItemsがundefinedの場合は空の配列を返す
        if (!allItems) {
            return {};
        }

		const items = allItems
			.map((item: any) => {
				// ここでDynamoDBレスポンスから直接フィールドを取得
				const title = item.title || "";
				const summary = item.summary || "";
				const url = item.url || "";
				const ogp_image = item.ogp_image || "";
				const expiredAt = item.expireAt || 0;
				const category = item.category || [];

				return {
					title,
					summary,
					url,
					ogp_image,
					expiredAt,
					category
				};
			})
			.sort(
				(a: { expiredAt: number }, b: { expiredAt: number }) =>
					b.expiredAt - a.expiredAt,
			);

		const groupedItems: GroupedItems = items.reduce((acc, item) => {
			item.category.forEach((category: string) => {
				if (!acc[category]) {
					acc[category] = [];
				}
				acc[category].push(item);
			});
			return acc;
		}, {} as GroupedItems);

		return groupedItems;
	} catch (error) {
		console.error("Error fetching data:", error);
		return {}; // エラーハンドリング
	}
};

export default async function Home() {
	const groupedItems: GroupedItems = await getData();

	return (
		<div>
			<Header />
			<main className="flex min-h-screen flex-col items-center justify-between p-12">
				{Object.entries(groupedItems).map(([category, items]) => (
					<div key={category}>
						<h2 className="text-2xl font-bold mb-6">{category}</h2>
						<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
							{items.map((item, index) => (
								<Card key={index} item={item} />
							))}
						</div>
					</div>
				))}
			</main>
			<Footer />
		</div>
	);
}
