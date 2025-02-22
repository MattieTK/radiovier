export interface Transcription {
    timestamp: string;
    text: string;
    translation: string;
    audio_hash: string;
}

export interface TranscriptionResponse {
    transcriptions: Transcription[];
}
