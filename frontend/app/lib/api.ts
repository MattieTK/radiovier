import { TranscriptionResponse } from '../../../frontend2/types/transcription';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const fetchRecentTranscriptions = async (): Promise<TranscriptionResponse> => {
    const response = await fetch(`${API_BASE}/api/transcriptions/recent`);
    return response.json();
};

export const fetchTranscriptionsBefore = async (timestamp: string): Promise<TranscriptionResponse> => {
    const response = await fetch(`${API_BASE}/api/transcriptions/before/${timestamp}`);
    return response.json();
};

export const getAudioUrl = (audioHash: string): string => {
    return `${API_BASE}/api/audio/${audioHash}`;
};
