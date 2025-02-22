import TranscriptionList from './components/TranscriptionList';

export default function Home() {
	return (
		<main className="min-h-screen bg-gray-50 py-8">
			<div className="max-w-4xl mx-auto px-4">
				<h1 className="text-3xl font-bold mb-8 text-center">
					Radio Transcriptions
				</h1>
				<TranscriptionList />
			</div>
		</main>
	);
}
