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
	}[];
}

const getData = async (): Promise<HomeProps> => {
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
		}))
		.sort(
			(a: { expiredAt: number }, b: { expiredAt: number }) =>
				b.expiredAt - a.expiredAt,
		); // expiredAtで降順に並び替え

	return { items };
};

export default async function Home() {
	const { items } = await getData();
	return (
		<div>
			<Header />
			<main className="flex min-h-screen flex-col items-center justify-between p-12">
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
					{items.map((item, index) => (
						// biome-ignore lint/suspicious/noArrayIndexKey: <explanation>
						<Card key={index} item={item} />
					))}
				</div>
			</main>
			<Footer />
		</div>
	);
}
