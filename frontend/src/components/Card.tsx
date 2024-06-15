import Link from "next/link";

interface CardProps {
	item: {
		title: string;
		summary: string;
		url: string;
		ogp_image: string;
	};
}

const Card: React.FC<CardProps> = ({ item }) => {
	const defaultImage =
		"https://img.daisyui.com/images/stock/photo-1606107557195-0e29a4b5b4aa.jpg";
	const imageUrl = item.ogp_image ? item.ogp_image : defaultImage;

	return (
		<Link href={item.url} passHref target="_blank">
			<div className="card w-96 bg-base-100 shadow-xl flex flex-col h-96">
				<figure className="h-1/2">
					<img
						src={imageUrl}
						alt="Thumbnail"
						className="w-full h-full object-cover"
					/>
				</figure>
				<div className="card-body flex flex-col justify-between p-4">
					<h2 className="card-title text-lg font-semibold line-clamp-2">
						{item.title}
					</h2>
					<p className="text-sm line-clamp-3">{item.summary}</p>
				</div>
			</div>
		</Link>
	);
};

export default Card;
