'use client';

import { useEffect, useState } from 'react';
import { Transcription } from '../../types/transcription';
import {
	fetchRecentTranscriptions,
	fetchTranscriptionsBefore,
} from '../lib/api';
import TranscriptionItem from './TranscriptionItem';
import useInfiniteScroll from '@/app/hooks/useInfiniteScroll';

export default function TranscriptionList() {
	const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const eventSource = new EventSource('http://localhost:8000/api/events');

		eventSource.onmessage = event => {
			const newTranscription = JSON.parse(event.data);
			setTranscriptions(prev => [newTranscription, ...prev]);
		};

		// Load initial transcriptions
		fetchRecentTranscriptions().then(data => {
			setTranscriptions(data.transcriptions);
			setLoading(false);
		});

		return () => eventSource.close();
	}, []);

	const loadMore = async () => {
		if (transcriptions.length === 0) return;
		const oldestTimestamp = transcriptions[transcriptions.length - 1].timestamp;
		const older = await fetchTranscriptionsBefore(oldestTimestamp);
		setTranscriptions(prev => [...prev, ...older.transcriptions]);
	};

	const [loadMoreRef] = useInfiniteScroll(loadMore);

	if (loading) return <div>Loading...</div>;

	return (
		<div className="max-w-2xl mx-auto">
			{transcriptions.map((t, i) => (
				<TranscriptionItem key={t.timestamp + i} transcription={t} />
			))}
			<div ref={loadMoreRef} className="h-10" />
		</div>
	);
}
