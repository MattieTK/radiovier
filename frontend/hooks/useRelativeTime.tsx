'use client';

import { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';

export function useRelativeTime(timestamp: Date): string {
	const [relativeTime, setRelativeTime] = useState('');

	useEffect(() => {
		const updateTime = () => {
			setRelativeTime(formatDistanceToNow(timestamp, { addSuffix: true }));
		};

		updateTime();
		const interval = setInterval(updateTime, 5000);
		return () => clearInterval(interval);
	}, [timestamp]);

	return relativeTime;
}
