'use client';

import { createContext, useContext, useRef, useState, ReactNode } from 'react';
import { getAudioUrl } from '@/lib/api';

interface AudioContextType {
	currentlyPlaying: string | null;
	play: (hash: string) => void;
	stop: (hash: string) => void;
	isPlaying: (hash: string) => boolean;
}

const AudioContext = createContext<AudioContextType>({
	currentlyPlaying: null,
	play: () => {},
	stop: () => {},
	isPlaying: () => false,
});

export const AudioProvider = ({ children }: { children: ReactNode }) => {
	// Persist the currently playing audio hash
	const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
	// Global audio element that lives outside of transcription items
	const audioRef = useRef<HTMLAudioElement>(null);

	const play = (hash: string) => {
		if (audioRef.current) {
			// If a different audio is already playing, stop it first.
			if (currentlyPlaying && currentlyPlaying !== hash) {
				audioRef.current.pause();
				audioRef.current.currentTime = 0;
			}
			// Update the audio source and play.
			audioRef.current.src = getAudioUrl(hash);
			audioRef.current
				.play()
				.then(() => {
					setCurrentlyPlaying(hash);
				})
				.catch(console.error);
		}
	};

	const stop = (hash: string) => {
		if (audioRef.current && currentlyPlaying === hash) {
			audioRef.current.pause();
			audioRef.current.currentTime = 0;
			setCurrentlyPlaying(null);
		}
	};

	const isPlaying = (hash: string) => currentlyPlaying === hash;

	return (
		<>
			<AudioContext.Provider
				value={{
					currentlyPlaying,
					play,
					stop,
					isPlaying,
				}}
			>
				{children}
			</AudioContext.Provider>
			{/* Global audio element hidden from view */}
			<audio ref={audioRef} style={{ display: 'none' }} />
		</>
	);
};

export const useAudioContext = () => useContext(AudioContext);
