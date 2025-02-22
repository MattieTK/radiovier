import { useState } from 'react';
import { Transcription } from '../../types/transcription';
import { getAudioUrl } from '../lib/api';

interface Props {
	transcription: Transcription;
}

export default function TranscriptionItem({ transcription }: Props) {
	const [isPlaying, setIsPlaying] = useState(false);
	const audioUrl = getAudioUrl(transcription.audio_hash);
	const timestamp = new Date(transcription.timestamp).toLocaleTimeString();

	return (
		<div className="border-b p-4 hover:bg-gray-50">
			<div className="flex justify-between items-start">
				<div className="flex-1">
					<p className="text-gray-600">{timestamp}</p>
					<p className="font-medium">{transcription.text}</p>
					<p className="text-gray-500 italic">{transcription.translation}</p>
				</div>
				<button
					onClick={() => setIsPlaying(!isPlaying)}
					className="ml-4 p-2 rounded-full hover:bg-gray-200"
				>
					{isPlaying ? '⏸️' : '▶️'}
				</button>
			</div>
			<audio
				src={audioUrl}
				controls={false}
				onEnded={() => setIsPlaying(false)}
				onPlay={() => setIsPlaying(true)}
				onPause={() => setIsPlaying(false)}
			/>
		</div>
	);
}
