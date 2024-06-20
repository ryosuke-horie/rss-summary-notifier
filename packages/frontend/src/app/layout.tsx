import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { GoogleTagManager } from "@next/third-parties/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
	title: "RSS Summary Notifier",
	description:
		"RSSフィードを収集し要約するサービスです。web技術系の情報収集に利用してください。",
	robots: {
		index: false,
		googleBot: {
			index: false,
		},
	},
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="ja">
			{!!process.env.GOOGLE_ANALYTICS_ID && (
				<GoogleTagManager gtmId={process.env.GOOGLE_ANALYTICS_ID} />
			)}
			<body className={inter.className}>{children}</body>
		</html>
	);
}
