import { TranscriptionResponse } from '../types/transcription';


export const fetchRecentTranscriptions = async (): Promise<TranscriptionResponse> => {
    const response = await fetch(`/api/transcriptions/recent`);
    return response.json();
};

export const getAudioUrl = (audioHash: string): string => {
    return `/api/audio/${audioHash}`;
};
