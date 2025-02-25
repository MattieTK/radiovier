'use client';

import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Transcription } from '@/types/transcription';
import { useAudioContext } from '@/hooks/useAudioContext';
import { useRelativeTime } from '@/hooks/useRelativeTime';

interface Props {
	transcription: Transcription;
	isLast: boolean;
	showTranslation: boolean;
}

export default function TranscriptionItem({
	transcription,
	isLast,
	showTranslation,
}: Props) {
	// Audio control via the AudioContext.
	const { play, stop, isPlaying } = useAudioContext();
	const relativeTime = useRelativeTime(transcription.timestamp);

	const handleClick = () => {
		// Toggle playback of this transcription's audio.
		if (isPlaying(transcription.audio_hash)) {
			stop(transcription.audio_hash);
		} else {
			play(transcription.audio_hash);
		}
	};

	return (
		<div className="flex gap-4 mb-2">
			<div className="w-24 text-sm text-gray-500 flex-shrink-0">
				{relativeTime}
			</div>
			<div className="flex-1">
				<span
					onClick={handleClick}
					className={cn(
						'inline cursor-pointer transition-colors',
						isPlaying(transcription.audio_hash)
							? 'bg-blue-100 hover:bg-blue-200'
							: 'hover:bg-gray-100',
						'rounded px-0.5 -mx-0.5'
					)}
				>
					<span className="">{transcription.text}</span>
					{showTranslation && (
						<span className="text-gray-500 ml-2 text-sm">
							({transcription.translation})
						</span>
					)}
				</span>
				{isLast && (
					<span className="ml-2 mx-auto">
						<span className="typing-dots text-gray-800 text-sm">
							<span></span>
							<span></span>
							<span></span>
						</span>
					</span>
				)}
			</div>
		</div>
	);
}
