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
        category: string;
	}[];
}

interface GroupedItems {
	[category: string]: {
		title: string;
		summary: string;
		url: string;
		ogp_image: string;
        category: string;
	}[];
}

const getData = async (): Promise<GroupedItems> => {
	// biome-ignore lint/suspicious/noExplicitAny: <explanation>
	const client: any = createDynamoDbClient();
	const params: ScanCommandInput = {
		TableName: process.env.TABLE_NAME,
	};
	const { Items: allItems } = await client.send(new ScanCommand(params));

	// データをマッピングして expiredAt で並び替え
	const items = allItems
		// biome-ignore lint/suspicious/noExplicitAny: <explanation>
		.map((item: any) => ({
			title: item.title,
			summary: item.summary,
			url: item.url,
			ogp_image: item.ogp_image,
			expiredAt: item.expiredAt,
            category: item.category,
		}))
		.sort(
			(a: { expiredAt: number }, b: { expiredAt: number }) =>
				b.expiredAt - a.expiredAt,
		); // expiredAtで降順に並び替え

	// categoryごとにグループ化
	const groupedItems: GroupedItems = items.reduce((acc, item) => {
		const category = item.category;
		if (!acc[category]) {
			acc[category] = [];
		}
		acc[category].push(item);
		return acc;
	}, {} as GroupedItems);

	return groupedItems;
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
