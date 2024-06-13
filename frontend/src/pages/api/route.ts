import { type NextRequest, NextResponse } from "next/server";

import { createDynamoDbClient } from "../../lib/dynamodb";
import type { DynamoDBClient } from "@aws-sdk/client-dynamodb";

import { ScanCommand, type ScanCommandInput } from "@aws-sdk/lib-dynamodb";

const handleGetRequest = async (client: DynamoDBClient) => {
  const params: ScanCommandInput = {
    TableName: process.env.TABLE_NAME,
  };
  const { Items: allItems } = await client.send(new ScanCommand(params));
  return new NextResponse(JSON.stringify(allItems));
};

const handler = async (req: NextRequest) => {
  // biome-ignore lint/suspicious/noExplicitAny: <explanation>
  const client: any = createDynamoDbClient();

  switch (req.method) {
    case "GET":
      return await handleGetRequest(client);
    default:
      return new NextResponse(JSON.stringify({ error: "error" }));
  }
};

export default handler;
