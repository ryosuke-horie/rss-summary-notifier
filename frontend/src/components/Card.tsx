interface CardProps {
	item: {
		title: string;
		summary: string;
		detail: string;
		pubtime: string;
		url: string;
	};
}

const Card: React.FC<CardProps> = ({ item }) => {
	return (
		<div className="card w-96 bg-base-100 shadow-xl">
			<figure>
				<img
					src="https://img.daisyui.com/images/stock/photo-1606107557195-0e29a4b5b4aa.jpg"
					alt="Shoes"
				/>
			</figure>
			<div className="card-body">
				<h2 className="card-title">{item.title}</h2>
				<p>{item.summary}</p>
				<p>{item.detail}</p>
				<p>{new Date(item.pubtime).toLocaleString()}</p>
				<div className="card-actions justify-end">
					<button className="btn btn-primary">Read More</button>
				</div>
			</div>
		</div>
	);
};

export default Card;
