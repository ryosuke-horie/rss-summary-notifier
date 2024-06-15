import { createDynamoDbClient } from "../lib/dynamodb";
import { ScanCommand, type ScanCommandInput } from "@aws-sdk/lib-dynamodb";
// import type { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import Card from "@/components/Card";

interface HomeProps {
  items: {
    title: string;
    summary: string;
    detail: string;
    pubtime: string;
    url: string;
    ogp_image: string;
  }[];
}

const getData = async (): Promise<HomeProps> => {
  const client: any = createDynamoDbClient();
  const params: ScanCommandInput = {
    TableName: process.env.TABLE_NAME,
  };
  const { Items: allItems } = await client.send(new ScanCommand(params));

  const items = allItems.map((item: any) => ({
    title: item.title,
    summary: item.summary,
    detail: item.detail,
    pubtime: item.pubtime,
    url: item.url,
    ogp_image: item.ogp_image,
  }));

  return { items };
};

export default async function Home() {
  const { items } = await getData();
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <h1 className="text-5xl font-bold text-center">Welcome to DaisyUI</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {items.map((item, index) => (
          <Card key={index} item={item} />
        ))}
      </div>
    </main>
  );
}
