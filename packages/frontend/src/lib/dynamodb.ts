import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient } from "@aws-sdk/lib-dynamodb";

// 環境変数からアクセスキーを取得し、クライアントを作成する
export const createDynamoDbClient = () => {
  const marshallOptions = {
    // Whether to automatically convert empty strings, blobs, and sets to `null`.
    convertEmptyValues: false,
    // Whether to remove undefined values while marshalling.
    removeUndefinedValues: true,
    // Whether to convert typeof object to map attribute.
    convertClassInstanceToMap: true,
  };
  const unmarshallOptions = {
    // Whether to return numbers as a string instead of converting them to native JavaScript numbers.
    wrapNumbers: false,
  };
  const translateConfig = { marshallOptions, unmarshallOptions };
  const client: DynamoDBClient = new DynamoDBClient({
    region: process.env.AWS_REGION,
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID || "",
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || "",
    },
  });

  return DynamoDBDocumentClient.from(client, translateConfig);
};
