import { useRoomContext } from '@livekit/components-react';
import { DataPacket_Kind, RoomEvent, Participant } from 'livekit-client';
import { useEffect, useState } from 'react';

const TOPIC_TRANSCRIPT = 'transcript';
const TOPIC_TRANSLATION = 'translation';

export interface TranscriptItem {
    id: string;
    senderIdentity: string;
    senderName?: string;
    text: string;
    language?: string;
    timestamp: number;
    isTranslation?: boolean;
}

export function useTranscript() {
    const room = useRoomContext();
    const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);

    useEffect(() => {
        if (!room) return;

        const handleDataReceived = (payload: Uint8Array, participant?: Participant, kind?: DataPacket_Kind, topic?: string) => {
            if ((topic === TOPIC_TRANSCRIPT || topic === TOPIC_TRANSLATION) && participant) {
                const str = new TextDecoder().decode(payload);
                try {
                    // Expecting JSON: { text: "...", language: "..." }
                    // Or just string.
                    // Let's assume JSON for reliability.
                    const data = JSON.parse(str);

                    const newItem: TranscriptItem = {
                        id: Math.random().toString(36).substring(7),
                        senderIdentity: participant.identity,
                        senderName: participant.name,
                        text: data.text || str, // Fallback to raw string if no text field
                        language: data.language,
                        timestamp: Date.now(),
                        isTranslation: topic === TOPIC_TRANSLATION
                    };

                    setTranscripts((prev) => [...prev, newItem].slice(-50)); // Keep last 50
                } catch (e) {
                    // If not JSON, treat as raw text
                    const newItem: TranscriptItem = {
                        id: Math.random().toString(36).substring(7),
                        senderIdentity: participant.identity,
                        senderName: participant.name,
                        text: str,
                        timestamp: Date.now(),
                        isTranslation: topic === TOPIC_TRANSLATION
                    };
                    setTranscripts((prev) => [...prev, newItem].slice(-50));
                }
            }
        };

        room.on(RoomEvent.DataReceived, handleDataReceived);
        return () => {
            room.off(RoomEvent.DataReceived, handleDataReceived);
        };
    }, [room]);

    return {
        transcripts
    };
}
