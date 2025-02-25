'use client';

import { useEffect, useState, useRef, useLayoutEffect } from 'react';
import { Transcription } from '@/types/transcription';
import { fetchRecentTranscriptions } from '@/lib/api';
import TranscriptionItem from './TranscriptionItem';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { AudioProvider } from '@/hooks/useAudioContext';
import { ScrollArea } from 'radix-ui';
import '@/styles/typing.css';

export default function TranscriptionList() {
	const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
	const [loading, setLoading] = useState(true);
	const [showTranslations, setShowTranslations] = useState(false);
	const [connectionStatus, setConnectionStatus] = useState<
		'establishing' | 'live'
	>('establishing');
	const [showScrollButton, setShowScrollButton] = useState(true);
	const [unreadCount, setUnreadCount] = useState(0);
	const scrollRef = useRef<HTMLDivElement>(null);
	const SCROLL_THRESHOLD = 200;

	useEffect(() => {
		const eventSource = new EventSource('http://localhost:8000/api/events');
		eventSource.onopen = () => setConnectionStatus('live');
		eventSource.onmessage = event => {
			const jsonStr = event.data.replace(/^data: /, '');
			const newTranscription = JSON.parse(jsonStr);
			setTranscriptions(prev => [...prev, newTranscription].slice(-50));

			// Increment unread count if not at bottom
			const container = scrollRef.current;
			if (container) {
				const { scrollTop, clientHeight, scrollHeight } = container;
				if (scrollHeight - scrollTop - clientHeight > SCROLL_THRESHOLD) {
					setUnreadCount(prev => prev + 1);
				}
			}
		};

		fetchRecentTranscriptions().then(data => {
			// Keep chronological order (oldest first)
			setTranscriptions(data.transcriptions);
			setLoading(false);
		});

		return () => eventSource.close();
	}, []);

	// NEW: Ensure scrollArea starts scrolled all the way down after loading
	useLayoutEffect(() => {
		if (!loading && scrollRef.current) {
			scrollToBottom(false);
		}
	}, [loading]);

	useEffect(() => {
		const container = scrollRef.current;
		if (!container) return;

		const { scrollTop, clientHeight, scrollHeight } = container;
		const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

		if (distanceFromBottom < SCROLL_THRESHOLD) {
			scrollToBottom(false);
		} else {
			setUnreadCount(prev => prev + 1);
		}
	}, [transcriptions]);

	const scrollToBottom = (smooth = true) => {
		const container = scrollRef.current;
		if (container) {
			container.scrollTo({
				top: container.scrollHeight,
				behavior: smooth ? 'smooth' : 'auto',
			});
			setUnreadCount(0);
			setShowScrollButton(false);
		}
	};

	const handleScroll = () => {
		const container = scrollRef.current;
		if (!container) return;
		const { scrollTop, clientHeight, scrollHeight } = container;
		const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

		const isNearBottom = distanceFromBottom < SCROLL_THRESHOLD;
		if (unreadCount > 0) {
			setShowScrollButton(!isNearBottom);
		}
		if (isNearBottom) {
			setUnreadCount(0);
		}
	};

	if (loading) {
		return (
			<Card>
				<CardContent className="p-4">Loading transcriptions...</CardContent>
			</Card>
		);
	}

	return (
		<Card>
			<CardContent className="p-4">
				<div className="flex items-center gap-2 mb-4">
					<span
						className={`w-3 h-3 rounded-full ${
							connectionStatus === 'live' ? 'bg-green-500' : 'bg-yellow-500'
						}`}
					></span>
					<span>
						{connectionStatus === 'live'
							? 'Connection Live'
							: 'Establishing connection...'}
					</span>
				</div>
				<div className="flex items-center space-x-2 mb-4">
					<Switch
						id="translations"
						checked={showTranslations}
						onCheckedChange={setShowTranslations}
					/>
					<Label htmlFor="translations">Show English translations</Label>
				</div>

				<div className="relative w-[800px] container mx-auto">
					<ScrollArea.Root className="h-[1000px] ">
						<ScrollArea.Viewport
							ref={scrollRef}
							className="text-lg leading-relaxed relative h-full overflow-auto"
							onScroll={handleScroll}
						>
							{transcriptions.map((t, i) => (
								<TranscriptionItem
									key={t.timestamp + i}
									transcription={t}
									isLast={i === transcriptions.length - 1}
									showTranslation={showTranslations}
								/>
							))}
						</ScrollArea.Viewport>
						<ScrollArea.Scrollbar
							className="ScrollAreaScrollbar"
							orientation="vertical"
						></ScrollArea.Scrollbar>
					</ScrollArea.Root>
					{showScrollButton && (
						<div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
							<button
								onClick={() => scrollToBottom(true)}
								className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-full shadow-lg transition-all duration-200 flex items-center gap-2"
							>
								<span className="bg-white text-blue-500 rounded-full px-2 py-0.5 text-sm font-bold">
									{unreadCount}
								</span>
								<span>new transcriptions</span>
							</button>
						</div>
					)}
				</div>
			</CardContent>
		</Card>
	);
}
