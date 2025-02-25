import { AudioProvider } from '@/hooks/useAudioContext';
import TranscriptionList from './components/TranscriptionList';

export default function Home() {
	return (
		<main className="container mx-auto py-8 px-4">
			<h1 className="text-3xl font-bold mb-8 text-center scroll-m-20 tracking-tight">
				Deutchlandfunk Transcriptions
			</h1>
			<AudioProvider>
				<TranscriptionList />
			</AudioProvider>
		</main>
	);
}
