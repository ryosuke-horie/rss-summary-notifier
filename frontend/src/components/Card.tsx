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
		<div className="card w-96 bg-base-100 shadow-xl">
			<figure>
				<img src={imageUrl} alt="Thumbnail" />
			</figure>
			<div className="card-body">
				<h2 className="card-title">{item.title}</h2>
				<p>{item.summary}</p>
			</div>
		</div>
	);
};

export default Card;
