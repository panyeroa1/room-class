import { useRoomContext } from '@livekit/components-react';
import { DataPacket_Kind, RoomEvent, Participant } from 'livekit-client';
import { useEffect, useState, useCallback } from 'react';

const TOPIC_HAND_RAISE = 'hand-raise';

export interface HandRaiseState {
    raisedHands: Set<string>; // Set of participant identities
    isHandRaised: boolean;    // Local user state
    raiseHand: () => Promise<void>;
    lowerHand: () => Promise<void>;
}

export function useHandRaising() {
    const room = useRoomContext();
    const [raisedHands, setRaisedHands] = useState<Set<string>>(new Set());
    const [isHandRaised, setIsHandRaised] = useState(false);

    useEffect(() => {
        if (!room) return;

        const handleDataReceived = (payload: Uint8Array, participant?: Participant, kind?: DataPacket_Kind, topic?: string) => {
            if (topic === TOPIC_HAND_RAISE && participant) {
                const str = new TextDecoder().decode(payload);
                try {
                    const data = JSON.parse(str);
                    setRaisedHands((prev) => {
                        const next = new Set(prev);
                        if (data.raised) {
                            next.add(participant.identity);
                        } else {
                            next.delete(participant.identity);
                        }
                        return next;
                    });
                } catch (e) {
                    console.error('Failed to parse hand raise data', e);
                }
            }
        };

        room.on(RoomEvent.DataReceived, handleDataReceived);
        return () => {
            room.off(RoomEvent.DataReceived, handleDataReceived);
        };
    }, [room]);

    const raiseHand = useCallback(async () => {
        if (!room) return;
        setIsHandRaised(true);
        const payload = JSON.stringify({ raised: true });
        const data = new TextEncoder().encode(payload);
        await room.localParticipant.publishData(data, { reliable: true, topic: TOPIC_HAND_RAISE });
    }, [room]);

    const lowerHand = useCallback(async () => {
        if (!room) return;
        setIsHandRaised(false);
        const payload = JSON.stringify({ raised: false });
        const data = new TextEncoder().encode(payload);
        await room.localParticipant.publishData(data, { reliable: true, topic: TOPIC_HAND_RAISE });
    }, [room]);

    return {
        raisedHands,
        isHandRaised,
        raiseHand,
        lowerHand,
    };
}
